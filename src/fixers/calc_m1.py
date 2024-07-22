import json


file = None 
with open("db/exchange.json", 'r') as f:
    file = json.loads(f.read())

m1 = 0
for name, user in file['usersByName'].items():
    m1 += user["immediate"]["settled"]["balance"] + user["immediate"]["current"]["balance"]

m1 -= file["usersByName"]["UNBMM"]["immediate"]["settled"]["balance"]
m1 -= file["usersByName"]["UNB"]["immediate"]["settled"]["balance"]
print(int(m1))


