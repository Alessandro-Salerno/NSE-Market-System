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


import time
import os
import signal
from collections import defaultdict

from order_matching.side import Side
from order_matching.execution import Execution

from unet.command_handler import UNetCommandHandler, unet_command
from unet.server import UNetServerCommand
from unet.protocol import * 
from unet.database import UNetUserDatabase
from unet.command_parser import UNetCommandParserFactory

from platformdb import PlatformDB
from object_lock import ObjectLock

from exdb import EXCHANGE_DATABASE
from global_market import GlobalMarket
from settlement import MarketSettlement
from email_engine import EmailEngine

import command_backend as cb
import utils


class ExchangePriviledgedCommandHandler(UNetCommandHandler):
    @unet_command('stop')
    def stop(self, command: UNetServerCommand):
        self.top.kill()
        GlobalMarket().close_markets()
        time.sleep(0.500)
        EXCHANGE_DATABASE.db.timer.stop()
        EXCHANGE_DATABASE.db.save()
        os.kill(os.getpid(), signal.SIGINT)
    
    @unet_command('setbal')
    def setbal(self, command: UNetServerCommand, username: str, bal: str):
        return cb.change_balance(cb.set_balance, username, bal)
    
    @unet_command('addbal')
    def addbal(self, command: UNetServerCommand, username: str, qty: str):
        return cb.change_balance(cb.increment_balance, username, qty)
    
    @unet_command('addticker')
    def addticker(self, command: UNetServerCommand, ticker: str, aclass: str):
        if not EXCHANGE_DATABASE.add_asset(ticker, aclass):
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"Ticker '{ticker}' already exists"
                }
            )
        
        GlobalMarket().create_market(ticker)

        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': f"Added '{ticker}={aclass}'"
            }
        )
    
    @unet_command('setticker')
    def setticker(self, command: UNetServerCommand, ticker: str, section: str, attribute: str, value: str, vtype: str):
        if ticker not in EXCHANGE_DATABASE.assets:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"No such ticker '{ticker}'"
                }
            )
        
        with EXCHANGE_DATABASE.assets[ticker] as asset:
            if section not in asset.keys():
                return unet_make_status_message(
                    mode=UNetStatusMode.ERR,
                    code=UNetStatusCode.BAD,
                    message={
                        'content': f"Unknown section '{section}' for asset '{ticker}={asset['class']}'"
                    }
                )
            
            if attribute not in asset[section].keys():
                return unet_make_status_message(
                    mode=UNetStatusMode.ERR,
                    code=UNetStatusCode.BAD,
                    message={
                        'content': f"Unknown attribute '{attribute}' for asset '{ticker}={asset['class']}/{section}'"
                    }
                )
            
            asset[section][attribute] = eval(vtype)(value)

        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': f"{ticker}/{section}/{attribute} set to '{value}' of type '{vtype}'"
            }
        )
    
    @unet_command('newsession')
    def newsession(self, command: UNetServerCommand):
        MarketSettlement().settle()
        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': 'Session reset'
            }
        )
    
    @unet_command('addrole')
    def addrole(self, command: UNetServerCommand, who: str, role: str):
        UNetUserDatabase().add_role(name=who, role=role)
        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': f"Added role '{role}' to user '{who}'"
            }
        )

    @unet_command('rmrole')
    def rmrole(self, command: UNetServerCommand, who: str, role: str):
        UNetUserDatabase().remove_role(name=who, role=role)
        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': f"Removed role '{role}' from user '{who}'"
            }
        )
    
    @unet_command('newsupdate')
    def newsupdate(self, command: UNetServerCommand):
        EmailEngine().send()
        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': 'News sent'
            }
        )
    
    @unet_command('rmticker')
    def rmticker(self, command: UNetServerCommand, ticker: str):
        if ticker not in EXCHANGE_DATABASE.assets:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"No such ticker '{ticker}'"
                }
            )
        
        GlobalMarket().remove_market(ticker)
        
        units = defaultdict(lambda: 0)
        for username in EXCHANGE_DATABASE.users:
            with EXCHANGE_DATABASE.users[username] as user:
                if ticker in user['immediate']['current']['assets']:
                    units[username] += user['immediate']['current']['assets'].pop(ticker)
                if ticker in user['immediate']['settled']['assets']:
                    if not EXCHANGE_DATABASE.user_is_issuer(username, EXCHANGE_DATABASE.assets[ticker].get_unsafe()):
                        units[username] += user['immediate']['settled']['assets'].pop(ticker)
                    else:
                        user['immediate']['settled']['assets'].pop(ticker)

        return unet_make_multi_message(
            unet_make_status_message(
                mode=UNetStatusMode.OK,
                code=UNetStatusCode.DONE,
                message={
                    'content': 'Ticker deleted'
                }
            ),

            *[unet_make_value_message(name=name, value=num) for name, num in units.items()]
        )


