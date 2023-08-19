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


from order_matching.side import Side
from order_matching.execution import Execution

from unet.singleton import UNetSingleton

from exdb import ExchangeDatabase
from object_lock import ObjectLock


class MarketIndex:
    def __init__(self, index=0) -> None:
        self.index = index

    def next(self):
        self.index += 1
        return self.index
    
    def set(self, index):
        self.index = index


class GlobalMarket(UNetSingleton):
    def __setup__(self):
        self.markets = {}
        self.orders = {}
        self.ready = False
        self.order_index = ObjectLock(MarketIndex())

        final_id = 0
        for order_id in ExchangeDatabase().orders:
            final_id = int(order_id) if int(order_id) > final_id else final_id
            self.order_index.get_unsafe().set(int(order_id) - 1)
            with ExchangeDatabase().orders[order_id] as order:
                match (order['execution']):
                    case 'LIMIT':
                        self.add_limit_order(order['ticker'],
                                             Side.BUY if order['side'] == 'BUY'
                                             else Side.SELL,
                                             order['price'],
                                             order['size'],
                                             order['issuer'])

                    case 'MARKET':
                        self.add_market_order(order['ticker'],
                                              Side.BUY if order['side'] == 'BUY'
                                              else Side.SELL,
                                              order['size'],
                                              order['issuer'])
        
        for ticker in ExchangeDatabase().assets:
            if ticker not in self.markets:
                from market_manager import MarketManager
                self.markets.__setitem__(ticker, MarketManager(ticker))

        self.order_index.get_unsafe().set(final_id)
        self.ready = True


    def get_order_index(self):
        with self.order_index as oi:
            return oi.index
        
    def next_order_index(self):
        with self.order_index as oi:
            return oi.next()

    def add_limit_order(self, ticker, side, price, size, issuer):
        from market_manager import MarketManager
        market: MarketManager = self.markets.setdefault(ticker, MarketManager(ticker))
        o = market.add_limit_order(side, size, price, issuer)
        return o
    
    def add_market_order(self, ticker, side, size, issuer):
        from market_manager import MarketManager
        market: MarketManager = self.markets.setdefault(ticker, MarketManager(ticker))
        o = market.add_market_order(side, size, issuer)
        return o

    def cancel_order(self, order_id, issuer):
        if order_id not in self.orders.keys():
            return -2
        
        with ExchangeDatabase().orders[str(order_id)] as order:
            if self.orders[order_id].trader_id != issuer:
                return -3
            
            self.markets[order['ticker']].cancel_order(self.orders[order_id])
            self.remove_order(order_id)
    
    def add_order(self, ticker: str, order):
        self.orders.__setitem__(order.order_id, order)

        if self.ready:
            ExchangeDatabase().add_order(order.order_id,
                                        'LIMIT' if order.execution == Execution.LIMIT
                                        else 'MARKET',
                                        order.trader_id,
                                        'BUY' if order.side == Side.BUY
                                        else 'SELL',
                                        ticker,
                                        order.size,
                                        order.price)

    def remove_order(self, order_id):
        ExchangeDatabase().users[self.orders[order_id].trader_id].get_unsafe()['immediate']['orders'].remove(str(order_id))
        self.orders.pop(order_id)
        ExchangeDatabase().orders.pop(str(order_id))
