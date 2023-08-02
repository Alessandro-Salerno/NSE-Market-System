import smtplib
import markdown
from email.mime.text import MIMEText

from texttable import Texttable

from unet.singleton import UNetSingleton
from exdb import ExchangeDatabase
from unet.database import UNetUserDatabase

import utils


class EmailEngine(UNetSingleton):
    def __setup__(self):
        self.password = ''
    
    def send(self):
        table = Texttable()
        table.set_cols_align(['l', 'r', 'r'])
        table.set_cols_valign(['m', 'm', 'm'])
        table.set_cols_dtype(['t', 'f', 't'])
        table.add_row(['SYMBOL', 'PRICE', 'CHANGE'])

        for aclass in sorted(list(ExchangeDatabase().asset_classes.keys())):
            assets = ExchangeDatabase().asset_classes[aclass]
            for assetname in sorted(assets):
                with ExchangeDatabase().assets[assetname] as asset:
                    price = utils.value_fmt(asset['immediate']['averagePrice'])
                    symbol = f'{assetname}={aclass}'
                    change = (f"{((asset['immediate']['averagePrice'] - asset['sessionData']['previousClose']) / asset['sessionData']['previousClose'] * 100):+.2f}%"
                                    if utils.are_none(asset['immediate']['averagePrice'], asset['sessionData']['previousClose'])
                                    else utils.value_fmt(None))
                    
                    table.add_row([symbol, price, change])

        addresses = [email for user, email in UNetUserDatabase().get_users()]
        addresses.remove(UNetUserDatabase().get_email_address('admin'))
        if '' in addresses:
            addresses.remove('')

        message = f"""
```
THIS MESSAGE IS SENT BY AN IN-GAME INSTITUTION ON THE "UMSR" MINECRAFT SERVER.
IF YOU'RE NOT A MEMBER OF THE "UMSR" MINECRAFT SERVER, CONSIDER WRITING TO <{UNetUserDatabase().get_email_address('admin')}> TO BE REMOVED FROM THE MAILING LIST.

ALL CONTENT IN THIS MESSAGE IS STRICTLY RELATED TO IN-GAME ASSETS WHICH ARE NOT PURCHASABLE WITH REAL WORLD MONEY.
THE UMSR NATIONAL STOCK EXCHANGE OPERATES IN ACORDANCE WITH IN-GAME FINANCIAL REGULATIONS AND DEALS IN EQUITIES, DERIVATIVES AND COMMODITIES.
FOR MORE INFORMATION ON THE UMSR NATIONAL STOCK EXCHANGE, CONSIDER WRITING TO <{UNetUserDatabase().get_email_address('admin')}> AND/OR CONTACT THE UMSR NATIONAL STOCK EXCHANGE GROUP, THE UMSR FINANCIAL CONDUCT AUTHORITY OR THE UMSR NATIONAL BANK.


MARKET SESSION FOR {utils.today()}
TIME {utils.now()}

{table.draw()}
```
"""
        
        msg = MIMEText(markdown.markdown(message, extensions=['fenced_code']), 'html')
        msg['Subject'] = f'UMSR Financial Markets Update for {utils.today()}'
        msg['From'] = UNetUserDatabase().get_email_address('admin')
        msg['To'] = ', '.join(addresses)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
            smtp_server.login(UNetUserDatabase().get_email_address('admin'), self.password)
            smtp_server.sendmail(UNetUserDatabase().get_email_address('admin'), addresses, msg.as_string())
