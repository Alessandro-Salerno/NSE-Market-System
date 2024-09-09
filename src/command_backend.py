# MC-UMSR-NSE Market System
# Copyright (C) 2023 - 2024 Alessandro Salerno

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

from exdb import EXCHANGE_DATABASE
from unet.protocol import *

from global_market import GlobalMarket
from historydb import HistoryDB
import utils


def increment_balance(username: str, qty: int):
    with EXCHANGE_DATABASE.users[username] as user:
        user['immediate']['settled']['balance'] += qty


def set_balance(username: str, qty: int):
    with EXCHANGE_DATABASE.users[username] as user:
        user['immediate']['settled']['balance'] = qty


def change_balance(changer, username: str, qty: str):
    if username not in EXCHANGE_DATABASE.users:
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
    
    if ticker not in EXCHANGE_DATABASE.assets:
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
        data = HistoryDB().get_asset_intraday_of(ticker, EXCHANGE_DATABASE.get_open_date())
        x, y, xfmt = _spread_series(data)

        bid = EXCHANGE_DATABASE.assets[ticker].get_unsafe()['immediate']['bid']
        ask = EXCHANGE_DATABASE.assets[ticker].get_unsafe()['immediate']['ask']
        
        x.append(utils.now())
        y.append(round((ask - bid) / round((ask + bid) / 2, 2) * 10000, 2)\
                 if bid != None and ask != None
                 else None)

        x.append(f'{utils.tomorrow()} 00:00:00')
        y.append(None)
        return x, y, xfmt
    
    if property == '__DEPTH__':
        bids = EXCHANGE_DATABASE.assets[ticker].get_unsafe()['immediate']['depth']['bids']
        offers = EXCHANGE_DATABASE.assets[ticker].get_unsafe()['immediate']['depth']['offers']
        
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


    data = HistoryDB().get_asset_intraday_of(ticker, EXCHANGE_DATABASE.get_open_date())
    return _now_series(data,
                       EXCHANGE_DATABASE.assets[ticker].get_unsafe()['immediate'][property])


def _intraday_chart(ticker: str, property: str, day: str):
    data = HistoryDB().get_asset_intraday_of(ticker, day)
    if property == '__SPREAD__':
        return _spread_series(data)
    
    return _intraday_series(data)


def _daily_chart(ticker: str, *args, **kwargs):
    data = HistoryDB().get_asset_between(ticker, '0000-00-00', EXCHANGE_DATABASE.get_open_date())

    x = []
    y = []

    for day in data:
        x.append(day[1])
        y.append(day[6])

    x.append(utils.now())
    y.append(EXCHANGE_DATABASE.assets[ticker].get_unsafe()['immediate']['mid'])

    return x, y, 'd/m/Y H:M'

def _now_series(data: list, current: float):
    x, y, fmt = _intraday_series(data)

    x.append(utils.now())
    y.append(current)

    x.append(f'{utils.tomorrow()} 00:00:00')
    y.append(None)

    return x, y, fmt


def _intraday_series(data: list):
    x = []
    y = []

    for day in data:
        x.append(f'{day[1]} {day[2]}')
        y.append(day[5])

    return x, y, 'd/m/Y H:M'


def _spread_series(data: list):
    x = []
    y = []

    for tick in data:
        bid = tick[3]
        ask = tick[4]
        mid = tick[5]
        
        x.append(f'{tick[1]} {tick[2]}')
        
        if bid == None or ask == None:
            y.append(None)
            continue

        y.append(round((ask - bid) / round((ask + bid) / 2, 2) * 10000, 2))

    return x, y, 'd/m/Y H:M'

def place_order(ticker: str, issuer: str, exec: any, side: any, size: str, price: str):
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
                'filled': 0,
                'price': 0,
                'id': None,
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
                'filled': 0,
                'price': 0,
                'id': None,
                'content': f"Invalid value '{size}' for order size"
            }
        )
    
    order_id = 0
    order = None
    order_fill = real_size
    fill_price = 0
    try:
        if exec == Execution.LIMIT:
            order = GlobalMarket().add_limit_order(ticker, side, real_price, real_size, issuer)
            order_id = order.order_id
            order_fill -= order.left

        if exec == Execution.MARKET:
            order = GlobalMarket().add_market_order(ticker, side, real_size, issuer)
            order_id = order.order_id
            order_fill -= order.left

        if order == None:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.DENY,
                message={
                    'filled': 0,
                    'price': 0,
                    'id': None,
                    'content': 'Sorry, market service on this ticker is not available'
                }
            )
        
        fill_price = round(order.fill_cost / order_fill, 2) if order_fill > 0 else 0
    except KeyError as ke:
        return unet_make_status_message(
            mode=UNetStatusMode.ERR,
            code=UNetStatusCode.BAD,
            message={
                'filled': 0,
                'price': 0,
                'id': None,
                'content': f"No such ticker '{ticker}'"
            }
        )

    return unet_make_status_message(
        mode=UNetStatusMode.OK,
        code=UNetStatusCode.DONE,
        message={
            'filled': order_fill,
            'price': fill_price,
            'id': order_id,
            'content': f"Order placed with ID={order_id}. {order_fill} Already filled at price '{fill_price}'"
        }
    )
