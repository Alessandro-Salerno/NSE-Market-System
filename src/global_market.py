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


from gmpy2 import mpz
from order_matching.side import Side
from order_matching.execution import Execution

from unet.singleton import UNetSingleton

from exdb import EXCHANGE_DATABASE


class MarketIndex:
    def __init__(self, index=0) -> None:
        self.index = mpz(index)

    def next(self):
        self.index += 1
        return self.index
    
    def set(self, index):
        self.index = mpz(index)


class GlobalMarket(UNetSingleton):
    def __setup__(self):
        self.markets = {}
        self.orders = {}
        self.ready = False
        self.order_index = MarketIndex()

        for ticker in EXCHANGE_DATABASE.assets:
            if ticker not in self.markets:
                EXCHANGE_DATABASE.assets[ticker].get_unsafe()['immediate']['depth'] = EXCHANGE_DATABASE.asset()['immediate']['depth']
                self.create_market(ticker)

        if len(EXCHANGE_DATABASE.orders.keys()) > 0:
            final_id = 0
            for order_id, order in EXCHANGE_DATABASE.orders.items():
                final_id = max(final_id, int(order_id))
                self.order_index.set(int(order_id) - 1)
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

            self.order_index.set(final_id)
        self.ready = True

    def next_order_index(self):
        return self.order_index.next().digits()

    def add_limit_order(self, ticker, side, price, size, issuer):
        market = self.markets[ticker]
        return market.add_limit_order(side, size, price, issuer)
    
    def add_market_order(self, ticker, side, size, issuer):
        market = self.markets[ticker]
        return market.add_market_order(side, size, issuer)

    def cancel_order(self, order_id, issuer):
        return self.markets[EXCHANGE_DATABASE.orders[order_id]['ticker']].cancel_order(self.orders[order_id],
                                                                                                     issuer)
    
    def add_order(self, ticker: str, order):
        self.orders.__setitem__(order.order_id, order)

        if self.ready:
            EXCHANGE_DATABASE.add_order(order.order_id,
                                        'LIMIT' if order.execution == Execution.LIMIT
                                        else 'MARKET',
                                        order.trader_id,
                                        'BUY' if order.side == Side.BUY
                                        else 'SELL',
                                        ticker,
                                        order.size,
                                        order.price)

    def remove_order(self, order_id):
        EXCHANGE_DATABASE.users[self.orders[order_id].trader_id].get_unsafe()['immediate']['orders'].remove(order_id)
        self.orders.pop(order_id)
        EXCHANGE_DATABASE.orders.pop(order_id)

    def create_market(self, ticker):
        from market_manager import MarketManager
        self.markets.__setitem__(ticker, MarketManager(ticker))

    def remove_market(self, ticker):
        l = self.markets[ticker].close(delete=True)
        l.release()

    def close_market(self, ticker):
        l = self.markets[ticker].close(delete=False)
        l.release()

    def close_markets(self):
        for market in self.markets:
            self.close_market(market)

    def open_market(self, ticker):
        self.markets[ticker].open()
    
    def open_markets(self):
        for market in self.markets:
            self.open_market(market)
