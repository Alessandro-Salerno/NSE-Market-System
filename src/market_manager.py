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
from datetime import datetime, timedelta
from gmpy2 import mpz, mpfr

from order_matching.side import Side
from order_matching.order import LimitOrder, MarketOrder, Order
from order_matching.execution import Execution
from order_matching.status import Status

from object_lock import ObjectLock
from global_market import GlobalMarket
from platformdb import PlatformDB
from exdb import EXCHANGE_DATABASE

from matching_layer import MatchingLayer


class MarketManager:
    def __init__(self, ticker: str):
        self._ticker = ticker
        self._tradable = True
        self._engine_lock = ObjectLock(MatchingLayer(sum([ord(c) for c in ticker])))

    def add_limit_order(self, side, size, price, issuer):
        order = LimitOrder(side=side,
                           price=price,
                           size=size,
                           order_id=GlobalMarket().next_order_index(),
                           trader_id=issuer,
                           timestamp=datetime.now(),
                           expiration=datetime.now() + timedelta(days=365),
                           price_number_of_digits=3)

        with self._engine_lock as engine:
            if not self._tradable:
                return
            
            trades = engine.place(order)
            self.update_asset(order, engine)
            GlobalMarket().add_order(self._ticker, order)
            self.transact(trades=trades, engine=engine)

        return order

    def add_market_order(self, side, size, issuer):
        order = MarketOrder(side=side,
                            size=size,
                            order_id=GlobalMarket().next_order_index(),
                            trader_id=issuer,
                            timestamp=datetime.now(),
                            expiration=datetime.now() + timedelta(days=365))

        with self._engine_lock as engine:
            if not self._tradable:
                return
            
            trades = engine.place(order)
            self.update_asset(order, engine)
            GlobalMarket().add_order(self._ticker, order)
            self.transact(trades=trades, engine=engine)
        
        return order

    def cancel_order(self, order, issuer):
        if order.trader_id != issuer:
            return -2
        
        with self._engine_lock as engine:
            try:
                    engine.delete(order)
                    order.status = Status.CANCEL
                    order.size = 0
                    self.update_asset(order, engine)
                    GlobalMarket().remove_order(order.order_id)
            except KeyError as ke:
                return -1

    def update_asset(self, order: Order, engine: MatchingLayer):
        # Assignign variables outside to save on lock time
        side = 'bids' if order.side == Side.BUY else 'offers'
        level = str(order.price)

        with EXCHANGE_DATABASE.assets[self._ticker] as asset:
            session_data = asset['sessionData']
            immediate = asset['immediate']

            if order.side == Side.SELL:
                session_data['sellVolume'] += order.size
            else:
                session_data['buyVolume'] += order.size

            immediate['bid'] = engine.max_bid()
            immediate['ask'] = engine.min_offer()
            immediate['mid'] = engine.current_price()
            immediate['lastBid'] = engine.last_bid()
            immediate['lastAsk'] = engine.last_offer()
            immediate['bidVolume'] = engine.max_bid_size()
            immediate['askVolume'] = engine.min_offer_size()

            depth = immediate['depth'][side]

            if order.status == Status.CANCEL:
                depth[level] -= order.left
                if depth[level] <= 0:
                    depth.pop(level)
            elif order.left == order.size:
                depth.__setitem__(level, depth.setdefault(level, 0) + order.size)

            if session_data['open'] == None:
                session_data['open'] = immediate['mid']

    def transact(self, trades, engine: MatchingLayer):
        if trades == None:
            return

        for trade in trades:
            sell_order_id = None
            buy_order_id = None

            depth_side = None
            level = str(trade.price)

            match (trade.side):
                case Side.SELL:
                    sell_order_id = trade.incoming_order_id
                    buy_order_id = trade.book_order_id
                    depth_side = 'bids'

                case Side.BUY:
                    sell_order_id = trade.book_order_id
                    buy_order_id = trade.incoming_order_id
                    depth_side = 'offers'

            sell_order: Order = GlobalMarket().orders[sell_order_id]
            buy_order: Order = GlobalMarket().orders[buy_order_id]

            sell_price = sell_order.price
            buy_price = buy_order.price

            if sell_order.execution == Execution.MARKET and buy_order.execution == Execution.MARKET:
                sell_price = engine.last_available_bid()
                buy_price = engine.last_available_ask()
                if buy_price < sell_price:
                    bp = buy_price
                    buy_price = sell_price
                    sell_price = bp
                trade.price = buy_price
            else:
                with EXCHANGE_DATABASE.assets[self._ticker] as asset:
                    sz = round(trade.price * trade.size, 3)
                    GlobalMarket().orders[trade.incoming_order_id].fill_cost += sz
                    asset['sessionData']['tradedValue'] = round(asset['sessionData']['tradedValue'] + sz, 2)
                    d = asset['immediate']['depth'][depth_side]
                    d[level] -= trade.size
                    if d[level] <= 0:
                        d.pop(level)
            
            seller = sell_order.trader_id
            buyer = buy_order.trader_id

            if sell_price <= 0:
                sell_price = buy_price
            if buy_price == float('inf'):
                buy_price = sell_price

            with EXCHANGE_DATABASE.users[buyer] as b:
                assets = b['immediate']['current']['assets']
                assets[self._ticker] += trade.size
                if assets[self._ticker] == 0:
                    assets.pop(self._ticker)
                b['immediate']['current']['balance'] = round(b['immediate']['current']['balance'] - round(buy_price * trade.size, 3), 3)
            
            with EXCHANGE_DATABASE.users[seller] as s:
                assets = s['immediate']['current']['assets']
                assets[self._ticker] -= trade.size
                if assets[self._ticker] == 0:
                    assets.pop(self._ticker)
                s['immediate']['current']['balance'] = round(s['immediate']['current']['balance'] + round(sell_price * trade.size, 3), 3)

            EXCHANGE_DATABASE.update_order(buy_order.order_id, buy_order.size)
            EXCHANGE_DATABASE.update_order(sell_order.order_id, sell_order.size)

            buy_order.left -= trade.size
            sell_order.left -= trade.size

            if buy_order.left == 0:
                GlobalMarket().remove_order(buy_order_id)
            if sell_order.left == 0:
                GlobalMarket().remove_order(sell_order_id)

    def close(self, delete=False):
        if delete:
            for order_id in EXCHANGE_DATABASE.orders.copy():
                self.cancel_order(GlobalMarket().orders[order_id], GlobalMarket().orders[order_id].trader_id)

        self._engine_lock._lock.acquire()

        # I know... i know
        if delete:
            with EXCHANGE_DATABASE.assets[self._ticker] as asset:
                with open(f'{self._ticker}.save.json', 'w') as file:
                    file.write(json.dumps(PlatformDB.to_dict(asset)))
                EXCHANGE_DATABASE.assets.pop(self._ticker)
                EXCHANGE_DATABASE.asset_classes[asset['info']['class']].remove(self._ticker)
        self._tradable = False
        return self._engine_lock._lock

    def open(self):
        with self._engine_lock as _:
            self._tradable = True