class ExchangeUserCommandHandler(UNetCommandHandler):
    @unet_command('whoami', 'chisono')
    def whoami(self, command: UNetServerCommand):
        return unet_make_value_message(
            name='User',
            value=command.issuer
        )
    
    @unet_command('balance', 'bal', 'saldo', 'sa')
    def balance(self, command: UNetServerCommand):
        settled = 0
        current = 0
        
        with EXCHANGE_DATABASE.users[command.issuer] as user:
            settled = user['immediate']['settled']['balance']
            current = user['immediate']['current']['balance']
    
        return unet_make_multi_message(
            unet_make_value_message(
                name='Unsettled Profit & Loss',
                value=current
            ),

            unet_make_value_message(
                name='settled Balance',
                value=settled
            )
        )
    
    @unet_command('market', 'mercato', 'mm')
    def market(self, command: UNetServerCommand):
        colums = ['TICKER', 'BID', 'ASK', 'MID', 'BID V', 'ASK V', 'CHANGE']
        tables = []

        for aclass in sorted(list(EXCHANGE_DATABASE.asset_classes.keys())):
            rows = []

            for index, ticker in enumerate(sorted(EXCHANGE_DATABASE.asset_classes[aclass])):
                rows.append([])
                with EXCHANGE_DATABASE.assets[ticker] as asset:
                    info = asset['info']
                    immediate = asset['immediate']
                    session_data = asset['sessionData']

                    rows[index].append(ticker)
                    rows[index].append(utils.value_fmt(immediate['bid']))
                    rows[index].append(utils.value_fmt(immediate['ask']))
                    rows[index].append(utils.value_fmt(immediate['mid']))
                    rows[index].append(utils.value_fmt(immediate['bidVolume']))
                    rows[index].append(utils.value_fmt(immediate['askVolume']))
                    rows[index].append(f"{(((immediate['mid'] - session_data['previousClose']) / session_data['previousClose']) * 100):+.2f}%"
                                    if utils.are_none(immediate['mid'], session_data['previousClose'])
                                        else utils.value_fmt(None))
                    
            tables.append(unet_make_table_message(
                title=f'CLASS {aclass} MARKET',
                columns=colums,
                rows=rows
            ))


        return unet_make_multi_message(
            *tables
        )
    
    @unet_command('today', 'oggi', 'tt', 'oo')
    def today(self, command: UNetServerCommand, ticker: str):
        return cb.show_chart(ticker, 'today', property='mid')
    
    @unet_command('todayspread', 'spreadoggi', 'tsp', 'spo')
    def today_spread(self, command: UNetServerCommand, ticker: str):
        return cb.show_chart(ticker, 'today', property='__SPREAD__')

    @unet_command('intraday', 'intragiornaliero', 'ii', 'ig')
    def intraday(self, command: UNetServerCommand, ticker: str, day: str, month: str, year: str):
        return cb.show_chart(ticker, 'intraday', property='mid', day=f'{year}-{day}-{month}')

    @unet_command('intradayspread', 'spreadintragiornaliero', 'isp', 'spig')
    def intraday_spread(self, command: UNetServerCommand, ticker: str, day: str, month: str, year: str):
        return cb.show_chart(ticker, 'intraday', property='__SPREAD__', day=f'{year}-{day}-{month}')

    @unet_command('daily', 'dd', 'giornaliero', 'gr')
    def daily(self, command: UNetServerCommand, ticker :str):
        return cb.show_chart(ticker.upper(), 'daily', property='close', current_property='mid')
    
    @unet_command('depth', 'de', 'dp')
    def depth(self, command: UNetServerCommand, ticker: str):
        return cb.show_chart(ticker.upper(), 'today', property='__DEPTH__')

    @unet_command('selllimit', 'vendilimite', 'sl', 'vl')
    def sell_limit(self, command: UNetServerCommand, ticker: str, qty: str, price: str):
        return cb.place_order(ticker.upper(), command.issuer, Execution.LIMIT, Side.SELL, qty, price)

    @unet_command('sellmarket', 'vendimercato', 'sm', 'vm')
    def sell_market(self, command: UNetServerCommand, ticker: str, qty: str):
        return cb.place_order(ticker.upper(), command.issuer, Execution.MARKET, Side.SELL, qty, 0)

    @unet_command('buyliimt', 'compralimite', 'bl', 'cl')
    def buy_limit(self, command: UNetServerCommand, ticker: str, qty: str, price: str):
        return cb.place_order(ticker.upper(), command.issuer, Execution.LIMIT, Side.BUY, qty, price)

    @unet_command('buymarket', 'compramercato', 'bm', 'cm')
    def buy_market(self, command: UNetServerCommand, ticker: str, qty: str):
        return cb.place_order(ticker.upper(), command.issuer, Execution.MARKET, Side.BUY, qty, 0)

    @unet_command('pay', 'paga', 'pp', 'pa')
    def pay(self, command: UNetServerCommand, who: str, amount: str):
        if who not in EXCHANGE_DATABASE.users:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"No such user '{who}'"
                }
            )
        
        real_amount = 0
        try:
            real_amount = round(float(amount), 3)
            if real_amount < 0:
                raise Exception()
        except:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"Invalid value '{amount}' for transaction size"
                }
            )
        
        if UNetUserDatabase().has_role(command.issuer, 'centralbank'):
            with EXCHANGE_DATABASE.users[who] as receiver:
                receiver['immediate']['settled']['balance'] += real_amount

            return unet_make_status_message(
                mode=UNetStatusMode.OK,
                code=UNetStatusCode.DONE,
                message={
                    'content': f"Transfered {real_amount} to '{who}'"
                }
            )

        with EXCHANGE_DATABASE.users[command.issuer] as sender:
            if sender['immediate']['settled']['balance'] + sender['immediate']['current']['balance'] < real_amount:
                return unet_make_status_message(
                    mode=UNetStatusMode.ERR,
                    code=UNetStatusCode.DENY,
                    message={
                        'content': f'Insufficient capital'
                    }
                )
            
            if sender['immediate']['settled']['balance'] < real_amount:
                sender['immediate']['current']['balance'] -= real_amount
            else:
                sender['immediate']['settled']['balance'] -= real_amount

        if not UNetUserDatabase().has_role(who, 'centralbank'):
            with EXCHANGE_DATABASE.users[who] as receiver:
                receiver['immediate']['settled']['balance'] += real_amount

        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': f"Transfered {real_amount} to '{who}'"
            }
        )
    
    @unet_command('positions', 'posizioni', 'ps')
    def positions(self, command: UNetServerCommand):
        with EXCHANGE_DATABASE.users[command.issuer] as user:
            return unet_make_multi_message(
                unet_make_table_message(
                    title='SESSION MOVES',
                    columns=['TICKER', 'CHANGE'],
                    rows=[[a, b] for a, b in sorted(user['immediate']['current']['assets'].items(), key=lambda item: item[1])]
                ),

                unet_make_table_message(
                    title='SETTLED POSITIONS',
                    columns=['TICKER', 'UNITS'],
                    rows=[[a, b] for a, b in sorted(user['immediate']['settled']['assets'].items(), key=lambda item: item[1])]
                )
            )
        
    @unet_command('marketposition', 'posizionemercato', 'mp', 'pm')
    def market_position(self, command: UNetServerCommand):
        colums = ['TICKER', 'L BID', 'L ASK', 'BUY V', 'SELL V', 'TRADED', 'SPREAD', 'SHORT']
        tables = []

        for aclass in sorted(list(EXCHANGE_DATABASE.asset_classes.keys())):
            rows = []

            for index, ticker in enumerate(sorted(EXCHANGE_DATABASE.asset_classes[aclass])):
                shortabs = 0
                for username in EXCHANGE_DATABASE.users:
                    user = EXCHANGE_DATABASE.users[username].get_unsafe()
                    uassets = user['immediate']['current']['assets']
                    sassets = user['immediate']['settled']['assets']
                    if EXCHANGE_DATABASE.user_is_issuer(username, EXCHANGE_DATABASE.assets[ticker].get_unsafe()):
                        continue
                    stl = 0
                    if ticker in sassets:
                        stl += sassets[ticker]
                    if ticker in uassets and uassets[ticker] < 0:
                        stl += uassets[ticker]
                    if stl < 0:
                        shortabs += abs(stl)
                
                rows.append([])
                with EXCHANGE_DATABASE.assets[ticker] as asset:
                    info = asset['info']
                    immediate = asset['immediate']
                    session_data = asset['sessionData']

                    rows[index].append(ticker)
                    rows[index].append(utils.value_fmt(immediate['lastBid']))
                    rows[index].append(utils.value_fmt(immediate['lastAsk']))
                    rows[index].append(utils.value_fmt(session_data['buyVolume']))
                    rows[index].append(utils.value_fmt(session_data['sellVolume']))
                    rows[index].append(utils.value_fmt(session_data['tradedValue']))
                    rows[index].append(utils.value_fmt(round((immediate['ask'] - immediate['bid']) / round(immediate['mid'], 3) * 10000, 2)\
                                                        if immediate['bid'] != None and immediate['ask'] != None
                                                        else None))

                    rows[index].append(f"{(shortabs / info['outstandingUnits'] * 100):.2f}%")

            tables.append(unet_make_table_message(
                title=f'CLASS {aclass} MARKET',
                columns=colums,
                rows=rows
            ))

        return unet_make_multi_message(
            *tables
        )
        
    @unet_command('changepassword', 'passwd')
    def change_password(self, command: UNetServerCommand, old_password: str, new_password: str):
        if UNetUserDatabase().get_user_password(command.issuer) != old_password:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.DENY,
                message={
                    'content': 'Wrong password'
                }
            )
        
        UNetUserDatabase().set_user_password(command.issuer, new_password)

        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': 'Password updated'
            }
        )
    
    @unet_command('emaddr')
    def emaddr(self, command: UNetServerCommand, new_address: str):
        UNetUserDatabase().set_email_address(command.issuer, new_address)

        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': 'E-Mail Address updated'
            }
        )
    
    @unet_command('orders', 'ordini', 'op', 'po')
    def pendingorders(self, command: UNetServerCommand):
        colums = ['TICKER', 'ORDER', 'EXEC', 'SIDE', 'SIZE', 'PRICE']
        rows = []

        with EXCHANGE_DATABASE.users[command.issuer] as user:
            for index, order_id in enumerate(user['immediate']['orders']):
                order = EXCHANGE_DATABASE.orders[order_id]
                rows.append([])
                rows[index].append(order['ticker'])
                rows[index].append(order_id)
                rows[index].append(order['execution'])
                rows[index].append(order['side'])
                rows[index].append(order['size'])
                rows[index].append(utils.value_fmt(order['price']))

        return unet_make_table_message(
            title=f'PENDING ORDERS',
            columns=colums,
            rows=rows
        )
    
    @unet_command('clearorders', 'annullaordini', 'co', 'ao')
    def clearorders(self, command: UNetServerCommand, ticker: str):
        ticker = ticker.upper()
        if ticker not in EXCHANGE_DATABASE.assets:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"No such ticker '{ticker}'"
                }
            )
        
        order_ids = []
        for order_id in EXCHANGE_DATABASE.users[command.issuer].get_unsafe()['immediate']['orders']:
            if EXCHANGE_DATABASE.orders[order_id]['ticker'] == ticker:
                order_ids.append(order_id)

        tot = 0
        for order_id in order_ids:
            tot += GlobalMarket().cancel_order(order_id, command.issuer) == None

        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'total': len(order_ids),
                'successful': tot,
                'failed': len(order_ids) - tot,
                'content': f'{len(order_ids)} orders processed, {tot} successful, {len(order_ids) - tot} failed'
            }
        )

    @unet_command('deleteorder', 'cancellaordine', 'do')
    def deleteorder(self, command: UNetServerCommand, order_id: int):
        r = GlobalMarket().cancel_order(order_id, command.issuer)

        message = {
            -1: f"No such Order ID '{order_id}'",
            -2: 'Permission denied',
            None: 'Order deleted'
        }[r]

        return unet_make_status_message(
            mode=UNetStatusMode.OK if r == None else UNetStatusMode.ERR,
            code=UNetStatusCode.DONE if r == None else UNetStatusCode.DENY,
            message={
                'errno': r,
                'content': message
            }
        )
    
    @unet_command('transfer', 'trasferisci', 'tr', 'mv')
    def transfer(self, command: UNetServerCommand, ticker: str, qty: str, who: str):
        ticker = ticker.upper()
        if ticker not in EXCHANGE_DATABASE.assets:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"No such ticker '{ticker}'"
                }
            )
        
        try:
            qty = int(qty)
            if qty <= 0:
                raise Exception()
        except:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"Invalid value '{qty}' for quantity"
                }
            )
        
        if who not in EXCHANGE_DATABASE.users:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"No such user '{who}'"
                }
            )
    
        with EXCHANGE_DATABASE.users[command.issuer] as sender:
            if not EXCHANGE_DATABASE.user_is_issuer(command.issuer, EXCHANGE_DATABASE.assets[ticker].get_unsafe()):
                if ticker not in sender['immediate']['settled']['assets'] or sender['immediate']['settled']['assets'][ticker] < qty:
                    return unet_make_status_message(
                        mode=UNetStatusMode.ERR,
                        code=UNetStatusCode.DENY,
                        message={
                            'content': f"The specified amount of {qty} units is higher than your settled portfolio allows"
                        }
                    )
            
            sender['immediate']['settled']['assets'][ticker] -= qty
            if sender['immediate']['settled']['assets'][ticker] == 0:
                sender['immediate']['settled']['assets'].pop(ticker)

        with EXCHANGE_DATABASE.users[who] as receiver:
            receiver['immediate']['settled']['assets'][ticker] += qty
            if receiver['immediate']['settled']['assets'][ticker] == 0:
                receiver['immediate']['settled']['assets'].pop(ticker)
        
        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': f"Transfered {qty} units of '{ticker}' to '{who}'"
            }
        )
    
    @unet_command('json')
    def json(self, command: UNetServerCommand, path: str):
        path_steps = path.split('/')
        target_key = path_steps.pop(len(path_steps) - 1) if len(path_steps) > 0 and path != '' else 'db'
        if '' in path_steps:
            path_steps.remove('')
        base = {'db': EXCHANGE_DATABASE.db.db}
        locks = []

        try:
            for index, step in enumerate(path_steps):
                if isinstance(base, dict):
                    base = base[step]
                    continue

                if isinstance(base, ObjectLock):
                    if base.lock not in locks:
                        base.lock.acquire()
                        locks.append(base.lock)
                    base = base.get_unsafe()[step]

            if isinstance(base, ObjectLock):
                if base.lock not in locks:
                    base.lock.acquire()
                    locks.append(base.lock)
                base = base.get_unsafe()

            root = base[target_key]
            
            if isinstance(root, ObjectLock):
                if root.lock not in locks:
                    root.lock.acquire()
                    locks.append(root.lock)
                root = root.get_unsafe()

            target = PlatformDB.to_dict(root) if isinstance(root, dict) else root
            for lock in locks:
                lock.release()

            return unet_make_value_message(
                name=target_key,
                value=target
            )
        except KeyError as ke:
            (lock.release() for lock in locks)
            
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'key': None,
                    'content': f"Uknown key"
                }
            )

    @unet_command('lazy')
    def lazy(self, command: UNetServerCommand, real_command: str):
        cmd = UNetCommandParserFactory('*').parse(real_command)
        cmd.issuer = command.issuer
        self.call_command(cmd)
