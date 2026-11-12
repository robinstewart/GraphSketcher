#!/usr/bin/env python3
"""Parse every .xcodeproj and write targets.json: {project: {target: {"sources": [...], "headers": [...], "resources": [...]}}}
with repo-relative paths. Used to tell which targets (Mac or iOS) build a given file."""
import json, os, subprocess, glob, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work", "targets.json")
res = {}
projs = glob.glob(REPO + "/OmniGroup/**/*.xcodeproj", recursive=True) + glob.glob(REPO + "/GraphSketcher/**/*.xcodeproj", recursive=True) + glob.glob(REPO + "/LinkBack/**/*.xcodeproj", recursive=True)
for proj in sorted(set(projs)):
    pb = os.path.join(proj, "project.pbxproj")
    d = json.loads(subprocess.run(["plutil", "-convert", "json", "-o", "-", pb], capture_output=True, text=True).stdout)
    objs = d["objects"]; projdir = os.path.dirname(proj)
    parent = {}
    for oid, o in objs.items():
        for c in o.get("children", []): parent[c] = oid
    def path_of(fid):
        o = objs[fid]; p = o.get("path", ""); st = o.get("sourceTree", "<group>")
        if st == "<group>" and fid in parent:
            base = path_of(parent[fid])
            return os.path.normpath(os.path.join(base, p)) if p else base
        if st == "SOURCE_ROOT" or st == "<group>": return os.path.normpath(os.path.join(projdir, p))
        return "$" + st + "/" + p
    pr = res[os.path.relpath(proj, REPO)] = {}
    for oid, o in objs.items():
        if o.get("isa") not in ("PBXNativeTarget", "PBXAggregateTarget"): continue
        t = pr[o["name"]] = {"sources": [], "headers": [], "resources": []}
        for ph in o.get("buildPhases", []):
            p = objs[ph]; kind = {"PBXSourcesBuildPhase": "sources", "PBXHeadersBuildPhase": "headers", "PBXResourcesBuildPhase": "resources"}.get(p["isa"])
            if not kind: continue
            for bf in p.get("files", []):
                ref = objs[bf].get("fileRef")
                if ref and ref in objs:
                    fp = path_of(ref)
                    t[kind].append(os.path.relpath(fp, REPO) if not fp.startswith("$") else fp)
json.dump(res, open(OUT, "w"), indent=1)
for p, ts in res.items():
    for t, v in ts.items(): print(f"{p} :: {t}: {len(v['sources'])} sources, {len(v['headers'])} headers, {len(v['resources'])} resources")
