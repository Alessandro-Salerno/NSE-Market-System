# MC-UMSR-NSE Market System
# Copyright (C) 2023 - 2024 Alessandro Salerno

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import socket
import json
import pandas
import os
import rich
import getpass
import signal
import plotext as p
from datetime import datetime

from rich.table import Table
from rich.console import Console
from rich import box

from mcom.connection_handler import MComConnectionHandler

from unet.client import UNetClient, UNetClientConnectionMode
from unet.protocol import UNetAuthMode
from unet.command import NoSuchUNetCommandException, UNetCommandIncompatibleArgumentException
from unet.command_handler import UNetCommandHandler, unet_command
from unet.command_parser import UNetCommandParserFactory, UNetCommandParseException

from unet.protocol import *


class MyLocalHandler(UNetCommandHandler):
    @unet_command('exit')
    def exit(self, command: any):
        os.kill(os.getpid(), signal.SIGINT)

    @unet_command('logout')
    def logout(self, command: any):
        self.top._connection.protocol.socket.close()
        self.top._connection.kill()
        self.parent.kill()

    @unet_command('ping')
    def ping(self, command: any):
        start = datetime.now()
        self.parent.protocol.ask('whoami')
        print(f"Ping time: {int((datetime.now().timestamp() - start.timestamp()) * 1000)} ms\n")

    @unet_command('avgping')
    def avgping(self, command: any):
        print('This operation may take a few seconds...')
        start = datetime.now()
        for i in range(1000):
            self.parent.protocol.ask('whoami')
        diff = datetime.now() - start
        print(f"Average ping time: {int(diff.microseconds / 1000)} microseconds\n")

    @unet_command('clear', 'cls')
    def clear(self, command: any):
        p.clear_terminal()

    @unet_command('cpw')
    def cpw(self, command: any):
        old = getpass.getpass('Old Password: ')
        new = getpass.getpass('New Password: ')
        return f'passwd "{old}" "{new}"'
    
    @unet_command('cem')
    def cem(self, command: any):
        new = input('New E-Mail Address: ')
        return f'emaddr "{new}"'


