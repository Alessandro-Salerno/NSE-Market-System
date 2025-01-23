# NSE Market System
# Copyright (C) 2023 - 2025 Alessandro Salerno

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
import inspect


def unet_command(*names):
    def inner(handler):
        handler._unet_command_handler = True
        handler._unet_command_argc = len(inspect.signature(handler).parameters) - 2
        handler._unet_command_names = list()
        for name in names:
            handler._unet_command_names.append(name)
        return handler
    
    return inner


class UNetCommandHandler:
    def __init__(self) -> None:
        self._commands = dict()
        self._parent = None
        self._top = None

        for attr in dir(self):
            concrete = getattr(self, attr)
            if hasattr(concrete, '_unet_command_handler'):
                for name in concrete._unet_command_names:
                    self._commands.__setitem__(name, concrete)

    def get_command(self, name: str) -> any: 
        try:
            return self._commands[name]
        except KeyError as ke:
            raise NoSuchUNetCommandException(name)
    
    def call_command(self, command: UNetCommand) -> any:
        handler = self.get_command(command.command_name)
        
        if handler._unet_command_argc != len(command.arguments):
            raise UNetCommandIncompatibleArgumentException(command.command_name, handler._unet_command_argc, len(command.arguments))
        
        return handler(command, *command.arguments)
    
    @property
    def parent(self):
        return self._parent

    @property
    def top(self):
        return self._top
