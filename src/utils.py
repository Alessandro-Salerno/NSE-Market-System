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


from datetime import datetime, timedelta
import pytz


def value_fmt(value):
    return '--' if value is None else value


def are_none(*values):
    res = True
    for val in values:
        res = res and val is not None
    return res


def today():
    now = datetime.now(tz=pytz.timezone('Europe/Rome'))
    return now.strftime('%Y-%m-%d')


def tomorrow():
    tmr = datetime.now(tz=pytz.timezone('Europe/Rome')) + timedelta(1)
    return tmr.strftime('%Y-%m-%d')


def now():
    now = datetime.now(tz=pytz.timezone('Europe/Rome'))
    return now.strftime('%Y-%m-%d %H:%M:%S')
