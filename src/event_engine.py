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
from collections import defaultdict
import threading


class ExchangeEvent:
    TEST = 0
    ORDER_FILLED = 1


class EventNotification:
    def __init__(self, username, event_name) -> None:
        self.username = username
        self.event_name = event_name


class EventEngine(UNetSingleton):
    def __setup__(self):
        self.user_events = defaultdict(lambda: {})
        self._submit_condition = threading.Condition()
        self._notifications = []

        self._engine_thread = threading.Thread(target=self._engine_loop, args=(), daemon=True)
        self._engine_thread.start()
        
    def subscribe(self, username, event_name):
        c = threading.Condition()
        with c:
            self.user_events[username].__setitem__(getattr(ExchangeEvent, event_name), c)
            if len(self._notifications) != 0:
                with self._submit_condition:
                    self._submit_condition.notify()
            c.wait()
    
    def notify_async(self, username, event_name):
        n = EventNotification(username, event_name)
        with self._submit_condition:
            self._notifications.append(n)
            self._submit_condition.notify()

    def _engine_loop(self):
        while True:
            with self._submit_condition:
                while len(self._notifications) == 0:
                    self._submit_condition.wait()

                for notification in self._notifications.copy():
                    usernames = notification.username
                    if isinstance(notification.username, str):
                        usernames = [notification.username,]

                    username_count = 0

                    for username in usernames.copy():
                        if username not in self.user_events:
                            usernames.remove(username)
                            continue

                        user = self.user_events[username]
                        username_count += 1

                        if notification.event_name not in user:
                            usernames.remove(username)
                            continue

                        cond = user.pop(notification.event_name)
                        with cond:
                            cond.notify()

                    if len(usernames) == username_count:
                        self._notifications.remove(notification)
