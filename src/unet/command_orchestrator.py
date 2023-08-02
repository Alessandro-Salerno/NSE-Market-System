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


from unet.command import UNetCommand, NoSuchUNetCommandException, UNetCommandIncompatibleArgumentException
from mcom.protocol import MComProtocol
from unet.command_handler import UNetCommandHandler


class UNetCommandOrchestrator:
    def __init__(self, local_handler: UNetCommandHandler, remote: MComProtocol) -> None:
        self._local_handler = local_handler
        self._remote = remote
    
    def call_command(self, command: UNetCommand) -> any:
        if command.local:
            return self._local_handler.call_command(command)
        
        return self._remote.send(command.command_stirng)

    @property
    def local_handler(self):
        return self._local_handler
    
    @property
    def remote(self):
        return self._remote
