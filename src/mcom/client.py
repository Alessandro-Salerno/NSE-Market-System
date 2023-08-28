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
from mcom.connection_handler import MComConnectionHandler


class MComClient:
    def __init__(self, server_address: str, server_port=19055, connection_handler_class=MComConnectionHandler) -> None:
        self._server_address = server_address
        self._server_port = server_port
        
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((server_address, server_port))

        self.on_connect()
        self._connection = connection_handler_class(socket=self._socket, parent=self, thread_independent=False)
        self.post_connect()

    def on_connect(self):
        pass

    def post_connect(self):
        pass

    @property
    def server_address(self):
        return self._server_address
    
    @property
    def server_port(self):
        return self._server_port
