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


class CreditState:
    DEFAULT = 'DEFAULT'
    PAID_CASH = 'CASH' 
    PAID_COLLATERAL = 'COLLATERAL'


class CreditDB(UNetSingleton):
    def __setup__(self):
        self._db = UNetDatabase('credit.db')

        self._db.run(
"""
CREATE TABLE IF NOT EXISTS Benchmarks(
    id_benchmark INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(16) NOT NULL UNIQUE,
    issuer TEXT NOT NULL,
    value INTEGER
)
""")

        self._db.run(
"""
CREATE TABLE IF NOT EXISTS Credits (
    id_credit INTEGER PRIMARY KEY AUTOINCREMENT,
    creditor TEXT NOT NULL,
    debtor TEXT NOT NULL,
    amount INTEGER NOT NULL,
    amount_due INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    duration INTEGER NOT NULL,
    matured INTEGER NOT NULL DEFAULT 0,
    frequency INTEGER NOT NULL DEFAULT 7,
    spread INTEGER NOT NULL DEFAULT 1,
    collateral INTEGER NOT NULL,
    note VARCHAR(255) NOT NULL,
    id_benchmark INTEGER NOT NULL,

    FOREIGN KEY (id_benchmark) REFERENCES Benchmarks(id_benchmark)
)
""")

        self._db.run(
"""
CREATE TABLE IF NOT EXISTS CreditHistory (
    id_instance INTEGER PRIMARY KEY AUTOINCREMENT,
    id_credit INTEGER NOT NULL,
    amount_due INTEGER NOT NULL,
    state VARCHAR(12) NOT NULL,
    day TEXT NOT NULL,

    FOREIGN KEY (id_credit) REFERENCES Credits(id_credit)
)
""")

    def add_credit(self, creditor, debtor, amount, amount_due, duration, frequency, collateral, spread, id_benchmark, note):
        self._db.run(
"""
INSERT INTO Credits (creditor, debtor, amount, amount_due, start_date, duration, frequency, spread, collateral, id_benchmark, note)
VALUES
(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", creditor, debtor, amount, amount_due, utils.today(), duration, frequency, spread, collateral, id_benchmark, note)

    def remove_credit(self, id_credit):
        self._db.run(
"""
DELETE FROM Credits
WHERE id_credit = ?
""", id_credit)

    def add_benchmark(self, name, issuer, value):
        self._db.run(
"""
INSERT INTO Benchmarks (name, issuer, value)
VALUES
(?, ?, ?)
""", name, issuer, value)

    def  remove_benchmark(self, id_benchmark):
        self._db.run(
"""
DELETE FROM  Benchmarks
WHERE id_benchmark = ?
""", id_benchmark)

    def update_benchmark(self, id_benchmark, value):
        self._db.run(
"""
UPDATE Benchmarks
SET value = ?
WHERE id_benchmark = ?
""", value, id_benchmark)

    def list_credits(self, username):
        return self._db.query(
"""
SELECT a.*, b.name, b.value
FROM Credits a
INNER JOIN Benchmarks b ON a.id_benchmark = b.id_benchmark
WHERE (creditor = ? OR debtor = ?) AND matured <= duration
ORDER BY (debtor)
""", username, username)

    def list_benchmarks(self):
        return self._db.query(
"""
SELECT *
FROM Benchmarks
ORDER BY (value) ASC
""")

    def update_matured_days(self):
        self._db.run(
"""
UPDATE Credits
SET matured = matured + 1
WHERE matured <= duration
""")

    def update_names(self, old_name, new_name):
        self._db.run(
"""
UPDATE Credits
SET creditor = ?
WHERE creditor =?
""", new_name, old_name)

        self._db.run(
"""
UPDATE Credits
SET debtor = ?
WHERE debtor =?
""", new_name, old_name)

        self._db.run(
"""
UPDATE Benchmarks
SET issuer = ?
WHERE issuer =?
""", new_name, old_name)

    def get_all_intrest_due(self):
        return self._db.query(
"""
SELECT a.*, b.value
FROM Credits a
INNER JOIN Benchmarks b ON a.id_benchmark = b.id_benchmark
WHERE (matured % frequency) = 0
""")
    
    def get_all_mature(self):
        return self._db.query(
"""
SELECT *
FROM Credits
WHERE matured = duration
""")

    def collateral_call(self, id_credit, amount_due):
        q = self._db.query(
"""
SELECT collateral
FROM Credits
WHERE id_credit = ?
""", id_credit)

        if q[0] < amount_due:
            return False
        
        self._db.run(
"""
UPDATE Credits
SET collateral = collateral - ?
WHERE id_credit = ?
""", amount_due, id_credit)

        return True

    def add_history_instance(self, id_credit, amount_due, state):
        self._db.run(
"""
INSERT INTO CreditHistory (id_credit, amount_due, state, day)
VALUES
(?, ?, ?, ?)
""", id_credit, amount_due, state, utils.today())

    def rollback_advancement(self, id_credit):
        self._db.run(
"""
UPDATE Credits
SET matured = matured - 1
WHERE id_credit = ?
""", id_credit)