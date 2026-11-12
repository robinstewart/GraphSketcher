#!/usr/bin/env python3
"""Build a compilation-unit dependency graph from .o files and compute
reachability + dominator subtrees for Omni framework units."""
import os, re, subprocess, sys, json, collections, glob, plistlib

S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = os.environ.get("PLATFORM", "mac")  # "mac" or "ios"
if PLATFORM == "mac":
    INT = os.path.join(S, "DD/Build/Intermediates.noindex"); CONFIG = "Debug"
    OMNI = {"OmniAppKit", "OmniBase", "OmniFoundation", "OmniInspector", "OmniQuartz", "OmniUnzip"}
    PROJ = {"GraphSketcher", "GraphSketcherModel", "GSQuickLookPlugin", "GSSpotlightPlugin", "LinkBack"}
    DEFAULT_GRAPH, SDK_FILE = "graph.json", "sdk_selectors.txt"
else:
    INT = os.path.join(S, "DDiOS/Build/Intermediates.noindex"); CONFIG = "Debug-iphonesimulator"
    OMNI = {"OmniAppKit", "OmniBase", "OmniFoundation", "OmniQuartz", "OmniUnzip", "OmniDAV", "OmniDocumentStore",
            "OmniFileExchange", "OmniFileStore", "OmniUI", "OmniUIDocument"}
    PROJ = {"GraphSketcher-iPad"}
    DEFAULT_GRAPH, SDK_FILE = "graph_ios.json", "sdk_selectors_ios.txt"
FWDIR = {fw: os.path.join(REPO, "OmniGroup/Frameworks", "OmniUI" if fw == "OmniUIDocument" else fw) for fw in OMNI}

def sh(args):
    return subprocess.run(args, capture_output=True, text=True).stdout

units = {}  # uid -> dict
for o in glob.glob(INT + "/*/" + CONFIG + "/*.build/Objects-normal/arm64/*.o"):
    target = o[len(INT)+1:].split("/")[0].replace(".build", "")
    if target not in OMNI | PROJ:
        continue
    base = os.path.basename(o)[:-2]
    uid = f"{target}/{base}"
    u = units.setdefault(uid, dict(target=target, base=base, defs=set(), undef=set(),
                                    sels_used=set(), meths=set(), catmeths=set(), strings=set()))
    for line in sh(["nm", "-m", o]).splitlines():
        m = re.match(r"\s*(?:[0-9a-f]+)?\s*\((.*?)\) (non-external|external|weak external|weak private external|private external)((?: \[[^\]]*\]| \(was a private external\))*) (.*)$", line)
        if not m:
            continue
        sect, ext, _flags, name = m.groups()
        if sect == "undefined":
            if name.startswith("_objc_msgSend$"):
                u["sels_used"].add(name[len("_objc_msgSend$"):])
            else:
                u["undef"].add(name)
            continue
        mm = re.match(r"([-+])\[(\S+?)(?:\((\S*)\))? (.+)\]$", name)
        if mm:
            sign, cls, cat, sel = mm.groups()
            u["meths"].add(sel)
            if cat is not None:
                u["catmeths"].add((cls, cat, sel))
            continue
        if ext != "non-external":
            u["defs"].add(name)
    # selectors via @selector and class-name strings
    for sect in (("__TEXT", "__objc_methname"), ("__TEXT", "__cstring")):
        out = sh(["otool", "-v", "-s", sect[0], sect[1], o])
        for line in out.splitlines()[2:]:
            mm2 = re.match(r"^[0-9a-f]+\s+(.*)$", line)
            if mm2:
                s = mm2.group(1).strip()
                if sect[1] == "__objc_methname":
                    u["sels_used"].add(s)
                else:
                    u["strings"].add(s)
    u["sels_used"] -= u["meths"]

