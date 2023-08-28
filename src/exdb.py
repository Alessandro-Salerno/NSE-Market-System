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
                'settled': {
                    'balance': balance,
                    'assets': assets
                },
                'orders': []
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
                'mid': None,
                'lastBid': None,
                'lastAsk': None,
                'depth': {
                    'bids': {},
                    'offers': {}
                }
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
        
        self.users[issuer].get_unsafe()['immediate']['orders'].append(str(order_id))

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
