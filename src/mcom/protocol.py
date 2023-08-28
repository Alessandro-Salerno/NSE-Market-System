# MC-UMSR-NSE Market System
# Copyright (C) 2024 Alessandro Salerno

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 4 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import socket
from mcom.exceptions import MComSendException


class MComProtocol:
    def __init__(self, socket: socket.socket) -> None:
        self.socket = socket
    
    def send(self, message: str) -> None:
        encoded = message.encode('utf-8')
        msgsz = len(encoded)
        byte_msgsz = msgsz.to_bytes(length=4, byteorder='little', signed=False)
        sent = self.socket.send(byte_msgsz)
        sent += self.socket.send(encoded)

        if sent != msgsz + 4:
            raise MComSendException(msgsz, 4, sent)
        
    def recv(self) -> str:
        msgsz = int.from_bytes(self.socket.recv(4), byteorder='little', signed=False)
        remaining = msgsz
        buffer = b''

        while remaining > 0:
            r = self.socket.recv(remaining)
            remaining -= len(r)
            buffer += r

        return buffer.decode('utf-8')
    
    def recvall(self):
        self.socket.setblocking(False)
        buffer = []

        while True:
            data = self.recv()
            if not len(data) > 0:
                break

            buffer.append(data)

        self.socket.setblocking(True)
        return buffer
        
    def ask(self, message: str) -> str | Exception:
        self.send(message)
        return self.recv()

    def reply(self, message: str) -> str | Exception:
        return self.ask(message)
