from historydb import *
import json
from datetime import datetime, date

his = HistoryDB()

file = None 
with open("db/exchange.json", 'r') as f:
    file = json.loads(f.read())

for name, user in file['usersByName'].items():
    u_his = user.pop('history')
    b_his = u_his['balance']
    a_his = u_his['assets']

    new_his = {}

    for date, balance in b_his.items():
        new_his[date] = [balance,]

    for date, assets in a_his.items():
        new_his[date].append(assets)

    for date, values in new_his.items():
        his.add_user_daily(name, date, values[0], values[1])

for ticker, asset in file['assetsByTicker'].items():
    a_his = asset.pop('history')
    t_his = a_his['today']
    i_his = a_his['intraday']
    d_his = a_his['daily']

    for time, values in t_his.items():
        his.add_asset_intraday(ticker, utils.today(), time, values['bid'], values['ask'], values['mid'])

    for date, info in i_his.items():
        for time, values in info.items():
            his.add_asset_intraday(ticker, date, time.split(' ')[1], values['bid'], values['ask'], values['mid'])

    for date, info in d_his.items():
        his.add_asset_daily(ticker, date, info['buyVolume'], info['sellVolume'], info['tradedValue'], info['open'], info['close'])

with open('db/exchange.json', 'w') as f:
    f.write(json.dumps(file))


    