# Sources a target lists but that produced no object file (they failed to compile).
# Model them from their text, very conservatively: every identifier counts as a possible
# class name, C symbol, or first selector keyword.
TEXT_UNITS = {}
tj = os.path.join(S, "targets.json")
if os.path.exists(tj):
    built = {(u["target"], u["base"]) for u in units.values()}
    for proj, ts in json.load(open(tj)).items():
        pname = os.path.basename(proj).replace(".xcodeproj", "")
        if pname not in OMNI | PROJ: continue
        if not any(u["target"] == pname for u in units.values()): continue
        for t, v in ts.items():
            if PLATFORM == "mac" and ("Touch" in t or "iPad" in t): continue
            if PLATFORM == "ios" and pname in ("OmniAppKit", "OmniBase", "OmniFoundation", "OmniQuartz", "OmniUnzip") and "Touch" not in t: continue
            for f in v["sources"]:
                base = os.path.splitext(os.path.basename(f))[0]
                if f.endswith((".m", ".mm", ".c")) and (pname, base) not in built and os.path.exists(os.path.join(REPO, f)):
                    uid = f"{pname}/{base}"
                    toks = set(re.findall(r"[A-Za-z_]\w*", open(os.path.join(REPO, f), errors="ignore").read()))
                    units[uid] = dict(target=pname, base=base, defs=set(), undef=set(), sels_used=set(), meths=set(),
                                      catmeths=set(), strings=set(toks))
                    TEXT_UNITS[uid] = toks
    if TEXT_UNITS: print("modelled from source text (no object file):", sorted(TEXT_UNITS))

# source file lines
def find_src(fw, base):
    hits = []
    for ext in (".m", ".mm", ".c", ".h"):
        hits += glob.glob(os.path.join(FWDIR[fw], "**", base + ext), recursive=True)
    return hits

