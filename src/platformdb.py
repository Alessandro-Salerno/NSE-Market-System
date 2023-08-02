import json
import logging
import os

from object_lock import ObjectLock
from repeated_timer import RepeatedTimer


class PlatformDB:
    def __init__(self, filename='platformdb.json', schema={}, default={}) -> None:
        self._filename = filename
        self._schema = schema
        self._free = True
        self._db = self._load()
        
        if self._db == {}:
            for key in schema.keys():
                self._db.__setitem__(key, {})
        
        self._timer = RepeatedTimer(15, self.save)


    def _load(self):
        l = self._get_content()
        if l is None:
            logging.warning('Empty PlatformDB Database!')
            return {}

        return self._get_items(l)
    
    def _get_content(self):
        f = None
        file_extensions = ['.new', '', '.old']

        for fext in file_extensions:
            f = self._load_from_file(self._filename + fext)
            if f is not None:
                break
        
        return f

    def _load_from_file(self, filename):
        try:
            with open(filename, 'r') as f:
                return dict(json.loads(f.read()))
        except:
            return None
        
    def _get_items(self, loaded: dict, schema=None, depth=0):
        sc = self._schema if schema is None else schema
        result = dict(sc).copy() if depth > 1 else {}

        for key in loaded.keys():
            if isinstance(loaded[key], dict):
                result.__setitem__(key, self._get_items(loaded[key], depth=depth + 1, schema=sc[key] if key in sc.keys() else sc))
                continue

            result.__setitem__(key, loaded[key])
        
        if '__PLATFORMDB_LOCK__' in result.keys():
            pl = result.pop('__PLATFORMDB_LOCK__')
            return ObjectLock(dict(result)) if pl else dict(result)

        return result

    def save(self):
        self._free = False

        new_json = self.to_json()
        if not os.path.exists(self._filename):
            with open(self._filename, 'w') as file:
                file.write(new_json)
            self._free = True
            return

        with open(self._filename + '.new', 'w') as new_file:
            new_file.write(new_json)
        
        old_json = ''
        with open(self._filename, 'r') as file:
            old_json = str(file.read())

        with open(self._filename + '.old', 'w') as old_file:
            old_file.write(old_json)
        
        with open(self._filename, 'w') as file:
            file.write(new_json)

        os.remove(self._filename + '.new')

        self._free = True

    def to_json(self):
        return json.dumps(PlatformDB.to_dict(self._db), indent=2)

    @staticmethod
    def to_dict(target: dict, lock=False):
        d = {}

        for key in target.keys():
            if isinstance(target[key], ObjectLock):
                with target[key] as i:
                    if isinstance(i, dict):
                        d.__setitem__(key, PlatformDB.to_dict(i, lock=True))
                        continue

            if isinstance(target[key], dict):
                d.__setitem__(key, PlatformDB.to_dict(target[key]))
                continue

            d.__setitem__(key, target[key])

        if lock:
            d.__setitem__('__PLATFORMDB_LOCK__', True)
        
        return d

    @property
    def filename(self):
        return self._filename
    
    @property
    def free(self):
        return self._free

    @property
    def db(self):
        while not self.free:
            pass

        return self._db
    
    @property
    def schema(self):
        return self._schema

    @property
    def timer(self):
        return self._timer
