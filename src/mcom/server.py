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


import threading
import socket
from mcom.connection_handler import MComConnectionHandler


class MComServer:
    def __init__(self, port=19055, connection_handler_class=MComConnectionHandler) -> None:
        self._port = port
        self._connection_handler_class = connection_handler_class
        self._alive = True
        
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('127.0.0.1', port))

        self._listen_thread = threading.Thread(target=self._listen, daemon=True)
        self._listen_thread.start()

        self._connections = []
        self._finished = False

    def _listen(self) -> None:
        self._server_socket.listen()

        while True:
            try: 
                connection, address = self._server_socket.accept()
                self._on_connect(connection, address)
            except Exception as e:
                self.on_exception(e)

        self._finished = True

    def _on_connect(self, connectioN: socket.socket, address) -> None:
        self._connections.append(self.on_connect(connection=connectioN, address=address))

    def on_connect(self, connection: socket.socket, address) -> MComConnectionHandler:
        return self._connection_handler_class(socket=connection, parent=self)

    def on_exception(self, exception: Exception) -> None:
        raise exception

    def kill(self) -> None:
        self._alive = False
        for conn in self._connections:
            conn.kill()

    @property
    def port(self):
        return self._port
    
    @property
    def connection_handler_class(self):
        return self._connection_handler_class
    
    @property
    def alive(self):
        return self._alive
    
    @property
    def finished(self):
        return self._finished

