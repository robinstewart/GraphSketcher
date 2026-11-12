import os; os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "work"))
import json, itertools
g=json.load(open("graph.json")); units=g["units"]; E=g["edges"]
OMNI={"OmniAppKit","OmniBase","OmniFoundation","OmniInspector","OmniQuartz","OmniUnzip"}
keep={"OmniFoundation/OFBundleRegistry","OmniAppKit/OAControlTextColorTransformer","OmniInspector/OIFontInspector"}
succ={a:[b for b in bs] for a,bs in E.items()}
succ["ROOT/autorun"]=[b for b in succ.get("ROOT/autorun",[]) if b in keep]
def reach(banned):
    seen=set(); st=[r for r in g["roots"] if r not in banned]
    while st:
        n=st.pop()
        if n in seen: continue
        seen.add(n)
        for m in succ.get(n,()):
            if m not in seen and m not in banned: st.append(m)
    return seen
base=reach(set())
loc=lambda ns: sum(units[n]["loc"] for n in ns if units.get(n,{}).get("target") in OMNI)
live=[n for n in base if units.get(n,{}).get("target") in OMNI]
single={n: base-reach({n}) for n in live}
res=[]
for a,b in itertools.combinations(live,2):
    if a in single[b] or b in single[a]: continue
    fr=base-reach({a,b})
    extra=loc(fr)-loc(single[a]|single[b])
    if extra>=300: res.append((extra,loc(fr),a,b,fr-single[a]-single[b]-{a,b}))
res.sort(reverse=True)
for e,t,a,b,fr in res[:25]:
    print(f"+{e:5} total={t:5}  {a} + {b}\n        extra: {', '.join(sorted(x.split('/')[1] for x in fr))}")
# per project unit
print("\n=== cutting all Omni refs from one project file")
for p in sorted(n for n in base if units.get(n,{}).get("target") in ("GraphSketcher","GraphSketcherModel")):
    saved=succ.get(p,[])
    succ[p]=[m for m in saved if units.get(m,{}).get("target") not in OMNI]
    fr=base-reach(set())
    succ[p]=saved
    if loc(fr)>=200: print(f"{loc(fr):5} {p}: {', '.join(sorted(x.split('/')[1] for x in fr if units.get(x,{}).get('target') in OMNI))}")
