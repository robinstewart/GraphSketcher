import os; os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "work"))
import json,sys
g=json.load(open(sys.argv[1])); E=g["edges"]
for t in sys.argv[2:]:
    print("==",t)
    for a,bs in sorted(E.items()):
        if t in bs: print("   <-",a, bs[t][:8])
