import socket
from mcom.connection_handler import MComConnectionHandler


class MComClient:
    def __init__(self, server_address: str, server_port=19055, connection_handler_class=MComConnectionHandler) -> None:
        self._server_address = server_address
        self._server_port = server_port
        
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((server_address, server_port))

        self.on_connect()
        self._connection = connection_handler_class(socket=self._socket, parent=self)

    def on_connect(self):
        pass

    @property
    def server_address(self):
        return self._server_address
    
    @property
    def server_port(self):
        return self._server_port
