from datetime import datetime

from order_matching.matching_engine import MatchingEngine
from order_matching.side import Side
from order_matching.order import Order
from order_matching.orders import Orders


class MatchingLayer:
    def __init__(self, seed: int) -> None:
        self._engine = MatchingEngine(seed)
        self._max_bid = None
        self._min_offer = None
        self._max_bid_size = None
        self._min_offer_size = None
        self._max_bid_ids = []
        self._min_offer_ids = []

    def max_bid(self):
        return self._max_bid
    
    def min_offer(self):
        return self._min_offer
    
    def max_bid_size(self):
        return self._max_bid_size
    
    def min_offer_size(self):
        return self._min_offer_size
    
    def current_price(self):
        return round((self._max_bid + self._min_offer) / 2, 3) \
                        if self._max_bid != None and self._min_offer != None else None
    
    def imbalance(self):
        return self._engine.unprocessed_orders.get_imbalance()

    def place(self, order: Order):
        order.left = order.size

        if not self._matching_order_exists(order):
            self._engine.unprocessed_orders.append(order)
            self._update_quotes_unmatched(order)
            return
        
        match (order.side):
            case Side.SELL:
                self._max_bid_size -= order.size

            case Side.BUY:
                self._min_offer_size -= order.size

        trades = self._engine.match(datetime.now(), Orders([order]))
        self._update_quotes_matched(order)

        if order.size > 0:
            self._update_quotes_unmatched(order)

        return trades.trades
    
    def delete(self, order: Order):
        self._engine.unprocessed_orders.remove(order)
        if int(order.order_id) not in self._max_bid_ids and int(order.order_id) not in self._min_offer_ids:
            return

        match (order.side):
            case Side.SELL:
                self._min_offer_ids.remove(int(order.order_id))
                self._min_offer_size -= order.size
                self._recompute_offers()

            case Side.BUY:
                self._max_bid_ids.remove(int(order.order_id))
                self._max_bid_size -= order.size
                self._recompute_bids()

    def _matching_order_exists(self, order: Order):
        match (order.side):
            case Side.SELL:
                return self._max_bid != None and self._max_bid >= order.price
            
            case Side.BUY:
                return self._min_offer != None and self._min_offer <= order.price
            
    def _update_quotes_unmatched(self, order: Order):
        match (order.side):
            case Side.SELL:
                if order.price == self._min_offer:
                    self._min_offer_size += order.size
                    self._min_offer_ids.append(int(order.order_id))

                if self._min_offer == None or order.price < self._min_offer:
                    self._min_offer = order.price
                    self._min_offer_size = order.size
                    self._min_offer_ids = [int(order.order_id),]

            case Side.BUY:
                if order.price == self._max_bid:
                    self._max_bid_size += order.size
                    self._max_bid_ids.append(int(order.order_id))

                if self._max_bid == None or order.price > self._max_bid:
                    self._max_bid = order.price
                    self._max_bid_size = order.size
                    self._max_bid_ids = [int(order.order_id),]
    
    def _update_quotes_matched(self, order: Order):
        match (order.side):
            case Side.SELL:
                self._recompute_bids()

            case Side.BUY:
                self._recompute_offers()

    def _recompute_bids(self):
        if self._max_bid_size <= 0:
            self._max_bid = self._engine.unprocessed_orders.max_bid
            if self._max_bid in self._engine.unprocessed_orders.bids:
                orders = self._engine.unprocessed_orders.bids[self._max_bid]
                self._max_bid_size = sum([o.size for o in orders])
                self._max_bid_ids = [int(o.order_id) for o in orders]
            else:
                self._max_bid_size = None
                self._max_bid_ids = []
            self._fix_quotes()

    def _recompute_offers(self):
        if self._min_offer_size <= 0:
            self._min_offer = self._engine.unprocessed_orders.min_offer
            if self._min_offer in self._engine.unprocessed_orders.offers:
                orders = self._engine.unprocessed_orders.offers[self._min_offer]
                self._min_offer_size = sum([o.size for o in orders])
                self._min_offer_ids = [int(o.order_id) for o in orders]
            else:
                self._min_offer_size = None
                self._min_offer_ids = []
            self._fix_quotes()
    
    def _fix_quotes(self):
        if self._max_bid == float('inf') or self._max_bid == float('nan') or self._max_bid_size == None or self._max_bid_size <= 0:
            self._max_bid = None
        if self._min_offer_size == float('inf') or self._min_offer == float('nan') or self._min_offer_size == None or self._min_offer_size <= 0:
            self._min_offer = None
