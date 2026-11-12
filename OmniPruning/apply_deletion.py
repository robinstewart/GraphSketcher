#!/usr/bin/env python3
"""Apply work/delete_list.json: remove each file from disk, from every .xcodeproj that
references it, and delete the #import lines listed in work/import_hits.json.
Run plan_deletion.py first. Pass --dry-run to only print what would happen.
With --resources, apply work/resource_delete_list.json instead (no #import edits)."""
import json, os, re, subprocess, glob, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); W = os.path.join(HERE, "work"); REPO = os.path.dirname(HERE)
DRY = "--dry-run" in sys.argv
RES = "--resources" in sys.argv
delete = set(json.load(open(os.path.join(W, "resource_delete_list.json" if RES else "delete_list.json"))))
hits = [] if RES else json.load(open(os.path.join(W, "import_hits.json")))

# 1. project files
for proj in sorted(set(glob.glob(REPO + "/OmniGroup/**/*.xcodeproj", recursive=True) + glob.glob(REPO + "/GraphSketcher/**/*.xcodeproj", recursive=True))):
    pb = os.path.join(proj, "project.pbxproj")
    objs = json.loads(subprocess.run(["plutil", "-convert", "json", "-o", "-", pb], capture_output=True, text=True).stdout)["objects"]
    projdir = os.path.dirname(proj); parent = {}
    for oid, o in objs.items():
        for c in o.get("children", []): parent[c] = oid
    def path_of(fid):
        o = objs[fid]; p = o.get("path", ""); st = o.get("sourceTree", "<group>")
        if st == "<group>" and fid in parent:
            base = path_of(parent[fid]); return os.path.normpath(os.path.join(base, p)) if p else base
        if st in ("SOURCE_ROOT", "<group>"): return os.path.normpath(os.path.join(projdir, p))
        return "$" + st + "/" + p
    ids = set()
    for oid, o in objs.items():
        if o.get("isa") == "PBXFileReference":
            fp = path_of(oid)
            if not fp.startswith("$") and os.path.relpath(fp, REPO) in delete: ids.add(oid)
    # a localized-resource group whose every variant is deleted goes too
    ids |= {oid for oid, o in objs.items() if o.get("isa") == "PBXVariantGroup" and o["children"] and set(o["children"]) <= ids}
    ids |= {oid for oid, o in objs.items() if o.get("isa") == "PBXBuildFile" and o.get("fileRef") in ids}
    if not ids: continue
    out, removed, skipping = [], 0, False
    for line in open(pb, encoding="utf-8"):
        if skipping:
            removed += 1; skipping = line.rstrip() != "\t\t};"; continue
        m = re.match(r"\s*([0-9A-F]{24})\b", line)
        if m and m.group(1) in ids:
            removed += 1
            if line.rstrip().endswith("= {"):
                assert objs[m.group(1)]["isa"] == "PBXVariantGroup", line
                skipping = True
            else:
                assert line.rstrip().endswith(("};", ",")), "multi-line pbxproj entry: " + line
            continue
        out.append(line)
    print(f"{os.path.relpath(proj, REPO)}: {len(ids)} objects, {removed} lines removed")
    if not DRY: open(pb, "w", encoding="utf-8").write("".join(out))

# 2. #import lines
byfile = {}
for r, i, text in hits: byfile.setdefault(r, {})[i] = text
for r, lines_ in sorted(byfile.items()):
    p = os.path.join(REPO, r); src = open(p, encoding="utf-8", errors="surrogateescape").read().split("\n")
    for i, text in lines_.items():
        assert src[i - 1].strip() == text, (r, i, src[i - 1], text)
    keep = [l for n, l in enumerate(src, 1) if n not in lines_]
    if not DRY: open(p, "w", encoding="utf-8", errors="surrogateescape").write("\n".join(keep))
print(f"{len(hits)} #import lines removed from {len(byfile)} files")

# 3. files
for f in sorted(delete):
    p = os.path.join(REPO, f)
    if not DRY: shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
print(f"{len(delete)} files deleted")