class MyHandler(MComConnectionHandler):
    def main(self) -> None:
        _ = Console()
        p.clear_terminal()

        login = json.loads(self.protocol.recv())
        self.reply(rtype=login['type'], code=login['code'], message=login['message']['content'])
        if login['code'] == UNetStatusCode.DONE:
            self.parent.command_orchestrator.call_command(UNetCommandParserFactory().parse('.ping'))

        self.USERNAME = json.loads(self.protocol.ask('whoami'))['value']
        self.previous_line = None
        self.schedule(self.my_main)
        self.kill(self.main)

    def my_main(self):
        ts = os.get_terminal_size()
        print("\033[%d;%dH" % (ts.lines - 3, 0))
        print(f"+{'-' * (ts.columns - 2)}+")
        prefix = f"({self.USERNAME})"
        print(f"| {prefix}{' ' * (ts.columns - 3 - len(prefix))}|")
        print(f"+{'-' * (ts.columns - 2)}+", end='')
        print("\033[%d;%dH" % (ts.lines - 1, 2 + len(prefix) + 2), end='')
        cmd_str = input()
        if len(cmd_str) == 1:
            cmd_str *= 2
        command = UNetCommandParserFactory().parse(cmd_str)
        res = self.parent.command_orchestrator.call_command(command)

        if command.local and res != None:
            self.display(json.loads(self.protocol.ask(res)))

        if not command.local:
            response = json.loads(self.protocol.recv())
            self.display(response)

    def on_exception(self, exception: Exception) -> None:
        if isinstance(exception, UNetCommandParseException):
            print(exception.to_string_frame())
            return
        
        if isinstance(exception, NoSuchUNetCommandException) or isinstance(exception, UNetCommandIncompatibleArgumentException):
            self.reply('LOCAL', 'ERR', exception.message)
            return
        
        if isinstance(exception, ConnectionResetError):
            self.reply('LOCAL', 'ERR', 'Connection lost')
            self.kill()
            running = False
            return

        return super().on_exception(exception)

    def clear_previous(self, new_line):
        if not self.previous_line:
            return
        
        print("\033[%d;%dH" % (self.previous_line, 0))
        ts = os.get_terminal_size()
        
        for _ in range(self.previous_line, new_line):
            print(' ' * ts.columns)

    def display(self, response: dict, multi=False, index=0, end=True, mlen=1):
        response_type = response['type']

        match response_type:
            case UNetMessageType.MULTI:
                self.previous_line = None
                for index, message in enumerate(response['messages']):
                    self.display(json.loads(message), multi=True, index=index, end=(index == len(response['messages']) - 1), mlen=len(response['messages']))
            
            case UNetMessageType.STATUS:
                if index == 0:
                    ts = os.get_terminal_size()
                    new_line = ts.lines - 4 - mlen - 1
                    self.clear_previous(new_line)
                    self.previous_line = new_line
                    print("\033[%d;%dH" % (new_line, 0))
                    print(f"+{'-' * (ts.columns - 2)}+")
                self.reply(rtype=response['type'], code=response['code'], message=response['message']['content'])
                if end:
                    print(f"+{'-' * (ts.columns - 2)}+")

            case UNetMessageType.VALUE:
                ts = os.get_terminal_size()
                if index == 0:
                    new_line = ts.lines - 4 - mlen - 1
                    self.clear_previous(new_line)
                    self.previous_line = new_line
                    print("\033[%d;%dH" % (new_line, 0))
                    print(f"+{'-' * (ts.columns - 2)}+")

                out = f"{response['name']}: {response['value']}"
                c = Console()
                print('| ', end='')
                c.print(f"{out}{' ' * (ts.columns - 3 - len(out))}", style='#FFFFFF', end='')
                print('|')
                if end:
                    print(f"+{'-' * (ts.columns - 2)}+")

            case UNetMessageType.CHART:
                self.previous_line = None
                p.clear_figure()
                p.clear_color()
                p.clear_data()
                p.clear_terminal() if index == 0 else None
                
                xfmt = response['xformat']
                xl = response['xlabel']
                yl = response['ylabel']
                t = response['title']
                
                ts = os.get_terminal_size()

                p.theme('pro')
                p.plotsize(ts.columns, ts.lines - 3)
                
                for series in response['series']:
                    x = series['x']
                    y = series['y']

                    if xfmt != None:
                        p.date_form(xfmt)
                        x = p.datetime_to_string(pandas.DatetimeIndex(x))
                    
                    p.plot(x, y)

                p.title(t)
                p.xlabel(xl)
                p.ylabel(yl)
                p.grid(True, True)
                p.build()
                print(p.active().monitor.matrix.get_canvas().replace("•", "█"))

            case UNetMessageType.TABLE:
                self.previous_line = None
                console = Console()
                p.clear_terminal() if index == 0 else None

                table = Table(
                    title=f"[bold][yellow]{response['title']}[/yellow][/bold]",
                    show_edge=True, show_lines=False, box=box.SIMPLE
                )

                columns = response['columns']
                rows = response['rows']
                
                for ci, column in enumerate(columns):
                    table.add_column(f'[blue]{column}[/blue]', justify=('left' if ci == 0 else 'right'))
                for row in rows:
                    final_row = []
                    color = '#FFFFFF'
                    for e in row:
                        if isinstance(e, float):
                            final_row.append(f'{e:.3f}')
                        else:
                            final_row.append(str(e))
                        
                        if isinstance(e, str):
                            if '+' in e and '%' in e and e != "+0.00%":
                                color = "#90EE90"
                            elif '-' in e and '%' in e:
                                color = "#FF7F7F"
                        
                    table.add_row(*final_row, style=color)
                
                ts = os.get_terminal_size()
                table.min_width = int(round(max(ts.columns / 3, min(ts.columns, 80))))
                console.print(table, justify='center', width=ts.columns)
                print()
            
            case other:
                self.reply('LOCAL', 'ERR', f"Unknown reponse type '{response_type}'")

    def reply(self, rtype, code, message):
        out = f'[{rtype}] ({code}) {message}'
        color = '#FFFFFF'
        if rtype == 'STATUS' and code == 'DONE':
            color = '#00FF00'
        elif rtype == 'STATUS':
            color = '#FF0000'
        
        c = Console()
        ts = os.get_terminal_size()
        print('| ', end='')
        c.print(f"{out}{' ' * (ts.columns - 3 - len(out))}", style=color, end='')
        print('|')


def get_int(message, valrange=(0, 0)):
    val = 0
    while True:
        try:
            val = int(input(message))

            if val == (0, 0) or val not in range(*valrange):
                return val
            else:
                print('Invalid input\n')
        except ValueError as ve:
            print('Invalid input\n')



if __name__ == '__main__':
    # VERY Bad client code
    while True:
        p.clear_terminal()
        
        server_addr = input('UNet Server IP: ')
        server_port = get_int('UNet Server Remote Port: ')

        mode_id = get_int(
"""
Connection Modes:
    1. Sign in
    2. Sign up

Mode: """)
        
        print()
        args = []
        match mode_id:
            case 1:
                args.append('LOGIN')
                args.append(input('Username: '))
                args.append(None)
                args.append(getpass.getpass('Password: '))

            case 2:
                args.append('SIGNUP')
                args.append(input('Username: '))
                args.append(input('E-Mail Address: '))
                args.append(getpass.getpass('Password: '))

        client = UNetClient(conn_mode=UNetClientConnectionMode(*args),
                            local_command_handler=MyLocalHandler(),
                            server_address=server_addr if len(server_addr) != 0 else '127.0.0.1',
                            server_port=server_port,
                            connection_handler_class=MyHandler)
