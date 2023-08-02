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


class ObjectLock:
    def __init__(self, target) -> None:
        self._target = target
        self._lock = threading.Lock()

    def __enter__(self):
        self._lock.acquire()
        return self._target

    def __exit__(self, *args, **kwargs):
        self._lock.release()
    
    def get_unsafe(self):
        return self._target

    @property
    def lock(self):
        return self._lock
