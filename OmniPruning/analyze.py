#!/usr/bin/env python3
import json, os, sys, collections
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
g = json.load(open(os.path.join(S, "graph.json")))
units, edges = g["units"], g["edges"]
OMNI_T = {"OmniAppKit", "OmniBase", "OmniFoundation", "OmniInspector", "OmniQuartz", "OmniUnzip"}
def isomni(n): return units.get(n, {}).get("target") in OMNI_T
def loc(n): return units[n]["loc"] if isomni(n) else 0

ROOT = "__ROOT__"
succ = collections.defaultdict(set)
for a, bs in edges.items():
    for b in bs:
        succ[a].add(b)
for r in g["roots"]:
    succ[ROOT].add(r)

# reachable + RPO
order, seen = [], set()
def dfs(n):
    stack = [(n, iter(sorted(succ[n])))]
    seen.add(n)
    while stack:
        node, it = stack[-1]
        nxt = next(it, None)
        if nxt is None:
            order.append(node); stack.pop()
        elif nxt not in seen:
            seen.add(nxt); stack.append((nxt, iter(sorted(succ[nxt]))))
dfs(ROOT)
rpo = order[::-1]
idx = {n: i for i, n in enumerate(rpo)}
pred = collections.defaultdict(set)
for a in rpo:
    for b in succ[a]:
        if b in idx:
            pred[b].add(a)
idom = {ROOT: ROOT}
def intersect(a, b):
    while a != b:
        while idx[a] > idx[b]: a = idom[a]
        while idx[b] > idx[a]: b = idom[b]
    return a
changed = True
while changed:
    changed = False
    for n in rpo[1:]:
        ps = [p for p in pred[n] if p in idom]
        if not ps: continue
        new = ps[0]
        for p in ps[1:]: new = intersect(p, new)
        if idom.get(n) != new:
            idom[n] = new; changed = True
kids = collections.defaultdict(list)
for n, d in idom.items():
    if n != d: kids[d].append(n)
def subtree(n):
    out, st = [], [n]
    while st:
        x = st.pop(); out.append(x); st += kids[x]
    return out

# Report: omni nodes whose idom is a project node or ROOT, or any omni node with big subtree
rows = []
for n in rpo:
    if not isomni(n): continue
    st = subtree(n)
    l = sum(loc(x) for x in st)
    inc = {p: edges[p][n] for p in pred[n]}
    rows.append((l, n, len([x for x in st if isomni(x)]), inc, st))
rows.sort(reverse=True)
mode = sys.argv[1] if len(sys.argv) > 1 else "dom"
if mode == "dom":
    for l, n, cnt, inc, st in rows:
        if l < 400 or cnt < 2: continue
        print(f"\n### {n}  subtree_loc={l} units={cnt}  idom={idom[n]}")
        print("   subtree:", ", ".join(sorted(x for x in st if x != n)))
        for p, r in sorted(inc.items()):
            print(f"   <- {p}: {', '.join(r[:6])}{' …' if len(r) > 6 else ''}")
elif mode == "unreach":
    un = [n for n in units if isomni(n) and n not in idx]
    print("unreachable omni units", len(un), sum(loc(n) for n in un))
    by = collections.defaultdict(list)
    for n in un: by[n.split("/")[0]].append(n)
    for fw, ns in sorted(by.items()):
        print(f"\n== {fw}: {len(ns)} units, {sum(loc(n) for n in ns)} loc")
        for n in sorted(ns, key=lambda n: -loc(n)):
            print(f"   {loc(n):5} {n}")
elif mode == "reach":
    for n in sorted(idx):
        if isomni(n):
            print(f"{loc(n):5} {n}  idom={idom.get(n)}  preds={sorted(pred[n])[:8]}")
