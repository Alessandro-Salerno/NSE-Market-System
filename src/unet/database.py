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


import sqlite3
import threading

from unet.singleton import UNetSingleton

class UNetQueryMode:
    QUERY = 0
    EXEC = 1

class UNetQuery:
    def __init__(self, query, args, mode):
        self.query = query
        self.args = args
        self.mode = mode
        self.result = None
        self._condition = threading.Condition()


class UNetDatabase:
    def __init__(self, filepath: str) -> None:
        self._filepath = filepath

        self._query_queue = []
        self._query_submit = threading.Condition()
        self._db_thread = threading.Thread(target=self._db_main, args=(), daemon=True)
        self._db_thread.start()
    
    def query(self, qstring: str, *args) -> any:
        query = UNetQuery(qstring, args, UNetQueryMode.QUERY)
        with query._condition:
            with self._query_submit:
                self._query_queue.append(query)
                self._query_submit.notify()
            query._condition.wait()
        return query.result

    def run(self, qstring: str, *args) -> any:
        query = UNetQuery(qstring, args, UNetQueryMode.EXEC)
        with query._condition:
            with self._query_submit:
                self._query_queue.append(query)
                self._query_submit.notify()
            query._condition.wait()
        return query.result

    def _db_main(self):
        conn = sqlite3.connect(self._filepath)
        cur = conn.cursor()
        
        while True:
            with self._query_submit:
                while len(self._query_queue) == 0:
                    self._query_submit.wait()

                query = self._query_queue.pop(0)
                cur.execute(query.query, query.args)

                match query.mode:
                    case UNetQueryMode.QUERY:
                        query.result = cur.fetchall()

                    case UNetQueryMode.EXEC:
                        query.result = conn.commit()

                with query._condition:
                    query._condition.notify()


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
        self._db = UNetDatabase('db/unet_users.db')

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

    def change_user_username(self, old_name: str, new_name: str):
        return self.db.run('UPDATE unet_user_credentials SET username = ? WHERE username = ?', new_name, old_name)

    @property
    def db(self):
        return self._db
