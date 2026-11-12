import os; os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "work"))
import json,collections
g=json.load(open("graph.json")); units=g["units"]; E=g["edges"]
OMNI={"OmniAppKit","OmniBase","OmniFoundation","OmniInspector","OmniQuartz","OmniUnzip"}
def reach(roots, skip=()):
    seen=set(); st=list(roots)
    while st:
        n=st.pop()
        if n in seen: continue
        seen.add(n)
        if n in skip: continue
        st+=list(E.get(n,{}))
    return seen
roots=[r for r in g["roots"] if r!="ROOT/autorun"]
R0=reach(roots); R1=set(g["reach"])
only=[n for n in R1-R0 if units.get(n,{}).get("target") in OMNI]
print("reachable only via autorun/patch:",len(only),sum(units[n]["loc"] for n in only))
auto=E.get("ROOT/autorun",{})
# attribute each autorun-only unit to autorun roots that reach it
for a in sorted(auto, key=lambda a:-len(reach([a]) - R0)):
    if a in R0: continue
    sub=[n for n in reach([a])-R0 if units.get(n,{}).get("target") in OMNI]
    print(f"\n{a}  (+{sum(units[n]['loc'] for n in sub)} loc, {len(sub)} units)  why={auto[a][:3]}")
    print("   ", ", ".join(sorted(x.split('/')[1] for x in sub if x!=a)))
