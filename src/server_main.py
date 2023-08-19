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


import json

from server_commands import ExchangePriviledgedCommandHandler, ExchangeUserCommandHandler
from unet.server import UNetAuthenticatedHandler, UNetAuthenticationHandler, UNetServer
from exdb import ExchangeDatabase
from scheduler import MarketScheduler
from global_market import GlobalMarket
from email_engine import EmailEngine


class ExchangeAuthenticatedHandler(UNetAuthenticatedHandler):
    def __init__(self, socket: any,
                 user: str,
                 user_command_handler=ExchangeUserCommandHandler(),
                 admin_command_handler=ExchangePriviledgedCommandHandler(),
                 parent=None) -> None:
        
        super().__init__(socket, user, user_command_handler, admin_command_handler, parent)


class ExchangeAuthenticationHandler(UNetAuthenticationHandler):
    def __init__(self, socket: any,
                 authenticated_handler=ExchangeAuthenticatedHandler,
                 parent=None) -> None:
        
        super().__init__(socket, authenticated_handler, parent)

    def on_login(self, username: str):
        ExchangeDatabase().add_user(username=username)

    def on_signup(self, username: str):
        ExchangeDatabase().add_user(username=username)


if __name__ == '__main__':
    print(
"""MC-UMSR-NSE-Market-System Copyright (C) 2023 Alessandro Salerno
This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
""")

    # Instantiate exchange database
    exdb = ExchangeDatabase()
    ee = EmailEngine()
    
    try:
        with open('settings.json', 'r') as file:
            settings = json.loads(file.read())
            ee.password = settings['googleAppPassword']
    except:
        with open('settings.json', 'w') as file:
            file.write(json.dumps({
                'googleAppPassword': ''
            }, indent=4))
            exit()

    mkt = GlobalMarket()
    server = UNetServer(connection_handler_class=ExchangeAuthenticationHandler)
    s = MarketScheduler()
    s.start_scheduler()
