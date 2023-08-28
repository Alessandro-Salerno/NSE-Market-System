# MC-UMSR-NSE Market System
# Copyright (C) 2023 Alessandro Salerno

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

        self.schedule(self.my_main)
        self.kill(self.main)

    def my_main(self):
        command = UNetCommandParserFactory().parse(input('> '))
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

    def display(self, response: dict, multi=False, index=0, end=True):
        response_type = response['type']

        match response_type:
            case UNetMessageType.MULTI:
                for index, message in enumerate(response['messages']):
                    self.display(json.loads(message), multi=True, index=index, end=(index == len(response['messages']) - 1))
            
            case UNetMessageType.STATUS:
                self.reply(rtype=response['type'], code=response['code'], message=response['message']['content'])

            case UNetMessageType.VALUE:
                print(f"-- {response['name']}: {response['value']}")
                print() if end else None

            case UNetMessageType.CHART:
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
                    table.add_row(*[str(e) for e in row])
                
                console.print(table, justify='center')
                print()
            
            case other:
                self.reply('LOCAL', 'ERR', f"Unknown reponse type '{response_type}'")

    def reply(self, rtype, code, message):
        print(f'[{rtype}] ({code}) {message}\n')



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
