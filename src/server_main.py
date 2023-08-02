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
