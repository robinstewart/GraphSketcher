#!/usr/bin/env python3
"""List resource files under OmniGroup/Frameworks and who refers to them.
A resource is a deletion candidate when its name (minus extension, @2x, ~ipad)
appears in no remaining source, nib, plist or other text file in the repo
(project files' own file-list entries excluded). Writes work/resources.json."""
import os, re, json, collections, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FW = os.path.join(REPO, "OmniGroup/Frameworks")
SRC_EXT = (".m", ".h", ".c", ".mm", ".pch")
TEXT_EXT = SRC_EXT + (".xib", ".storyboard", ".plist", ".defaults", ".sdef", ".scriptSuite",
            ".scriptTerminology", ".strings", ".xcconfig", ".keycommands", ".html", ".sh", ".rb", ".ofunits", ".cikernel")
SKIP_DIRS = {".git", "work", "build", "DerivedData"}
def read(p):
    b = open(p, "rb").read()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"): return b.decode("utf-16", "ignore")
    if b[:6] == b"bplist":
        return subprocess.run(["plutil", "-convert", "xml1", "-o", "-", p], capture_output=True, text=True).stdout
    return b.decode("utf-8", "ignore")
texts = {}      # relpath -> text  (everything that can mention a resource)
resources = []  # relpaths under Frameworks
pbx = {}
for root, dirs, files in os.walk(REPO):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith("OmniPruning")]
    if root.endswith(".nib"):
        # a nib bundle is one resource
        rel = os.path.relpath(root, REPO)
        texts[rel] = "".join(read(os.path.join(root, f)) for f in files)
        if root.startswith(FW): resources.append(rel)
        dirs[:] = []; continue
    for f in files:
        p = os.path.join(root, f); rel = os.path.relpath(p, REPO)
        if f == ".DS_Store": continue
        if f == "project.pbxproj": pbx[rel] = read(p); continue
        if f.endswith(TEXT_EXT) or os.access(p, os.X_OK) and os.path.getsize(p) < 200000 and "." not in f:
            texts[rel] = read(p)
        if root.startswith(FW) and not f.endswith(SRC_EXT) and ".xcodeproj" not in root:
            resources.append(rel)
def key(rel):
    b = os.path.basename(rel)
    b = re.sub(r"\.[^.]+$", "", b)
    b = re.sub(r"(@2x|~ipad|~iphone)+$", "", b)
    return b
# pbxproj: which targets bundle the file; plus any mention outside file-list lines (e.g. shell scripts)
def pbx_info(rel):
    name = os.path.basename(rel); targets = set(); other = []
    for pp, txt in pbx.items():
        for line in txt.splitlines():
            if name in line or (key(rel) in line and "shellScript" in line):
                if " in Resources */" in line or " in CopyFiles */" in line or " in Copy " in line: targets.add(pp.split("/")[-2].replace(".xcodeproj", ""))
                elif "shellScript" in line or "INFOPLIST" in line or "ORDER_FILE" in line or "PREFIX" in line: other.append(pp)
    return sorted(targets), sorted(set(other))
out = []
for rel in sorted(resources):
    k = key(rel)
    lproj = re.search(r"/(\w+)\.lproj/", rel)
    users = sorted(t for t, txt in texts.items() if t != rel and k in txt
                   and not (key(t) == k and os.path.dirname(os.path.dirname(t)) == os.path.dirname(os.path.dirname(rel)) and ".lproj" in t and ".lproj" in rel))
    tg, oth = pbx_info(rel)
    out.append(dict(file=rel, key=k, users=users, bundled_by=tg, pbx_other=oth))
os.makedirs(os.path.join(HERE, "work"), exist_ok=True)
json.dump(out, open(os.path.join(HERE, "work/resources.json"), "w"), indent=1)
cand = [r for r in out if not r["users"] and not r["pbx_other"]]
print(len(out), "resources;", len(cand), "with no reference")
for r in cand: print("  ", r["file"], "| bundled:", ",".join(r["bundled_by"]) or "-")
