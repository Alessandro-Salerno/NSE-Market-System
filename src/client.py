import socket
import json
import pandas
import os
import rich
import getpass
import signal
import plotext as p

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


# program flags
running = True
connected = True


class MyLocalHandler(UNetCommandHandler):
    @unet_command('exit')
    def exit(self, command: any):
        self.top._connection.protocol.socket.close()
        self.top._connection.kill()
        self.parent.kill()
        os.kill(os.getpid(), signal.SIGINT)

    @unet_command('logout')
    def logout(self, command: any):
        self.top._connection.protocol.socket.close()
        self.top._connection.kill()
        self.parent.kill()
        global connected
        connected = False

    @unet_command('clear', 'cls')
    def clear(self, command: any):
        p.clear_terminal()

    @unet_command('cpw')
    def cpw(self, command: any):
        old = getpass.getpass('Old Password: ')
        new = getpass.getpass('New Password: ')
        return f'passwd "{old}" "{new}"'
    
    @unet_command('che')
    def che(self, command: any):
        new = input('New E-Mail Address: ')
        return f'emaddr "{new}"'


class MyHandler(MComConnectionHandler):
    def __init__(self, socket: socket, parent=None) -> None:
        super().__init__(socket, parent)
    
    def main(self) -> None:
        _ = Console()
        p.clear_terminal()

        login = json.loads(self.protocol.recv())
        if login['code'] != UNetStatusCode.DONE:
            self.reply(rtype=login['type'], code=login['code'], message=login['message']['content'])

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

                p.date_form(xfmt)
                p.theme('pro')
                p.plotsize(ts.columns, ts.lines - 3)
                
                for series in response['series']:
                    x = series['x']
                    y = series['y']
                    dates = p.datetime_to_string(pandas.DatetimeIndex(x))
                    p.plot(dates, y)

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


if __name__ == '__main__':
    # VERY Bad client code
    while running:
        p.clear_terminal()
        
        server_addr = input('UNet Server IP: ')
        server_port = input('UNet Server Remote Port: ')

        print('1. Login')
        print('2. Signup')

        mode_id = 0
        while True:
            try:
                mode_id = int(input('> '))

                if mode_id > 0 and mode_id <= 2:
                    break
                else:
                    print('Invalid input\n')
            except:
                print('Invalid input\n')

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
                            server_address='127.0.0.1',
                            server_port=19055,
                            connection_handler_class=MyHandler)

        connected = True
        while connected:
            pass

    while True:
        pass
