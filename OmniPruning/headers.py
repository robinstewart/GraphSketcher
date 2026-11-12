#!/usr/bin/env python3
"""For each dead unit, find importers of its header among live source files."""
import json, os, re, glob, collections, sys
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
g = json.load(open(os.path.join(S, "graph.json")))
units = g["units"]; reach = set(g["reach"])
OMNI_T = {"OmniAppKit", "OmniBase", "OmniFoundation", "OmniInspector", "OmniQuartz", "OmniUnzip"}
dead = sorted(n for n, u in units.items() if u["target"] in OMNI_T and n not in reach)
dead_bases = {n.split("/", 1)[1]: n for n in dead}

# live source files: project sources (Mac) + live omni unit files + all headers (headers are live if imported by live)
live_files = set()
for root, dirs, files in os.walk(os.path.join(REPO, "GraphSketcher")):
    if "/iPad" in root: continue
    for f in files:
        if f.endswith((".m", ".h", ".c", ".mm", ".pch")):
            live_files.add(os.path.join(root, f))
for n in reach:
    for f in units.get(n, {}).get("files", []):
        live_files.add(os.path.join(REPO, f))
UMBRELLA = {"OmniFoundation.h", "OmniAppKit.h", "OmniBase.h", "OmniQuartz.h", "OmniInspector.h", "OmniUnzip.h", "OmniFoundation-Mac.h"}
imp_re = re.compile(r'#\s*(?:import|include)\s*[<"](?:\w+/)?([\w\-+]+)\.h[>"]')
importers = collections.defaultdict(set)
for f in live_files:
    try: txt = open(f, errors="ignore").read()
    except OSError: continue
    for m in imp_re.finditer(txt):
        importers[m.group(1)].add(os.path.relpath(f, REPO))
# umbrella headers importing dead headers
umb = collections.defaultdict(list)
for fw in OMNI_T:
    for f in glob.glob(f"{REPO}/OmniGroup/Frameworks/{fw}/**/*.h", recursive=True):
        if os.path.basename(f) in UMBRELLA or os.path.basename(f).endswith("-Mac.h"):
            for i, line in enumerate(open(f, errors="ignore")):
                m = imp_re.search(line)
                if m and m.group(1) in dead_bases:
                    umb[m.group(1)].append(os.path.relpath(f, REPO))

def lines(p):
    try: return sum(1 for _ in open(os.path.join(REPO, p), errors="ignore"))
    except OSError: return 0
rows = []
for n in dead:
    base = n.split("/", 1)[1]
    u = units[n]
    hfile = [f for f in u["files"] if f.endswith(".h")]
    mfile = [f for f in u["files"] if not f.endswith(".h")]
    imps = sorted(i for i in importers.get(base, ()) if os.path.basename(i) not in UMBRELLA and not i.endswith(base + ".m") and not i.endswith(base + ".h"))
    rows.append(dict(unit=n, m=sum(lines(f) for f in mfile), h=sum(lines(f) for f in hfile), files=u["files"], live_importers=imps, umbrella=umb.get(base, [])))
json.dump(rows, open(os.path.join(S, "dead.json"), "w"), indent=1)
tot_m = sum(r["m"] for r in rows); tot_h = sum(r["h"] for r in rows)
clean = [r for r in rows if not r["live_importers"]]
print(f"dead units {len(rows)}  .m lines {tot_m}  .h lines {tot_h}")
print(f"  with no live importer (besides umbrella): {len(clean)} units, {sum(r['m']+r['h'] for r in clean)} lines")
for r in rows:
    if r["live_importers"]:
        print(f"{r['unit']:55} m={r['m']:5} h={r['h']:4}  importers: {', '.join(r['live_importers'][:5])}{' …' if len(r['live_importers'])>5 else ''}")
