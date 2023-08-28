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

from order_matching.matching_engine import MatchingEngine
from order_matching.orders import Orders
from order_matching.side import Side
from order_matching.order import LimitOrder, MarketOrder, Order
from order_matching.execution import Execution

from object_lock import ObjectLock
from global_market import GlobalMarket
from exdb import ExchangeDatabase

from matching_layer import MatchingLayer


class MarketManager:
    def __init__(self, ticker: str):
        self._ticker = ticker
        self._engine_lock = ObjectLock(MatchingLayer(sum([ord(c) for c in ticker])))

    def add_limit_order(self, side, size, price, issuer):
        with self._engine_lock as engine:
            order = LimitOrder(side=side,
                               price=price,
                               size=int(size),
                               order_id=GlobalMarket().next_order_index(),
                               trader_id=issuer,
                               timestamp=datetime.now(),
                               expiration=datetime.now() + timedelta(days=365),
                               price_number_of_digits=3)
            
            trades = engine.place(order)
            self.update_asset(order, engine)
            GlobalMarket().add_order(self._ticker, order)
            self.transact(trades=trades)

            return order

    def add_market_order(self, side, size, issuer):
        with self._engine_lock as engine:
            order = MarketOrder(side=side,
                                size=int(size),
                                order_id=GlobalMarket().next_order_index(),
                                trader_id=issuer,
                                timestamp=datetime.now(),
                                expiration=datetime.now() + timedelta(days=365))
            
            trades = engine.place(order)
            self.update_asset(order, engine)
            GlobalMarket().add_order(self._ticker, order)
            self.transact(trades=trades)
            
            return order

    def cancel_order(self, order):
        with self._engine_lock as engine:
            engine.delete(order)
            order.size = 0
            order.left = 0
            self.update_asset(order, engine)

    def update_asset(self, order: Order, engine: MatchingLayer):
        with ExchangeDatabase().assets[self._ticker] as asset:
            session_data = asset['sessionData']
            immediate = asset['immediate']

            if order.side == Side.SELL:
                session_data['sellVolume'] += order.size
            else:
                session_data['buyVolume'] += order.size

            immediate['lastAsk'] = immediate['ask'] if immediate['ask'] is not None \
                    and immediate['ask'] != engine.min_offer() else immediate['lastAsk']

            immediate['lastBid'] = immediate['bid'] if immediate['bid'] is not None and \
                     immediate['bid'] != engine.max_bid() else immediate['lastBid']

            immediate['bid'] = engine.max_bid()
            immediate['ask'] = engine.min_offer()
            immediate['mid'] = engine.current_price()
            immediate['bidVolume'] = engine.max_bid_size()
            immediate['askVolume'] = engine.min_offer_size()

            immediate['depth']['bids'] = { str(price): sum([order.size for order in orders]) for price, orders in engine._engine.unprocessed_orders.bids.items() }
            immediate['depth']['offers'] = { str(price): sum([order.size for order in orders]) for price, orders in engine._engine.unprocessed_orders.offers.items() }

            if session_data['open'] == None:
                session_data['open'] = immediate['mid']

    def transact(self, trades):
        if trades == None:
            return

        for trade in trades:
            sell_order_id = None
            buy_order_id = None

            if trade.side == Side.SELL:
                sell_order_id = trade.incoming_order_id
                buy_order_id = trade.book_order_id

            if trade.side == Side.BUY:
                sell_order_id = trade.book_order_id
                buy_order_id = trade.incoming_order_id

            sell_order: Order = GlobalMarket().orders[sell_order_id]
            buy_order: Order = GlobalMarket().orders[buy_order_id]

            sell_order_original_price = sell_order.price
            buy_order_original_price = buy_order.price

            # Very ugly code to be refactored
            # I saw this bug too late sorry
            # Hope comments help
            if sell_order.execution == Execution.MARKET and buy_order.execution == Execution.MARKET:
                with ExchangeDatabase().assets[self._ticker] as asset:
                    # If there's no market
                    if asset['immediate']['bid'] == None or asset['immediate']['ask'] == None:
                        # If there was no market before
                        if asset['immediate']['lastBid'] == None or asset['immediate']['lastAsk'] == None:
                            # And if there has never been a market
                            if asset['sessionData']['previousClose'] == None:
                                # Transaction happens at price 0 on both sides
                                sell_order.price = 0
                                buy_order.price = 0
                            else:
                                # if there is a reference for last clsoe the transaction happens at that price on both sides
                                sell_order.price = asset['sessionData']['previousClose']
                                buy_order.price = asset['sessionData']['previousClose']
                        else:
                            # If, instead, there was a merket, then the transaction happens at inverted prices
                            sell_order.price = min(asset['immediate']['lastAsk'], asset['immediate']['lastBid'])
                            buy_order.price = max(asset['immediate']['lastAsk'], asset['immediate']['lastBid'])
                    else:
                        # Finally, if there was a price all along and the engine just didn't catch it, the transaction happens at inverted prices
                        sell_order.price = min(asset['immediate']['ask'], asset['immediate']['bid'])
                        buy_order.price = max(asset['immediate']['ask'], asset['immediate']['bid'])

            if sell_order.price <= 0:
                sell_order.price = buy_order.price

            if buy_order.price == float('inf'):
                buy_order.price = sell_order.price

            seller = sell_order.trader_id
            buyer = buy_order.trader_id

            with ExchangeDatabase().users[buyer] as b:
                assets = b['immediate']['current']['assets']
                if self._ticker in assets:
                    assets[self._ticker] += trade.size
                else:
                    assets.__setitem__(self._ticker, trade.size)
                if assets[self._ticker] == 0:
                    assets.pop(self._ticker)
                b['immediate']['current']['balance'] = round(b['immediate']['current']['balance'] - round(buy_order.price * trade.size, 3), 3)
            
            with ExchangeDatabase().users[seller] as s:
                assets = s['immediate']['current']['assets']
                if self._ticker in assets:
                    assets[self._ticker] -= trade.size
                else:
                    assets.__setitem__(self._ticker, trade.size * -1)
                if assets[self._ticker] == 0:
                    assets.pop(self._ticker)
                s['immediate']['current']['balance'] = round(s['immediate']['current']['balance'] + round(sell_order.price * trade.size, 3), 3)

            ExchangeDatabase().update_order(buy_order.order_id, buy_order.size)
            ExchangeDatabase().update_order(sell_order.order_id, sell_order.size)

            buy_order.left -= trade.size
            sell_order.left -= trade.size

            if not buy_order.left > 0:
                GlobalMarket().remove_order(buy_order_id)
            else:
                buy_order.price = buy_order_original_price

            if not sell_order.left > 0:
                GlobalMarket().remove_order(sell_order_id)
            else:
                sell_order.price = sell_order_original_price

            with ExchangeDatabase().assets[self._ticker] as asset:
                asset['sessionData']['tradedValue'] = round(asset['sessionData']['tradedValue'] + round(trade.price * trade.size, 2), 2)
