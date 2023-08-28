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


from order_matching.execution import Execution

from exdb import ExchangeDatabase
from unet.protocol import *

from global_market import GlobalMarket
import utils


def increment_balance(username: str, qty: int):
    with ExchangeDatabase().users[username] as user:
        user['immediate']['settled']['balance'] += qty


def set_balance(username: str, qty: int):
    with ExchangeDatabase().users[username] as user:
        user['immediate']['settled']['balance'] = qty


def change_balance(changer, username: str, qty: str):
    if username not in ExchangeDatabase().users:
        return unet_make_status_message(
            mode=UNetStatusMode.ERR,
            code=UNetStatusCode.BAD,
            message={
                'content': f"No such user '{username}'"
            }
        )
    
    real_qty = 0
    try:
        real_qty = int(qty)
    except:
        return unet_make_status_message(
            mode=UNetStatusMode.ERR,
            code=UNetStatusCode.BAD,
            message={
                'content': f"Invalid value '{qty}'"
            }
        )

    changer(username, real_qty)

    return unet_make_status_message(
        mode=UNetStatusMode.OK,
        code=UNetStatusCode.DONE,
        message={
            'content': f"settled Balance of user '{username} set to {real_qty}"
        }
    )

def show_chart(ticker: str, timeframe: str, **kwargs):
    ticker = ticker.upper()
    
    if ticker not in ExchangeDatabase().assets:
        return unet_make_status_message(
            mode=UNetStatusMode.ERR,
            code=UNetStatusCode.BAD,
            message={
                'content': f"No such ticker '{ticker}'"
            }
        )
    
    backends = {
        'today': _today_chart,
        'intraday': _intraday_chart,
        'daily': _daily_chart
    }

    x, y, fmt = backends[timeframe](ticker, **kwargs)

    if len(x) != len(y) or len(x) < 2:
        return unet_make_status_message(
            mode=UNetStatusMode.ERR,
            code=UNetStatusCode.DENY,
            message={
                'content': 'Insufficient data'
            }
        )

    return unet_make_chart_message(
        unet_make_chart_series(
            name=ticker,
            x=x,
            y=y
        ),

        title=ticker,
        xformat=fmt,
        xlabel='Time',
        ylabel='Value'
    )


def _today_chart(ticker: str, property: str):
    if property == '__SPREAD__':
        x, y, xfmt = _spread_series(ExchangeDatabase().assets[ticker].get_unsafe()['history']['today'])

        bid = ExchangeDatabase().assets[ticker].get_unsafe()['immediate']['bid']
        ask = ExchangeDatabase().assets[ticker].get_unsafe()['immediate']['ask']
        
        x.append(utils.now())
        y.append(round((ask - bid) / round((ask + bid) / 2, 3) * 10000, 2)\
                 if bid != None and ask != None
                 else None)

        x.append(f'{utils.tomorrow()} 00:00:00')
        y.append(None)
        return x, y, xfmt
    
    if property == '__DEPTH__':
        bids = ExchangeDatabase().assets[ticker].get_unsafe()['immediate']['depth']['bids']
        offers = ExchangeDatabase().assets[ticker].get_unsafe()['immediate']['depth']['offers']
        
        bidkeys = sorted([float(k) for k in bids])
        offerkeys = sorted([float(k) for k in offers])

        fbids = {float(k): bids[str(k)] for k in bidkeys}
        foffers = {float(k): offers[str(k)] for k in offerkeys}
        
        both = {}
        both.update(fbids)
        both.update(foffers)

        x = []
        y = []

        bid_qty = sum([fbids[i] for i in fbids])
        offer_qty = 0
        
        for bid in bidkeys:
            x.append(bid)
            y.append(bid_qty)
            bid_qty -= both[bid]

        for offer in offerkeys:
            offer_qty += both[offer]
            x.append(offer)
            y.append(offer_qty)
        return x, y, None

    return _now_series(ExchangeDatabase().assets[ticker].get_unsafe()['history']['today'],
                       property,
                       ExchangeDatabase().assets[ticker].get_unsafe()['immediate'][property])


def _intraday_chart(ticker: str, property: str, day: str):
    if day not in ExchangeDatabase().assets[ticker].get_unsafe()['history']['intraday']:
        return [], [], None
    
    if property == '__SPREAD__':
        return _spread_series(ExchangeDatabase().assets[ticker].get_unsafe()['history']['intraday']['day'])
    
    return _intraday_series(ExchangeDatabase().assets[ticker].get_unsafe()['history']['intraday']['day'])


def _daily_chart(ticker: str, property: str, current_property: str):
    return _now_series(ExchangeDatabase().assets[ticker].get_unsafe()['history']['daily'],
                       property,
                       ExchangeDatabase().assets[ticker].get_unsafe()['immediate'][current_property])


def _now_series(history: dict, propertY: str, current: float):
    x = [date for date in history.keys()]
    y = [history[key][propertY]
            for key in history]

    x.append(utils.now())
    y.append(current)

    x.append(f'{utils.tomorrow()} 00:00:00')
    y.append(None)

    return x, y, 'd/m/Y H:M'


def _intraday_series(ticks: dict, propertY: str):
    pass

def _spread_series(history: dict):
    return list(history.keys()), \
            [(round((history[e]['ask'] - history[e]['bid']) / round((history[e]['ask'] + history[e]['bid']) / 2, 3) * 10000, 2)
             if history[e]['bid'] != None and history[e]['ask'] != None
             else None)
              for e in history], \
            'd/m/Y H:M'


def place_order(ticker: str, issuer: str, exec: any, side: any, size: str, price: str):
    if ticker not in ExchangeDatabase().assets.keys():
        return unet_make_status_message(
            mode=UNetStatusMode.ERR,
            code=UNetStatusCode.BAD,
            message={
                'content': f"No such ticker '{ticker}'"
            }
        )
    
    real_price = 0
    try:
        real_price = float(price)
        if real_price == float('inf') or real_price == float('nan'):
            raise Exception()
        if exec != Execution.MARKET and real_price <= 0:
            raise Exception()
    except:
        return unet_make_status_message(
            mode=UNetStatusMode.ERR,
            code=UNetStatusCode.BAD,
            message={
                'content': f"Invalid value '{price}' for order price"
            }
        )
    
    real_size = 0
    try:
        real_size = int(size)
        if real_price == float('inf') or real_price == float('nan') or real_size <= 0:
            raise Exception()
    except:
        return unet_make_status_message(
            mode=UNetStatusMode.ERR,
            code=UNetStatusCode.BAD,
            message={
                'content': f"Invalid value '{size}' for order size"
            }
        )
    
    order_id = 0
    order_fill = real_size
    if exec == Execution.LIMIT:
        order = GlobalMarket().add_limit_order(ticker, side, real_price, real_size, issuer)
        order_id = order.order_id
        order_fill -= order.size

    if exec == Execution.MARKET:
        order = GlobalMarket().add_market_order(ticker, side, real_size, issuer)
        order_id = order.order_id
        order_fill -= order.size

    return unet_make_status_message(
        mode=UNetStatusMode.OK,
        code=UNetStatusCode.DONE,
        message={
            'filled': order_fill,
            'price': order.price,
            'id': order_id,
            'content': f"Order placed with ID={order_id}. {order_fill} Already filled at price '{order.price}'"
        }
    )
