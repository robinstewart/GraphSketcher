#!/usr/bin/env python3
"""Second check for resources.py candidates: could the name be built at run time?
Flags a candidate when a string literal in any source is a format string that
matches its name, or is a prefix/suffix (>=5 chars) of its name."""
import os, re, json
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
res = json.load(open(os.path.join(HERE, "work/resources.json")))
cand = [r for r in res if not r["users"] and not r["pbx_other"]]
lits = {}
for top in ("OmniGroup", "GraphSketcher"):
    for root, dirs, files in os.walk(os.path.join(REPO, top)):
        for f in files:
            if f.endswith((".m", ".h", ".c", ".mm")):
                for s in re.findall(r'"((?:[^"\\\n]|\\.)*)"', open(os.path.join(root, f), errors="ignore").read()):
                    lits.setdefault(s, os.path.relpath(os.path.join(root, f), REPO))
fmts = []
for s, f in lits.items():
    if "%" in s and len(re.sub(r"%[\d.]*[@dsilu]+", "", s)) >= 3:
        fmts.append((re.compile("^" + ".*".join(re.escape(p) for p in re.split(r"%[\d.]*[@dsilu]+", s)) + r"(\.\w+)?$"), s, f))
for r in cand:
    k = r["key"]; name = os.path.basename(r["file"]); hits = []
    for rx, s, f in fmts:
        if rx.match(k) or rx.match(name): hits.append(f"format {s!r} in {f}")
    for s, f in lits.items():
        if 5 <= len(s) < len(k) and (k.startswith(s) or k.endswith(s) or name.endswith(s)):
            hits.append(f"part {s!r} in {f}")
    r["dynamic"] = hits
    if hits: print(r["file"], "\n     ", "\n      ".join(hits[:4]))
json.dump(cand, open(os.path.join(HERE, "work/resource_candidates.json"), "w"), indent=1)
