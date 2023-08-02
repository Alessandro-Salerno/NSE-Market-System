import socket
from mcom.exceptions import MComSendException


class MComProtocol:
    def __init__(self, socket: socket.socket) -> None:
        self.socket = socket
    
    def send(self, message: str) -> None:
        encoded = message.encode('utf-8')
        msgsz = len(encoded)
        byte_msgsz = msgsz.to_bytes(length=3, byteorder='little', signed=False)
        sent = self.socket.send(byte_msgsz)
        sent += self.socket.send(encoded)

        if sent != msgsz + 3:
            raise MComSendException(msgsz, 3, sent)
        
    def recv(self) -> str:
        msgsz = int.from_bytes(self.socket.recv(3), byteorder='little', signed=False)
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
