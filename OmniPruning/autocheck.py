import os; os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "work"))
import json
g=json.load(open("graph.json")); gn=json.load(open("graph_nosdk.json"))
units=g["units"]; E=g["edges"]; EN=gn["edges"]
OMNI={"OmniAppKit","OmniBase","OmniFoundation","OmniInspector","OmniQuartz","OmniUnzip"}
def reach(roots, edges, skip=()):
    seen=set(); st=list(roots)
    while st:
        n=st.pop()
        if n in seen: continue
        seen.add(n); st+=list(edges.get(n,{}))
    return seen
roots=[r for r in g["roots"] if r!="ROOT/autorun"]
R0=reach(roots,E)
only=sorted(n for n in set(g["reach"])-R0 if units.get(n,{}).get("target") in OMNI)
for t in only:
    callers={}
    for a,bs in EN.items():
        if t in bs and a in R0 and a!=t:
            callers[a]=bs[t]
    sel=set(x for v in callers.values() for x in v)
    print(f"{units[t]['loc']:5} {t}\n      live callers (no-sdk graph) via: {sorted(sel)[:12]}")
