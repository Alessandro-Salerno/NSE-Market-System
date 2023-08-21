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


import json
import socket
import traceback
import logging

from mcom.connection_handler import MComConnectionHandler
from mcom.server import MComServer

from unet.command import UNetCommand, NoSuchUNetCommandException, UNetCommandIncompatibleArgumentException
from unet.command_parser import UNetCommandParserFactory
from unet.command_handler import UNetCommandHandler
from unet.database import UNetUserDatabase
import unet.protocol as uprot


class UNetServerCommand(UNetCommand):
    def __init__(self, base_command: UNetCommand, issuer: str) -> None:
        super().__init__(base_command.command_stirng, base_command.command_name, *base_command.arguments, local=base_command.local)
        self._issuer = issuer

    @property
    def issuer(self):
        return self._issuer


class UNetAuthenticatedHandler(MComConnectionHandler):
    def __init__(self,
                 socket: socket,
                 user: str,
                 user_command_handler: UNetCommandHandler,
                 admin_command_handler: UNetCommandHandler,
                 parent=None) -> None:
        
        self._user = user
        self._user_command_handler = user_command_handler
        self._user_command_handler._parent = self
        self._user_command_handler._top = parent
        self._admin_command_handler = admin_command_handler
        self._admin_command_handler._parent = self
        self._admin_command_handler._top = parent
        self._parser_facttory = UNetCommandParserFactory(local_symbol='*')
        super().__init__(socket=socket, parent=parent)

    def main(self) -> None:
        msg_cmd = self.protocol.recv()
        if len(msg_cmd) == 0 or msg_cmd == None:
            raise ConnectionResetError()
        
        command = UNetServerCommand(self._parser_facttory.parse(msg_cmd), self._user)

        if command.local and self.parent.user_database.has_role(self._user, 'admin'):
            self.protocol.send(self._admin_command_handler.call_command(command=command))
            logging.info(f"Admin '{self._user}' issued priviledged command '{command.command_stirng}'")
            return
        
        if not command.local and self.parent.user_database.has_role(self._user, 'user'):
            self.protocol.send(self._user_command_handler.call_command(command=command))
            return
        
        logging.warning(f"Unauthorized user '{self._user}' issued priviledged command '{command.command_stirng}'")
        self.protocol.send(uprot.unet_make_status_message(
            mode=uprot.UNetStatusMode.ERR,
            code=uprot.UNetStatusCode.DENY,
            message={
                'content': 'Permission denied'
            }
        ))

    def on_logout(self, username: str) -> None:
        return

    def on_exception(self, exception: Exception) -> None:
        if isinstance(exception, ConnectionResetError) or isinstance(exception, ConnectionAbortedError) \
            or isinstance(exception.__cause__, ConnectionResetError) or isinstance(exception.__cause__, ConnectionAbortedError):
            logging.info(f'{self._user} disconnected')
            self.kill()
            self.on_logout(self._user)
            return
        
        self.protocol.send(uprot.unet_make_status_message(
            mode=uprot.UNetStatusMode.ERR,
            code=uprot.UNetStatusCode.EXC,
            message={
                'content': str(exception)
            }
        ))
        
        if isinstance(exception, NoSuchUNetCommandException) or isinstance(exception, UNetCommandIncompatibleArgumentException):
            logging.info(f"{self._user} issued invalid command '{exception.command_name} and raised error: {exception.message}")
            return

        traceback.print_exc()


class UNetAuthenticationHandler(MComConnectionHandler):
    def __init__(self, socket: socket, authenticated_handler=UNetAuthenticatedHandler, parent=None) -> None:
        self._authenticated_handler = authenticated_handler
        super().__init__(socket, parent)
    
    def main(self) -> None:
        init_msg = self.protocol.recv()
        init_json = json.loads(init_msg)

        if init_json['version'] != uprot.UNET_PROTOCOL_VERSION:
            self.protocol.send(uprot.unet_make_status_message(
                mode=uprot.UNetStatusMode.ERR,
                code=uprot.UNetStatusCode.VER,
                message={
                    'version': uprot.UNET_PROTOCOL_VERSION,
                    'content': "You're running an outdated version of the UNet protocol"
                }
            ))

        if init_json['type'] != uprot.UNetMessageType.AUTH:
            self.bad_request('Expected AUTH message')
            return
        
        if init_json['mode'] == uprot.UNetAuthMode.LOGIN:
            self.login(init_json)
            return
        
        if init_json['mode'] == uprot.UNetAuthMode.SIGNUP:
            self.signup(init_json)
            return

    def login(self, init_json):
        if UNetUserDatabase().exists(init_json['name'], init_json['password']) < 2:
            self.bad_request('No such user')
            return
        
        self.protocol.send(uprot.unet_make_status_message(
            mode=uprot.UNetStatusMode.OK,
            code=uprot.UNetStatusCode.DONE,
            message={
                'content': 'Login successful'
            }
        ))

        self.kill()
        self.on_login(init_json['name'])
        return self._authenticated_handler(socket=self.protocol.socket, parent=self.parent, user=init_json['name'])
    
    def signup(self, init_json):
        if not str(init_json['name']).replace('_', '').isalnum():
            return self.bad_request('Username contains invalid characters')
            return

        if UNetUserDatabase().exists(init_json['name'], init_json['password']) != 0:
            self.bad_request('User already exists')
            return
        
        self.protocol.send(uprot.unet_make_status_message(
            mode=uprot.UNetStatusMode.OK,
            code=uprot.UNetStatusCode.DONE,
            message={
                'content': 'Login successful'
            }
        ))

        UNetUserDatabase().add_user(init_json['name'], init_json['email'], init_json['password'])
        self.kill()
        self.on_signup(init_json['name'])
        return self._authenticated_handler(socket=self.protocol.socket, parent=self.parent, user=init_json['name'])

    def on_login(self, username: str):
        return
    
    def on_signup(self, username: str):
        return

    def bad_request(self, message: str):
        self.protocol.send(uprot.unet_make_status_message(
            mode=uprot.UNetStatusMode.ERR,
            code=uprot.UNetStatusCode.BAD,
            message={
                'content': message
            }
        ))

        self.kill()
    
    def on_exception(self, exception: Exception) -> None:
        self.protocol.send(uprot.unet_make_status_message(
            mode=uprot.UNetStatusMode.ERR,
            code=uprot.UNetStatusCode.EXC,
            message={
                'content': str(exception)
            }
        ))

        self.kill()
        return super().on_exception(exception)


class UNetServer(MComServer):
    def __init__(self, port=19055, connection_handler_class=UNetAuthenticationHandler) -> None:
        self._user_database = UNetUserDatabase()
        logging.basicConfig(format='[%(process)d]    [%(asctime)s  %(levelname)s]\t%(message)s', level=logging.INFO)
        super().__init__(port, connection_handler_class)

    @property
    def user_database(self):
        return self._user_database
