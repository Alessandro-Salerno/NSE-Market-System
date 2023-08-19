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

from order_matching.side import Side
from order_matching.execution import Execution

from unet.command_handler import UNetCommandHandler, unet_command
from unet.server import UNetServerCommand
from unet.protocol import * 
from unet.database import UNetUserDatabase

from exdb import ExchangeDatabase
from setlement import Marketsetlement
from email_engine import EmailEngine

import command_backend as cb
import utils


class ExchangePriviledgedCommandHandler(UNetCommandHandler):
    @unet_command('stop')
    def stop(self, command: UNetServerCommand):
        self.top.kill()
        time.sleep(0.500)
        ExchangeDatabase().db.timer.stop()
        ExchangeDatabase().db.save()
        os.kill(os.getpid(), signal.SIGINT)
    
    @unet_command('setbal')
    def setbal(self, command: UNetServerCommand, username: str, bal: str):
        return cb.change_balance(cb.set_balance, username, bal)
    
    @unet_command('addbal')
    def addbal(self, command: UNetServerCommand, username: str, qty: str):
        return cb.change_balance(cb.increment_balance, username, qty)
    
    @unet_command('addticker')
    def addticker(self, command: UNetServerCommand, ticker: str, aclass: str):
        if not ExchangeDatabase().add_asset(ticker, aclass):
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"Ticker '{ticker}' already exists"
                }
            )
        
        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': f"Added '{ticker}={aclass}'"
            }
        )
    
    @unet_command('setticker')
    def setticker(self, command: UNetServerCommand, ticker: str, section: str, attribute: str, value: str, vtype: str):
        if ticker not in ExchangeDatabase().assets:
            return unet_make_status_message(
                mode=UNetStatusMode.ERR,
                code=UNetStatusCode.BAD,
                message={
                    'content': f"No such ticker '{ticker}'"
                }
            )
        
        with ExchangeDatabase().assets[ticker] as asset:
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
        Marketsetlement().setle()
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


