from creditdb import CreditDB

db = CreditDB()
db.add_benchmark("KEY", "UNB", -720)
print(db.list_benchmarks())
db.add_credit("PLTB", "UNIT", 100, 100, 7, 7, 20, 0, 1, "TEST")
print(db.list_credits("PLTB"))
db.update_matured_days()
print(db.list_credits("PLTB"))
db.remove_credit(1)
print(db.list_credits("PLTB"))
db.remove_benchmark(1)
print(db.list_benchmarks())
