import json

from mcom.connection_handler import MComConnectionHandler
from mcom.client import MComClient
from mcom.protocol import MComProtocol

from unet.command_orchestrator import UNetCommandOrchestrator
from unet.command_handler import UNetCommandHandler
import unet.protocol as uprot


class UNetClientConnectionMode:
    def __init__(self, mode: str, name: str, email: str, password: str) -> None:
        self._mode = mode
        self._name = name
        self._email = email
        self._password = password
    
    @property
    def mode(self):
        return self._mode
    
    @property
    def name(self):
        return self._name
    
    @property
    def email(self):
        return self._email

    @property
    def password(self):
        return self._password


class UNetClient(MComClient):
    def __init__(self,
                 conn_mode: UNetClientConnectionMode,
                 local_command_handler: UNetCommandHandler,
                 server_address: str,
                 server_port=19055,
                 connection_handler_class=MComConnectionHandler) -> None:
        
        self._conn_mode = conn_mode
        self._local_command_handler = local_command_handler
        self._local_command_handler._top = self
        super().__init__(server_address, server_port, connection_handler_class)
        self._local_command_handler._parent = self._connection

    def on_connect(self):
        protocol = MComProtocol(self._socket)
        self._command_orchestrator = UNetCommandOrchestrator(self._local_command_handler, protocol)
        
        protocol.send(uprot.unet_make_auth_message(
            mode=self.conn_mode.mode,
            name=self.conn_mode.name,
            email=self.conn_mode.email,
            password=self.conn_mode.password
        ))

    @property
    def command_orchestrator(self):
        if not hasattr(self, '_command_orchestrator'):
            return None
        
        return self._command_orchestrator

    @property
    def conn_mode(self):
        return self._conn_mode
