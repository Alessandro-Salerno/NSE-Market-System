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


from unet.database import UNetDatabase
from unet.singleton import UNetSingleton
import utils
import json


class HistoryDB(UNetSingleton):
    def __setup__(self):
        self._db = UNetDatabase('db/history.db')

        self._db.run(
"""
CREATE TABLE IF NOT EXISTS AssetDaily (
    ticker VARCHAR(32) NOT NULL,
    day TEXT NOT NULL,
    buy_volume INT NOT NULL DEFAULT 0,
    sell_volume INT NOT NULL DEFAULT 0,
    traded_value REAL NOT NULL DEFAULT 0,
    open REAL,
    close REAL
)
""")

        self._db.run(
"""
CREATE TABLE IF NOT EXISTS AssetIntraday (
    ticker VARCHAR(32) NOT NULL,
    day TEXT NOT NULL,
    time TEXT NOT NULL,
    bid REAL,
    ask REAL,
    mid REAL
)
""")

        self._db.run(
"""
CREATE TABLE IF NOT EXISTS UserDaily (
    username TEXT NOT NULL,
    day TEXT NOT NULL,
    balance REAL NOT NULL,
    assets TEXT NOT NULL
)
""")

        self._db.run(
"""
CREATE TABLE IF NOT EXISTS Payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL,
    amount REAL NOT NULL,
    currency VARCHAR(32) NOT NULL,
    day TEXT NOT NULL,
    time TEXT NOT NULL,
    category TEXT
)
""")

    def add_asset_intraday(self, ticker, date, time, bid, ask, mid):
        self._db.run(
"""
INSERT INTO AssetIntraday VALUES
(?, ?, ?, ?, ?, ?)
""", ticker, date, time, bid, ask, mid)

    def add_asset_daily(self, ticker, date, buy_vol, sell_vol, traded, open_, close):
        self._db.run(
"""
INSERT INTO AssetDaily VALUES
(?, ?, ?, ?, ?, ?, ?)
""", ticker, date, buy_vol, sell_vol, traded, open_, close)

    def add_user_daily(self, username, date, balance, assets):
        self._db.run(
"""
INSERT INTO UserDaily VALUES
(?, ?, ?, ?)
""", username, date, balance, json.dumps(assets))

    def get_asset_intraday_of(self, ticker, date):
        return self._db.query(
"""
SELECT *
FROM AssetIntraday
WHERE ticker = ? AND day = ?
ORDER BY time ASC
""", ticker, date)

    def get_asset_between(self, ticker, start_date, end_date):
        return self._db.query(
"""
SELECT *
FROM AssetDaily
WHERE ticker = ? AND date(day) BETWEEN ? AND ?
ORDER BY day ASC
""", ticker, start_date, end_date)

    def get_asset_intraday_between(self, ticker, start_date, end_date):
        return self._db.query(
"""
SELECT *
FROM AssetIntraday
WHERE ticker = ? AND date(day) BETWEEN ? AND ?
ORDER BY day ASC, time ASC
""", ticker, start_date, end_date)

    def get_user_on(self, username, day):
        return self._db.query(
"""
SELECT *
FROM UserDaily
WHERE username = ? AND day = ?
""", username, day)

    def get_user_between(self, username, start_date, end_date):
        return self._db.query(
"""
SELECT *
FROM UserDaily
WHERE username = ? AND date(day) BETWEEN ? AND ?
""", username, start_date, end_date)

    def add_payment(self, sender, receiver, amount, category, currency='XUD'):
        self._db.run(
"""
INSERT INTO Payments (sender, receiver, amount, currency, day, time, category) VALUES
(?, ?, ?, ?, ?, ?, ?)
""", sender, receiver, amount, currency, utils.today(), utils.nowtime(), category)

    def update_ticker(self, old_ticker, new_ticker):
        self._db.run(
"""
UPDATE AssetIntraday
SET ticker = ?
WHERE ticker = ?
""", new_ticker, old_ticker)

        self._db.run(
"""
UPDATE AssetDaily
SET ticker = ?
WHERE ticker = ?
""", new_ticker, old_ticker)

        self._db.run(
"""
UPDATE UserDaily
SET assets = REPLACE(assets, ?, ?)
WHERE assets LIKE ?
""", f'"{old_ticker}"', f'"{new_ticker}"', f'%"{old_ticker}":%')