def lines(path):
    try:
        with open(path, errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0

for uid, u in units.items():
    if u["target"] in OMNI:
        u["files"] = sorted(set(os.path.relpath(p, REPO) for p in find_src(u["target"], u["base"])))
    else:
        u["files"] = []
    u["loc"] = sum(lines(os.path.join(REPO, p)) for p in u["files"])

# symbol definers
SDK_SELS = set(open(os.path.join(S, SDK_FILE)).read().split())
SDK_FILTER = not os.environ.get("NO_SDK_FILTER")
sym_def = collections.defaultdict(set)
cls_def = {}
cat_sel_def = collections.defaultdict(set)
for uid, u in units.items():
    for d in u["defs"]:
        sym_def[d].add(uid)
        m = re.match(r"_OBJC_CLASS_\$_(\w+)", d)
        if m:
            cls_def[m.group(1)] = uid
    for cls, cat, sel in u["catmeths"]:
        if SDK_FILTER and sel in SDK_SELS:
            continue
        cat_sel_def[sel].add(uid)

# Selectors that Apple frameworks also implement / are generic: drop if defined in >2 omni categories
edges = collections.defaultdict(lambda: collections.defaultdict(set))  # a -> b -> reasons
for uid, u in units.items():
    for s in u["undef"]:
        for d in sym_def.get(s, ()):
            if d != uid:
                edges[uid][d].add(s)
    for sel in u["sels_used"]:
        if sel in ("didLoad", "performPosing", "load", "initialize"):
            continue  # invoked by OBPostLoader / runtime; modelled via ROOT/autorun
        ds = cat_sel_def.get(sel, ())
        if 0 < len(ds):
            for d in ds:
                if d != uid:
                    edges[uid][d].add("sel:" + sel)
    for s in u["strings"]:
        if s in cls_def and cls_def[s] != uid:
            edges[uid][cls_def[s]].add("str:" + s)
for uid, toks in TEXT_UNITS.items():
    for sym, ds in sym_def.items():
        if sym.lstrip("_") in toks:
            for d in ds:
                if d != uid: edges[uid][d].add("text:" + sym)
    for sel, ds in cat_sel_def.items():
        if sel.split(":")[0] in toks:
            for d in ds:
                if d != uid: edges[uid][d].add("textsel:" + sel)

# Roots: project units + classes/selectors named in project resources (nibs/plists)
CLS_RE = [r'customClass="(\w+)"', r'key="NSClassName">(\w+)<', r'<string>(\w+)</string>',
          r'"class" = "(\w+)"']
SEL_RE = [r'selector="([\w:]+)"', r'<string key="NSAction">([\w:]+)<', r'key="label">([\w:]+:)<']
def res_refs(txt):
    cl, se = set(), set()
    for r in CLS_RE: cl |= set(re.findall(r, txt))
    for r in SEL_RE: se |= set(re.findall(r, txt))
    return cl, se

def add_virtual(name, txt, why):
    cl, se = res_refs(txt)
    units[name] = dict(target="VIRTUAL", base=name, loc=0, files=[])
    for c in cl:
        if c in cls_def:
            edges[name][cls_def[c]].add(why + ":" + c)
    for sel in se:
        for d in cat_sel_def.get(sel, ()):
            edges[name][d].add(why + ":sel:" + sel)

proj_res = ""
for root, dirs, files in os.walk(os.path.join(REPO, "GraphSketcher")):
    if ("/iPad" in root) != (PLATFORM == "ios"):
        continue
    for f in files:
        if f.endswith((".xib", ".plist", ".storyboard")) or root.endswith(".nib"):
            proj_res += open(os.path.join(root, f), "rb").read().decode("utf-8", "ignore")
add_virtual("ROOT/project-resources", proj_res, "projres")
roots = {uid for uid, u in units.items() if u["target"] in PROJ} | {"ROOT/project-resources"}
nib_roots = set(edges["ROOT/project-resources"])

omni_res_edges = {}
for fw in OMNI:
    for path in glob.glob(FWDIR[fw] + "/**/*.xib", recursive=True) + glob.glob(FWDIR[fw] + "/**/*.nib", recursive=True):
        if os.path.isdir(path):
            txt = "".join(open(os.path.join(path, f), "rb").read().decode("utf-8", "ignore") for f in os.listdir(path))
        else:
            txt = open(path, "rb").read().decode("utf-8", "ignore")
        base = re.sub(r"\.(xib|nib)$", "", os.path.basename(path))
        vname = "NIB/" + fw + "/" + base
        add_virtual(vname, txt, "nib")
        omni_res_edges[os.path.relpath(path, REPO)] = sorted(edges[vname])
        for uid, u in list(units.items()):
            if u.get("strings") and base in u["strings"]:
                edges[uid][vname].add("loadsnib:" + base)
res_roots = set()
autorun_pat = re.compile(r"OBDidLoad|OBPerformPosing|\+\s*\(void\)\s*(didLoad|performPosing|load)\b|__attribute__\s*\(\(\s*constructor")
units["ROOT/autorun"] = dict(target="VIRTUAL", base="autorun", loc=0, files=[])
for uid, u in list(units.items()):
    if u["target"] in OMNI:
        for f in u["files"]:
            if autorun_pat.search(open(os.path.join(REPO, f), errors="ignore").read()):
                edges["ROOT/autorun"][uid].add("autorun")
# Categories overriding SDK-named methods: on Apple classes they're patches (root);
# on Omni classes they're live whenever the class is.
if SDK_FILTER:
    for uid, u in list(units.items()):
        if u["target"] not in OMNI: continue
        for cls, cat, sel in u.get("catmeths", ()):
            if sel in SDK_SELS and sel not in ("didLoad", "performPosing"):
                if cls in cls_def:
                    if cls_def[cls] != uid:
                        edges[cls_def[cls]][uid].add("catoverride:" + sel)
                else:
                    edges["ROOT/autorun"][uid].add("patch:%s(%s) %s" % (cls, cat, sel))
if os.environ.get("NO_AUTORUN"):
    del edges["ROOT/autorun"]
roots |= {"ROOT/autorun"}
all_roots = roots

def reach(start, banned=frozenset()):
    seen = set(); stack = [r for r in start if r not in banned]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        for m in edges.get(n, ()):
            if m not in seen and m not in banned:
                stack.append(m)
    return seen

R = reach(all_roots)
R_with_res = reach(all_roots | res_roots)

out = dict(
    units={uid: dict(target=u["target"], files=u["files"], loc=u["loc"]) for uid, u in units.items()},
    edges={a: {b: sorted(r) for b, r in bs.items()} for a, bs in edges.items()},
    roots=sorted(roots), nib_roots=sorted(nib_roots),
    omni_res_edges={k: sorted(v) for k, v in omni_res_edges.items()},
    reach=sorted(R), reach_with_res=sorted(R_with_res),
)
json.dump(out, open(os.path.join(S, os.environ.get("GRAPH", DEFAULT_GRAPH)), "w"), indent=1)

def loc(ns): return sum(units[n]["loc"] for n in ns if units[n]["target"] in OMNI)
omni_all = {u for u in units if units[u]["target"] in OMNI}
print("omni units", len(omni_all), "loc", loc(omni_all))
print("reachable omni (code+project nibs)", len(R & omni_all), loc(R & omni_all))
print("reachable omni (+ omni resource roots)", len(R_with_res & omni_all), loc(R_with_res & omni_all))
for fw in sorted(OMNI):
    a = {u for u in omni_all if u.startswith(fw + "/")}
    print(f"  {fw:16} total {len(a):4} {loc(a):6}  reach {len(a & R):4} {loc(a & R):6}  reach+res {len(a & R_with_res):4} {loc(a & R_with_res):6}")
print("nib roots:", sorted(nib_roots))
print("omni resource roots:", {k: v for k, v in out["omni_res_edges"].items()})
