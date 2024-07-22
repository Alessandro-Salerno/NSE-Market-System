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
                self._submit_condition.wait()

                notification = self._notifications[0]
                usernames = notification.username
                if isinstance(notification.username, str):
                    usernames = [notification.username,]

                for username in usernames:
                    if username not in self.user_events:
                        continue

                    user = self.user_events[username]
                    usernames.remove(username)

                    if notification.event_name not in user:
                        continue

                    cond = user.pop(notification.event_name)
                    with cond:
                        cond.notify()

                if len(usernames) == 0:
                    self._notifications.pop(0)