class ExchangeUserCommandHandler(UNetCommandHandler):
    @unet_command('whoami', 'account', 'chisono', 'wai', 'wa', 'acc', 'cs', 'chi', 'me', 'io')
    def whoami(self, command: UNetServerCommand):
        return unet_make_value_message(
            name='User',
            value=command.issuer
        )
    
    @unet_command('balance', 'bal', 'saldo', 'sa')
    def balance(self, command: UNetServerCommand):
        setled = 0
        current = 0
        
        with ExchangeDatabase().users[command.issuer] as user:
            setled = user['immediate']['setled']['balance']
            current = user['immediate']['current']['balance']
    
        return unet_make_multi_message(
            unet_make_value_message(
                name='Unsetled Profit & Loss',
                value=current
            ),

            unet_make_value_message(
                name='Setled Balance',
                value=setled
            )
        )
    
    @unet_command('market', 'mercato', 'mark', 'mkt', 'mer', 'mm', 'mk')
    def market(self, command: UNetServerCommand):
        colums = ['TICKER', 'BID', 'ASK', 'MID', 'BID V', 'ASK V', 'CHANGE']
        tables = []

        for aclass in sorted(list(ExchangeDatabase().asset_classes.keys())):
            rows = []

            for index, ticker in enumerate(sorted(ExchangeDatabase().asset_classes[aclass])):
                rows.append([])
                with ExchangeDatabase().assets[ticker] as asset:
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
    
    @unet_command('selllimit', 'vendilimite', 'slmt', 'sl', 'vl')
    def sell_limit(self, command: UNetServerCommand, ticker: str, qty: str, price: str):
        return cb.place_order(ticker.upper(), command.issuer, Execution.LIMIT, Side.SELL, qty, price)

    @unet_command('sellmarket', 'vendimercato', 'smkt', 'sm', 'vm')
    def sell_market(self, command: UNetServerCommand, ticker: str, qty: str):
        return cb.place_order(ticker.upper(), command.issuer, Execution.MARKET, Side.SELL, qty, 0)

    @unet_command('buyliimt', 'compralimite', 'blmt', 'bl', 'cl')
    def buy_limit(self, command: UNetServerCommand, ticker: str, qty: str, price: str):
        return cb.place_order(ticker.upper(), command.issuer, Execution.LIMIT, Side.BUY, qty, price)

    @unet_command('buymarket', 'compramercato', 'bmkt', 'bm', 'bm')
    def buy_market(self, command: UNetServerCommand, ticker: str, qty: str):
        return cb.place_order(ticker.upper(), command.issuer, Execution.MARKET, Side.BUY, qty, 0)

    @unet_command('pay', 'paga', 'wire', 'pp', 'pa', 'ww')
    def pay(self, command: UNetServerCommand, who: str, amount: str):
        if who not in ExchangeDatabase().users:
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
            with ExchangeDatabase().users[who] as receiver:
                receiver['immediate']['setled']['balance'] += real_amount

            return unet_make_status_message(
                mode=UNetStatusMode.OK,
                code=UNetStatusCode.DONE,
                message={
                    'content': f"Transfered {real_amount} to '{who}'"
                }
            )

        with ExchangeDatabase().users[command.issuer] as sender:
            if sender['immediate']['setled']['balance'] + sender['immediate']['current']['balance'] < real_amount:
                return unet_make_status_message(
                    mode=UNetStatusMode.ERR,
                    code=UNetStatusCode.DENY,
                    message={
                        'content': f'Insufficient capital'
                    }
                )
            
            if sender['immediate']['setled']['balance'] < real_amount:
                sender['immediate']['current']['balance'] -= real_amount
            else:
                sender['immediate']['setled']['balance'] -= real_amount

        if not UNetUserDatabase().has_role(who, 'centralbank'):
            with ExchangeDatabase().users[who] as receiver:
                receiver['immediate']['setled']['balance'] += real_amount

        return unet_make_status_message(
            mode=UNetStatusMode.OK,
            code=UNetStatusCode.DONE,
            message={
                'content': f"Transfered {real_amount} to '{who}'"
            }
        )
    
    @unet_command('positions', 'posizioni', 'ps')
    def positions(self, command: UNetServerCommand):
        with ExchangeDatabase().users[command.issuer] as user:
            return unet_make_multi_message(
                unet_make_table_message(
                    title='UNSETLED POSITIONS',
                    columns=['SYM', 'UNITS'],
                    rows=[[a, user['immediate']['current']['assets'][a]] for a in user['immediate']['current']['assets']]
                ),

                unet_make_table_message(
                    title='SETLED POSITIONS',
                    columns=['SYM', 'UNITS'],
                    rows=[[a, user['immediate']['setled']['assets'][a]] for a in user['immediate']['setled']['assets']]
                )
            )
        
    @unet_command('marketposition', 'posizionemercato', 'mp', 'pm')
    def market_position(self, command: UNetServerCommand):
        colums = ['TICKER', 'L BID', 'L ASK', 'BUY V', 'SELL V', 'TRADED', 'SPREAD', 'SHORT', 'IMBALANCE']
        tables = []

        for aclass in sorted(list(ExchangeDatabase().asset_classes.keys())):
            rows = []

            for index, ticker in enumerate(sorted(ExchangeDatabase().asset_classes[aclass])):
                shortabs = 0
                for username in ExchangeDatabase().users:
                    user = ExchangeDatabase().users[username].get_unsafe()
                    uassets = user['immediate']['current']['assets']
                    sassets = user['immediate']['setled']['assets']
                    if ticker in uassets and uassets[ticker] < 0:
                        shortabs += abs(uassets[ticker])
                    if ticker in sassets and sassets[ticker] < 0:
                        shortabs += abs(sassets[ticker])
                
                rows.append([])
                with ExchangeDatabase().assets[ticker] as asset:
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
                    rows[index].append(round(immediate['imbalance'], 5))

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
    
    @unet_command('pendingorders', 'orders', 'ordini', 'or', 'po', 'op')
    def pendingorders(self, command: UNetServerCommand):
        colums = ['TICKER', 'ORDER', 'EXEC', 'SIZE', 'PRICE']
        rows = []

        with ExchangeDatabase().users[command.issuer] as user:
            for index, order_id in enumerate(user['immediate']['orders']):
                order = ExchangeDatabase().orders[order_id].get_unsafe()
                rows.append([])
                rows[index].append(order['ticker'])
                rows[index].append(order_id)
                rows[index].append(order['execution'])
                rows[index].append(order['size'])
                rows[index].append(utils.value_fmt(order['price']))

        return unet_make_table_message(
            title=f'PENDING ORDERS',
            columns=colums,
            rows=rows
        )
