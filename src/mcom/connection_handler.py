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
from mcom.protocol import MComProtocol


class MComConnectionHandler:
    def __init__(self, socket: socket.socket, parent=None, thread_independent=True) -> None:
        self.protocol = MComProtocol(socket)
        self._alive = True
        self._finished = False
        self._parent = parent
        self._thread_independent = thread_independent

        self._scheduled = {}
        self.schedule(self.main) if thread_independent else None

    def _loop(self, target, *args, **kwargs) -> None:
        while self.alive and self._scheduled[target]:
            try:
                target(*args, **kwargs)
            except Exception as e:
                self.on_exception(e)

        self._finished = not self._alive

    def main(self) -> None:
        pass

    def on_exception(self, exception: Exception) -> None:
        raise exception
    
    def schedule(self, target=None, *args, **kwargs):
        self._scheduled.__setitem__(target, True)
        _mcom_loop_thread = threading.Thread(target=self._loop, args=(target, *args), kwargs=kwargs, daemon=self._thread_independent)
        _mcom_loop_thread.start()
        _mcom_loop_thread.join() if not self._thread_independent else None

    def kill(self, target=None) -> None:
        if target == None:
            self._alive = False
            return
        
        self._scheduled.__setitem__(target, False)

    def join(self):
        if self._thread_independent:
            raise NotImplementedError('Connection handler in thread-independent')
        
        self.schedule(self.main)

    @property
    def alive(self):
        return self._alive
    
    @property
    def parent(self):
        return self._parent

    @property
    def finished(self):
        return self._finished
