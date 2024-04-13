import json
from types import NoneType


file = None 
with open("exchange.json", 'r') as f:
    file = json.loads(f.read())

for name, user in file['usersByName'].items():
    user['immediate']['orders'] = []

file['ordersById'] = {}
if 'ordrsById' in file:
    file.pop('ordrsById')

with open('exchange.json', 'w') as f:
    f.write(json.dumps(file))

