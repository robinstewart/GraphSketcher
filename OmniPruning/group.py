import os; os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "work"))
import json,collections,os
rows=json.load(open("dead.json"))
by=collections.defaultdict(list)
for r in rows:
    d=os.path.dirname(r["files"][0]).replace("OmniGroup/Frameworks/","") if r["files"] else "?"
    by[d].append(r)
for d,rs in sorted(by.items(), key=lambda kv:-sum(r["m"]+r["h"] for r in kv[1])):
    nf=sum(len(r["files"]) for r in rs); nl=sum(r["m"]+r["h"] for r in rs)
    print(f"\n{d}: {len(rs)} units, {nf} files, {nl} lines")
    print("   "+", ".join(sorted(r["unit"].split("/")[1]+("*" if r["live_importers"] else "") for r in rs)))
