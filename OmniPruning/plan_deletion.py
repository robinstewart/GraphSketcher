#!/usr/bin/env python3
"""Write work/delete_list.json: files that are safe to delete with #import-line removals only.
= (sources no target compiles) + (compiled units unreachable on the Mac graph)
  - anything an iOS target builds that is reachable on the iPad graph
  - headers still needed for inline functions/types, and a few hand-picked keeps.
Prints every #import of a to-be-deleted header found in files that stay."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); W = os.path.join(HERE, "work"); REPO = os.path.dirname(HERE)
J = lambda n: json.load(open(os.path.join(W, n)))
gm, gi, T = J("graph.json"), J("graph_ios.json"), J("targets.json")
MAC_T = {"OmniAppKit (Framework)", "OmniBase", "OmniFoundation", "OmniInspector", "OmniQuartz", "OmniUnzip",
         "GraphSketcher", "GraphSketcherModel", "GSQuickLookPlugin", "GSSpotlightPlugin", "LinkBack", "FixStringsFile"}
built = {}  # file -> set of (platform, target)
for proj, ts in T.items():
    for t, v in ts.items():
        plat = "mac" if (t in MAC_T and "iPad" not in proj) else "ios"
        for k in ("sources", "headers", "resources"):
            for f in v[k]: built.setdefault(f, set()).add((plat, t, k))
def unit_files(g):
    live, dead = set(), set(); reach = set(g["reach"])
    for n, u in g["units"].items():
        (live if n in reach else dead).update(u["files"])
    return live, dead - live
mac_live, mac_dead = unit_files(gm); ios_live, ios_dead = unit_files(gi)
MACFW = ["OmniAppKit", "OmniBase", "OmniFoundation", "OmniInspector", "OmniQuartz", "OmniUnzip"]
cand = set(mac_dead)
# sources that no target compiles and nothing #includes (uncompiled_sources.txt: in no build phase and not #included anywhere; checked by hand)
for l in open(os.path.join(HERE, "uncompiled_sources.txt")):
    cand.add("OmniGroup/Frameworks/" + l.strip().lstrip("./"))
KEEP_BASENAMES = {  # header-only uses on the Mac (inline functions, types, macros)
    "CFDictionary-OFExtensions.h", "OFDataBuffer.h", "OATextAttachment.h",
    "OFTransientObjectsTracker.h", "OFTransientObjectsTracker.m"} | set(json.load(open(os.path.join(HERE, "keep_by_hand.json"))))
keep = {}
for f in sorted(cand):
    b = os.path.basename(f)
    if b in KEEP_BASENAMES: keep[f] = "kept by hand (header-only use or build needs it)"
    elif f in ios_live: keep[f] = "reachable on iPad graph"
    elif f in mac_live: keep[f] = "reachable on Mac graph"
    else:
        srcs = [x for x in built.get(f, ()) if x[2] == "sources"]
        for plat, t, k in srcs:
            g_dead = mac_dead if plat == "mac" else ios_dead
            if f not in g_dead: keep[f] = f"compiled by {t} but not in that platform's graph"
# keep .h/.m pairs together
stems = {os.path.splitext(f)[0] for f in keep}
for f in sorted(cand):
    if f not in keep and os.path.splitext(f)[0] in stems and os.path.basename(f) not in ("OFDataBuffer.m", "OATextAttachment.m", "CFDictionary-OFExtensions.m"):
        keep[f] = "paired with a kept file"
# a header listed in an iOS target but whose unit isn't in the iOS graph: keep unless its .m is iOS-dead
for f in sorted(cand):
    if f in keep or not f.endswith(".h"): continue
    if any(p == "ios" for p, t, k in built.get(f, ())) and f not in ios_dead:
        keep[f] = "header in an iOS target with no iOS unit"
        m = os.path.splitext(f)[0] + ".m"
        if m in cand: keep[m] = "paired with a kept file"
delete = sorted(f for f in cand if f not in keep and os.path.exists(os.path.join(REPO, f)))
json.dump(delete, open(os.path.join(W, "delete_list.json"), "w"), indent=1)
json.dump(keep, open(os.path.join(W, "kept_candidates.json"), "w"), indent=1)
nl = lambda fs: sum(sum(1 for _ in open(os.path.join(REPO, f), errors="ignore")) for f in fs)
print(f"candidates {len(cand)}; keep {len(keep)}; delete {len(delete)} files, {nl(delete)} lines")
# importers
gone = {os.path.basename(f) for f in delete if f.endswith(".h")}
stay_names = set()
imp = re.compile(r'^\s*#\s*(?:import|include)\s*[<"]([^>"]+)[>"]')
hits = []
for root, d, fs in os.walk(REPO):
    if "/OmniPruning" in root or "/.git" in root or "DerivedData" in root: continue
    for f in fs:
        p = os.path.join(root, f); r = os.path.relpath(p, REPO)
        if not f.endswith((".h", ".m", ".mm", ".c", ".pch")) or r in delete: continue
        if f.endswith(".h"): stay_names.add(f)
        for i, line in enumerate(open(p, errors="ignore"), 1):
            m = imp.match(line)
            if m and os.path.basename(m.group(1)) in gone: hits.append((r, i, line.strip()))
print("basename clashes between deleted and remaining headers:", sorted(gone & stay_names))
json.dump(hits, open(os.path.join(W, "import_hits.json"), "w"), indent=1)
print("import lines to remove:", len(hits))
if "-v" in sys.argv:
    for h in hits: print("  ", *h)
