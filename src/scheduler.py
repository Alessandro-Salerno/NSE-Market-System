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


import schedule
import time

from unet.singleton import UNetSingleton

from exdb import ExchangeDatabase
from settlement import MarketSettlement
from email_engine import EmailEngine
import utils


class MarketScheduler(UNetSingleton):
    def add_intraday(self):
        for assetname in ExchangeDatabase().assets:
            with ExchangeDatabase().assets[assetname] as asset:
                today = asset['history']['today']
                today.__setitem__(utils.now(), asset['immediate'].copy())

    def schedule_intraday(self):
        # Warning: bad code, gotta refactor
        schedule.every().hour.at(':00').do(self.add_intraday)
        schedule.every().hour.at(':13').do(self.add_intraday)
        schedule.every().hour.at(':20').do(self.add_intraday)
        schedule.every().hour.at(':30').do(self.add_intraday)
        schedule.every().hour.at(':40').do(self.add_intraday)
        schedule.every().hour.at(':50').do(self.add_intraday)
    
    def schedule_settlement(self):
        if ExchangeDatabase().get_open_date() != utils.today():
            MarketSettlement().setle()
        
        schedule.every().day.at('00:00', 'Europe/Rome').do(MarketSettlement().setle)

    def schedule_emails(self):
        schedule.every().day.at('12:00', 'Europe/Rome').do(EmailEngine().send)

    def start_scheduler(self):
        self.schedule_intraday()
        self.schedule_settlement()

        while True:
            schedule.run_pending()
            time.sleep(60)
