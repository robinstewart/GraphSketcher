#!/usr/bin/env python3
"""Usage: cut.py TARGET [TARGET...] [--keep-autorun X,Y] [--drop-autorun]
Simulate cutting every live reference into the TARGET units. Prints the edges
that would need refactoring (from units that stay live) and the units freed."""
import json, os, sys, collections
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
g = json.load(open(os.path.join(S, os.environ.get("GRAPH", "graph.json"))))
units, E = g["units"], g["edges"]
OMNI = {"OmniAppKit", "OmniBase", "OmniFoundation", "OmniInspector", "OmniQuartz", "OmniUnzip"}
args = sys.argv[1:]
drop_autorun = "--drop-autorun" in args  # treat hook-only units as deletable (see report tier B)
keep = {"OmniAppKit/OAControlTextColorTransformer", "OmniInspector/OIFontInspector"} | ({"OmniFoundation/OFBundleRegistry"} if "--cut-bundleregistry" not in sys.argv else set())
targets = [a for a in args if not a.startswith("--")]
def isomni(n): return units.get(n, {}).get("target") in OMNI
def reach(roots, banned=frozenset()):
    seen = set(); st = [r for r in roots if r not in banned]
    while st:
        n = st.pop()
        if n in seen: continue
        seen.add(n)
        for m in E.get(n, {}):
            if m in banned: continue
            if n == "ROOT/autorun" and drop_autorun and m not in keep: continue
            st.append(m)
    return seen
roots = g["roots"]
before = reach(roots)
after = reach(roots, banned=set(targets))
freed = sorted(n for n in before - after if isomni(n))
cut_edges = []
for a in after:
    for b, why in E.get(a, {}).items():
        if b in freed:
            cut_edges.append((a, b, why))
print(f"freed: {len(freed)} units, {sum(units[n]['loc'] for n in freed)} loc, {sum(len(units[n]['files']) for n in freed)} files")
for n in freed:
    print(f"   {units[n]['loc']:5}  {n}")
print("references to refactor (live -> freed):")
for a, b, why in sorted(cut_edges):
    print(f"   {a} -> {b}: {', '.join(why[:6])}")
