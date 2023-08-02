import json


UNET_PROTOCOL_VERSION = '1.0.0'


class UNetMessageType:
    AUTH = 'AUTH'
    STATUS = 'STATUS'
    VALUE = 'VALUE'
    TABLE = 'TABLE'
    CHART = 'CHART'
    MULTI = 'MULTI'


class UNetAuthMode:
    LOGIN = 'LOGIN'
    SIGNUP = 'SIGNUP'


class UNetStatusMode:
    OK = 'OK'
    ERR = 'ERR'


class UNetStatusCode:
    DONE = 'DONE'
    EXC = 'EXC'
    BAD = 'BAD'
    VER = 'VER'
    DENY = 'DENY'


def unet_make_message(**kwargs):
    return json.dumps(kwargs)


def unet_make_auth_message(mode: str, name: str, email: str, password: str):
    return unet_make_message(
        type=UNetMessageType.AUTH,
        version=UNET_PROTOCOL_VERSION,
        mode=mode,
        name=name,
        email=email,
        password=password
    )


def unet_make_status_message(mode: str, code: str, message: str):
    return unet_make_message(
        type=UNetMessageType.STATUS,
        mode=mode,
        code=code,
        message=message
    )
9

def unet_make_table_message(title: str, columns: list, rows: list):
    return unet_make_message(
        type=UNetMessageType.TABLE,
        title=title,
        columns=columns,
        rows=rows
    )


def unet_make_chart_message(*series, title: str, xformat: str, xlabel: str, ylabel: str):
    return unet_make_message(
        type=UNetMessageType.CHART,
        title=title,
        xformat=xformat,
        xlabel=xlabel,
        ylabel=ylabel,
        series=series
    )


def unet_make_chart_series(name: str, x: list, y: list):
    return {
        'name': name,
        'x': x,
        'y': y
    }


def unet_make_multi_message(*messages):
    return unet_make_message(
        type=UNetMessageType.MULTI,
        messages=messages
    )

def unet_make_value_message(name: str, value: any):
    return unet_make_message(
        type=UNetMessageType.VALUE,
        name=name,
        value=value
    )
