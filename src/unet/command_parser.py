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


from unet.command import UNetCommand


class UNetCommandParseException(Exception):
    def __init__(self, command: str, position: int, message: str) -> None:
        self.message = message + f' (at char {position})'
        self.command = command
        self.position = position
        super().__init__(self.message)

    def to_string_frame(self):
        return f'UNetParseException: {self.message}\n{self.command}\n{" " * (self.position)}^'


class UNetCommandParser:
    def __init__(self, local_symbol='.') -> None:
        self._local_symbol = local_symbol
        self._command = None
        self._position = -1

    def parse(self, command: str) -> UNetCommand:
        self._command = command
        local, command = self._expect_start()
        arguments = []

        while self._position < len(self._command):
            arguments.append(self._expect_section())

        return UNetCommand(self._command, command, local=local, *arguments)

    def _current(self) -> chr:
        if self._position >= len(self._command):
            self._throw_exception('Unexpected EOL')
        
        return self._command[self._position]

    def _advance(self, units=1) -> None:
        self._position += units

    def _next(self) -> chr:
        self._advance()
        return self._current()
    
    def _expect_start(self):
        first = self._next()
        local = first == self.local_symbol
        command = ''

        if not local:
            command += first

        command += self._expect_section()
        return local, command

    def _expect_section(self) -> str:
        c = self._next()
        buffer = ''
        pos_offset = 0

        if chr(ord(c[0])).isnumeric():
            if pos_offset > 0:
                self._throw_exception('Unexpected Token')

        while c.isalnum() or c == '.':
            buffer += c
            self._advance()
            pos_offset += 1

            if not self._position < len(self._command):
                break

            c = self._current()
        
        if c == '"':
            if pos_offset > 0:
                self._throw_exception('Unexpected Token')
            
            c = self._next()
            while c != '"':
                buffer += c
                c = self._next()
        else:
            self._advance(-1)

        self._expect_space()
        return buffer   
    
    def _expect_space(self):
        self._advance()
        
        if self._position < len(self._command):
            if self._current().isspace():
                return
            
            self._throw_exception('Expected space or EOL')
        
    def _throw_exception(self, message: str) -> None:
        raise UNetCommandParseException(self._command, self._position, message)

    @property
    def local_symbol(self):
        return self._local_symbol


class UNetCommandParserFactory:
    def __init__(self, local_symbol='.') -> None:
        self._local_symbol = local_symbol

    def parse(self, command: str) -> UNetCommand:
        return UNetCommandParser(self.local_symbol).parse(command)

    @property
    def local_symbol(self):
        return self._local_symbol
