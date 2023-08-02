import schedule
import time

from unet.singleton import UNetSingleton

from exdb import ExchangeDatabase
from setlement import Marketsetlement
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
    
    def schedule_setlement(self):
        if ExchangeDatabase().get_open_date() != utils.today():
            Marketsetlement().setle()
        
        schedule.every().day.at('00:00', 'Europe/Rome').do(Marketsetlement().setle)

    def schedule_emails(self):
        schedule.every().day.at('12:00', 'Europe/Rome').do(EmailEngine().send)

    def start_scheduler(self):
        self.schedule_intraday()
        self.schedule_setlement()

        while True:
            schedule.run_pending()
            time.sleep(60)
