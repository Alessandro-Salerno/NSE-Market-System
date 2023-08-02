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


class UNetCommand:
    def __init__(self, command_string: str, command_name: str, *args, local=False) -> None:
        self._command_string = command_string
        self._command_name = command_name
        self._arguments = args
        self._local = local

    @property
    def command_stirng(self):
        return self._command_string

    @property
    def command_name(self):
        return self._command_name
    
    @property
    def arguments(self):
        return self._arguments
    
    @property
    def local(self):
        return self._local


class NoSuchUNetCommandException(Exception):
    def __init__(self, name: str) -> None:
        self.message = f'No matching command could be found for \'{name}\''
        self.command_name = name
        super().__init__(self.message)


class UNetCommandIncompatibleArgumentException(Exception):
    def __init__(self, name: str, argc: int, given_argc: int) -> None:
        self.message = f'UNet Command \'{name}\' requires {argc} positional argument(s). {given_argc} given'
        self.command_name = name
        self.required_arguments = argc
        self.given_arguments = given_argc
        super().__init__(self.message)
