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


import sqlite3

from unet.singleton import UNetSingleton


class UNetDatabase:
    def __init__(self, filepath: str) -> None:
        self._filepath = filepath
    
    def query(self, qstring: str, *args) -> any:
        conn = sqlite3.connect(self._filepath)
        cur = conn.cursor()
        cur.execute(qstring, args)
        return cur.fetchall()
    
    def run(self, qstring: str, *args) -> any:
        conn = sqlite3.connect(self._filepath)
        cur = conn.cursor()
        cur.execute(qstring, args)
        return conn.commit()


class UNetLazyDatabase:
    def __init__(self, filepath: str) -> None:
        self._filepath = filepath
        self._connection = sqlite3.connect(self._filepath)

    def query(self, qstring: str, *args) -> any:
        cur = self._connection.cursor()
        cur.execute(qstring, args)
        return cur.fetchall()
    
    def issue(self, qstring: str, *args) -> any:
        cur = self._connection.cursor()
        cur.execute(qstring, args)

    def begin(self):
        self.issue('BEGIN TRANSACTION')

    def finalize(self):
        self.issue('END TRANSACTION')
        self._connection.commit()

    def __enter__(self):
        self.begin()
        return self
    
    def __exit__(self, *args):
        self.finalize()


class UNetUserDatabase(UNetSingleton):
    def __init__(self) -> None:
        self._db = UNetDatabase('unet_users.db')

        self.db.run('CREATE TABLE IF NOT EXISTS unet_user_credentials(username text, email str, password text)')
        self.db.run('CREATE TABLE IF NOT EXISTS unet_user_roles(username text, role text)')

        if self.exists('admin', None) < 1:
            self.add_user('admin', None, 'admin')
            self.add_role('admin', 'admin')

    def add_user(self, name: str, email: str, password: str) -> bool:
        if self.exists(name, password):
            return False
        
        self.db.run('INSERT INTO unet_user_credentials VALUES (?, ?, ?)', name, email, password)
        self.db.run('INSERT INTO unet_user_roles VALUES (?, ?)', name, 'user')
        return True
    
    def exists(self, name: str, password: str) -> bool:
        res = self.db.query('SELECT password FROM unet_user_credentials WHERE username = ?', name)

        if len(res) == 0:
            return 0
        
        if res[0][0] != password:
            return 1
        
        return 2
    
    def add_role(self, name: str, role: str) -> None:
        res = self.db.query('SELECT role FROM unet_user_roles WHERE username = ?', name)

        if role not in res:
            self.db.run('INSERT INTO unet_user_roles VALUES (?, ?)', name, role)

    def remove_role(self, name: str, role: str) -> None:
        res = self.db.query('SELECT role FROM unet_user_roles WHERE username = ?', name)

        if role in res:
            self.db.run('DELETE FROM unet_user_roles WHERE username = ? AND role = ?', name, role)

    def has_role(self, name: str, role: str) -> bool:
        return (role,) in self.db.query('SELECT role FROM unet_user_roles WHERE username = ?', name)

    def get_user_password(self, name: str) -> str:
        res = self.db.query('SELECT password FROM unet_user_credentials WHERE username = ?', name)
        return res[0][0]

    def set_user_password(self, name: str, password: str) -> None:
        self.db.run('UPDATE unet_user_credentials SET password = ? WHERE username = ?', password, name)

    def get_email_address(self, name: str) -> str:
        res = self.db.query('SELECT email FROM unet_user_credentials WHERE username = ?', name)
        return res[0][0]
    
    def set_email_address(self, name: str, email: str) -> None:
        self.db.run('UPDATE unet_user_credentials SET email = ? WHERE username = ?', email, name)

    def get_users(self) -> list:
        return self.db.query('SELECT username, email FROM unet_user_credentials')

    @property
    def db(self):
        return self._db
