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


from datetime import datetime
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

        for ticker in ExchangeDatabase().assets:
            if ticker not in self.markets:
                self.create_market(ticker)

        if len(ExchangeDatabase().orders.keys()) > 0:
            final_id = 0
            for order_id in ExchangeDatabase().orders:
                final_id = max(final_id, int(order_id))
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

            self.order_index.get_unsafe().set(final_id)
        self.ready = True


    def get_order_index(self):
        with self.order_index as oi:
            return oi.index
        
    def next_order_index(self):
        with self.order_index as oi:
            return oi.next()

    def add_limit_order(self, ticker, side, price, size, issuer):
        market = self.markets[ticker]
        return market.add_limit_order(side, size, price, issuer)
    
    def add_market_order(self, ticker, side, size, issuer):
        market = self.markets[ticker]
        return market.add_market_order(side, size, issuer)

    def cancel_order(self, order_id, issuer):
        try:
            if order_id not in self.orders.keys():
                return -1
            
            with ExchangeDatabase().orders[str(order_id)] as order:
                if self.orders[order_id].trader_id != issuer:
                    return -2
                
                self.markets[order['ticker']].cancel_order(self.orders[order_id])
                self.remove_order(order_id)
        except KeyError as ke:
            return -1
        except Exception as e:
            raise e
    
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

    def create_market(self, ticker):
        from market_manager import MarketManager
        self.markets.__setitem__(ticker, MarketManager(ticker))
