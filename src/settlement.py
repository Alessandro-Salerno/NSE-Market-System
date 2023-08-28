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


from unet.singleton import UNetSingleton

from exdb import ExchangeDatabase
import utils


class MarketSettlement(UNetSingleton):
    def setle(self):
        fee = 0
        
        for username in ExchangeDatabase().users:
            with ExchangeDatabase().users[username] as user:
                current_assets = user['immediate']['current']['assets']
                setled_assets = user['immediate']['settled']['assets']
                history = user['history']
                asset_history = history['assets']
                balance_history = history['balance']

                user['immediate']['settled']['balance'] = round(user['immediate']['settled']['balance'] + user['immediate']['current']['balance'], 3)
                fee += user['immediate']['current']['balance']
                user['immediate']['current']['balance'] = 0

                for assetname in current_assets:
                    if ExchangeDatabase().user_is_issuer(username, ExchangeDatabase().assets[assetname].get_unsafe()):
                        with ExchangeDatabase().assets[assetname] as asset:
                            if asset['info']['outstandingUnits'] == 1:
                                asset['info']['outstandingUnits'] = abs(current_assets[assetname])
                                continue
                            asset['info']['outstandingUnits'] += abs(current_assets[assetname])
                        continue
                    
                    if assetname not in setled_assets:
                        setled_assets.__setitem__(assetname, current_assets[assetname])
                        continue
                    
                    setled_assets[assetname] += current_assets[assetname]

                user['immediate']['current']['assets'].clear()
                asset_history.__setitem__(ExchangeDatabase().get_open_date(), dict(user['immediate']['settled']['assets']).copy())
                balance_history.__setitem__(ExchangeDatabase().get_open_date(), user['immediate']['settled']['balance'])
        
        for assetname in ExchangeDatabase().assets:
            with ExchangeDatabase().assets[assetname] as asset:
                immediate = asset['immediate']
                session_data = asset['sessionData']
                history = asset['history']
                today = history['today']
                intraday = history['intraday']
                daily = history['daily']

                session_data['close'] = immediate['mid']
                daily.__setitem__(ExchangeDatabase().get_open_date(), dict(session_data).copy())

                session_data['sellVolume'] = 0
                session_data['buyVolume'] = 0
                session_data['tradedValue'] = 0
                session_data['open'] = immediate['mid']
                session_data['previousClose'] = session_data['close']
                session_data['close'] = None

                intraday.__setitem__(ExchangeDatabase().get_open_date(), dict(today).copy())
                today.clear()

        with ExchangeDatabase().users['admin'] as admin:
            admin['immediate']['settled']['balance'] += fee

        ExchangeDatabase().set_open_date(utils.today())
