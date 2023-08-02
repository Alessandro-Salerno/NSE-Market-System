from datetime import datetime, timedelta
import pytz


def value_fmt(value):
    return '--' if value is None else value


def are_none(*values):
    res = True
    for val in values:
        res = res and val is not None
    return res


def today():
    now = datetime.now(tz=pytz.timezone('Europe/Rome'))
    return now.strftime('%Y-%m-%d')


def tomorrow():
    tmr = datetime.now(tz=pytz.timezone('Europe/Rome')) + timedelta(1)
    return tmr.strftime('%Y-%m-%d')


def now():
    now = datetime.now(tz=pytz.timezone('Europe/Rome'))
    return now.strftime('%Y-%m-%d %H:%M:%S')
