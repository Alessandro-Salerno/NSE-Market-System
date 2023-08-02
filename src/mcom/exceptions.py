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


class MComSendException(Exception):
    def __init__(self, message_size: int, header_size: int, sent_bytes: int, *args: object) -> None:
        super().__init__(f'Could only send {sent_bytes} byte(s) of {message_size + header_size} byte(s) with header of size {header_size} byte(s)')
        self.message_size = message_size
        self.header_size = header_size
        self.total_size = message_size + header_size
        self.sent_bytes = sent_bytes
