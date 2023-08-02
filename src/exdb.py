from platformdb import PlatformDB
from unet.singleton import UNetSingleton
from object_lock import ObjectLock
import utils


class ExchangeDatabase(UNetSingleton):
    def __setup__(self) -> None:
        self.db = PlatformDB(filename='exchange.json', schema={
            'usersByName': self.user(),
            'assetsByTicker': self.asset(),
            'assetsByClass': {},
            'ordersById': self.order()
        })

        self.db.db.setdefault('openDate', utils.today())
        self.db.timer.start()

    def user(self,
             balance=0,
             assets={}):
        return {
            'immediate': {
                'current': {
                    'balance': 0,
                    'assets': {}
                },
                'setled': {
                    'balance': balance,
                    'assets': assets
                },
            },
            'history': {
                'assets': {},
                'balance': {}
            }
        }
    
    def asset(self,
              ticker=None,
              aclass=None,
              issuer='admin'):
        return {
            'info': {
                'class': aclass,
                'issuer': issuer,
                'outstandingUnits': 1
            },
            'immediate': {
                'bid': None,
                'ask': None,
                'bidVolume': None,
                'askVolume': None,
                'averagePrice': None,
                'lastBid': None,
                'lastAsk': None,
                'imbalance': 0
            },
            'sessionData': {
                'buyVolume': 0,
                'sellVolume': 0,
                'tradedValue': 0,
                'previousClose': None,
                'open': None,
                'close': None,
            },
            'history': {
                'today': {},
                'intraday': {},
                'daily': {}
            }
        }
    
    def order(self,
              execution=None,
              issuer=None,
              side=None,
              ticker=None,
              size=None,
              price=None):
        return {
            'execution': execution,
            'ticker': ticker,
            'issuer': issuer,
            'side': side,
            'size': size,
            'price': price
        }
    
    def add_user(self,
                 username: str,
                 balance=0,
                 assets={}):
        
        userdb = self.db.db['usersByName']
        if username in userdb.keys():
            return False
        
        userdb.__setitem__(username, ObjectLock(self.user(balance=balance,
                                                            assets=assets)))
        return True

    def add_asset(self,
                  ticker: str,
                  aclass: str,
                  issuer='admin'):
        
        tickerdb = self.db.db['assetsByTicker']
        classdb = self.db.db['assetsByClass']

        if ticker in tickerdb.keys():
            return False
    
        tickerdb.__setitem__(ticker, ObjectLock(self.asset(ticker=ticker,
                                                            aclass=aclass,
                                                            issuer=issuer)))
        classdb.setdefault(aclass, []).append(ticker)
        return True
    
    def add_order(self,
                  order_id,
                  execution=None,
                  issuer=None,
                  side=None,
                  ticker=None,
                  size=None,
                  price=None):
        
        if str(order_id) in self.orders.keys():
            return False

        self.orders.__setitem__(str(order_id), ObjectLock(self.order(execution,
                                                                issuer,
                                                                side,
                                                                ticker,
                                                                size,
                                                                price)))
        return True
        
    def update_order(self,
                     order_id,
                     size):
        
        with self.orders[str(order_id)] as order:
            order['size'] = size
    
    def get_open_date(self):
        return self.db.db['openDate']
    
    def set_open_date(self, date):
        self.db.db['openDate'] = date

    def user_is_issuer(self, username, asset):
        return asset['info']['issuer'] == username or asset['info']['issuer'] == '*'
    
    @property
    def users(self):
        return self.db.db['usersByName']
    
    @property
    def assets(self):
        return self.db.db['assetsByTicker']
    
    @property
    def asset_classes(self):
        return self.db.db['assetsByClass']
    
    @property
    def orders(self):
        return self.db.db['ordersById']
