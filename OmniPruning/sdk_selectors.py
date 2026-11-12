#!/usr/bin/env python3
"""Write work/sdk_selectors.txt (macOS) and work/sdk_selectors_ios.txt: every selector name the
Apple SDK headers declare. depgraph.py uses these so that a call to, say, -isEqual: does not
count as a use of an Omni category that happens to define a method with the same name."""
import os, re, subprocess
WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
FWS = ["Foundation", "AppKit", "UIKit", "CoreData", "QuartzCore", "CoreImage", "WebKit", "Quartz", "CoreText",
       "CoreGraphics", "ApplicationServices", "Cocoa", "ImageIO", "QuickLook", "CoreServices", "MobileCoreServices",
       "StoreKit", "MessageUI", "Security", "CFNetwork", "SystemConfiguration"]
for sdkname, out in (("macosx", "sdk_selectors.txt"), ("iphonesimulator", "sdk_selectors_ios.txt")):
    sdk = subprocess.run(["xcrun", "--sdk", sdkname, "--show-sdk-path"], capture_output=True, text=True).stdout.strip()
    sels = set()
    for fw in FWS:
        for root, d, files in os.walk(os.path.join(sdk, "System/Library/Frameworks", fw + ".framework")):
            for f in files:
                if not f.endswith(".h"): continue
                t = open(os.path.join(root, f), errors="ignore").read()
                t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
                for m in re.finditer(r"^\s*[-+]\s*\([^;{]*?\)\s*([^;{]+?)(?:\s+(?:NS_|API_|__|UI_)[A-Z_]+.*)?;", t, re.M):
                    decl = m.group(1); parts = re.findall(r"(\w+)\s*:", decl)
                    if parts: sels.add("".join(p + ":" for p in parts))
                    else:
                        w = re.match(r"(\w+)", decl.strip())
                        if w: sels.add(w.group(1))
                for m in re.finditer(r"@property\s*(?:\(([^)]*)\))?[^;]*?(\w+)\s*(?:(?:NS|UI)_\w+(?:\([^)]*\))?\s*|API_\w+\([^)]*\)\s*)*;", t):
                    attrs = m.group(1) or ""; name = m.group(2)
                    g = re.search(r"getter\s*=\s*(\w+)", attrs); sels.add(g.group(1) if g else name)
                    if "readonly" not in attrs:
                        s = re.search(r"setter\s*=\s*(\w+:)", attrs)
                        sels.add(s.group(1) if s else "set" + name[0].upper() + name[1:] + ":")
    open(os.path.join(WORK, out), "w").write("\n".join(sorted(sels)))
    print(out, len(sels))
