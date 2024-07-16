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


from unet.singleton import UNetSingleton
from order_matching.execution import Execution
from order_matching.side import Side

import command_backend as cb
from exdb import EXCHANGE_DATABASE
from historydb import HistoryDB
from creditdb import CreditDB, CreditState
import utils


class MarketSettlement(UNetSingleton):
    def settle(self):
        for username in EXCHANGE_DATABASE.users:
            with EXCHANGE_DATABASE.users[username] as user:
                current_assets = user['immediate']['current']['assets']
                settled_assets = user['immediate']['settled']['assets']

                for assetname in current_assets:
                    settled_assets[assetname] += current_assets[assetname]
                    
                for assetname, qty in settled_assets.copy().items():
                    if qty == 0:
                        settled_assets.pop(assetname)
                    # Remove this to disable "margin call"
                    elif qty < 0 \
                        and not EXCHANGE_DATABASE.user_is_issuer(username, EXCHANGE_DATABASE.assets[assetname].get_unsafe()):
                        cb.place_order(assetname, 
                                       EXCHANGE_DATABASE.assets[assetname].get_unsafe()['info']['issuer'],
                                       Execution.MARKET,
                                       Side.BUY,
                                       abs(qty),
                                       0)

                user['immediate']['settled']['balance'] = round(user['immediate']['settled']['balance'] + user['immediate']['current']['balance'], 3)
                user['immediate']['current']['balance'] = 0
                user['immediate']['current']['assets'].clear()

                HistoryDB().add_user_daily(username, EXCHANGE_DATABASE.get_open_date(), user['immediate']['settled']['balance'], user['immediate']['settled']['assets'])
        
        for assetname in EXCHANGE_DATABASE.assets:
            with EXCHANGE_DATABASE.assets[assetname] as asset:
                immediate = asset['immediate']
                session_data = asset['sessionData']
        
                session_data['close'] = immediate['mid']

                HistoryDB().add_asset_daily(assetname, EXCHANGE_DATABASE.get_open_date(), session_data['buyVolume'], session_data['sellVolume'], session_data['tradedValue'], session_data['open'], session_data['close'])

                session_data['sellVolume'] = 0
                session_data['buyVolume'] = 0
                session_data['tradedValue'] = 0
                session_data['open'] = immediate['mid']
                session_data['previousClose'] = session_data['close']
                session_data['close'] = None

        EXCHANGE_DATABASE.set_open_date(utils.today())

        CreditDB().update_matured_days()

        intrest_due = CreditDB().get_all_intrest_due()

        for credit in intrest_due:
            creditor = credit[1]
            debtor = credit[2]
            amount = credit[3]
            frequency = credit[8]
            spread = credit[9]
            base = credit[len(credit) - 1]
            rate_due = (float(base + spread) / 7 * frequency) / 10000
            amount_due = round(amount * rate_due, 3)
            success = True

            if amount_due >= 0:
                with EXCHANGE_DATABASE.users[debtor] as debtor_user:
                    if debtor_user['immediate']['settled']['balance'] >= amount_due:
                        debtor_user['immediate']['settled']['balance'] = round(debtor_user['immediate']['settled']['balance'] - amount_due, 3)
                        CreditDB().add_history_instance(credit[0], amount_due, CreditState.PAID_CASH)
                    elif CreditDB().collateral_call(credit[0], amount_due):
                        CreditDB().add_history_instance(credit[0], amount_due, CreditState.PAID_COLLATERAL)
                    else:
                        CreditDB().add_history_instance(credit[0], amount_due, CreditState.DEFAULT)
                        CreditDB().rollback_advancement(credit[0])
                        success = False

                if success:
                    with EXCHANGE_DATABASE.users[creditor] as creditor_user:
                        creditor_user['immediate']['settled']['balance'] = round(creditor_user['immediate']['settled']['balance'] + amount_due, 3)
            else:
                with EXCHANGE_DATABASE.users[creditor] as creditor_user:
                    if creditor_user['immediate']['settled']['balance'] >= amount_due:
                        creditor_user['immediate']['settled']['balance'] = round(creditor_user['immediate']['settled']['balance'] + amount_due, 3)
                        CreditDB().add_history_instance(credit[0], amount_due, CreditState.PAID_CASH)
                    else:
                        CreditDB().add_history_instance(credit[0], amount_due, CreditState.DEFAULT)
                        CreditDB().rollback_advancement(credit[0])
                        success = False
                
                if success:
                    with EXCHANGE_DATABASE.users[debtor] as debtor_user:
                        debtor_user['immediate']['settled']['balance'] = round(debtor_user['immediate']['settled']['balance'] - amount_due, 3)

        maturities = CreditDB().get_all_mature()

        for credit in maturities:
            creditor = credit[1]
            debtor = credit[2]
            amount_due = credit[4]
            success = True
            refund = credit[10]

            with EXCHANGE_DATABASE.users[debtor] as debtor_user:
                if debtor_user['immediate']['settled']['balance'] + refund >= amount_due:
                    debtor_user['immediate']['settled']['balance'] = round(debtor_user['immediate']['settled']['balance'] - amount_due, 3)
                    CreditDB().add_history_instance(credit[0], amount_due, CreditState.PAID_CASH)
                else:
                    CreditDB().add_history_instance(credit[0], amount_due, CreditState.DEFAULT)
                    CreditDB().rollback_advancement(credit[0])
                    success = False
                    refund = 0

                if success:
                    debtor_user['immediate']['settled']['balance'] = round(debtor_user['immediate']['settled']['balance'] + refund, 3)
            
            if success:
                with EXCHANGE_DATABASE.users[creditor] as creditor_user:
                    creditor_user['immediate']['settled']['balance'] = round(creditor_user['immediate']['settled']['balance'] + amount_due, 3)
