import threading


class ObjectLock:
    def __init__(self, target) -> None:
        self._target = target
        self._lock = threading.Lock()

    def __enter__(self):
        self._lock.acquire()
        return self._target

    def __exit__(self, *args, **kwargs):
        self._lock.release()
    
    def get_unsafe(self):
        return self._target

    @property
    def lock(self):
        return self._lock
