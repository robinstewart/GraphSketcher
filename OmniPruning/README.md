# OmniPruning

Tools and notes for shrinking `OmniGroup/Frameworks`.

- [OMNIGROUP_PRUNING.md](OMNIGROUP_PRUNING.md): the list of opportunities and their status.
- The scripts here build a dependency graph from compiled object files and work out which Omni source files the Mac and iPad apps can actually reach.

Everything the scripts generate goes into `work/`, which git ignores (build output there is several hundred MB).

## Running the analysis

Run from the repository root. Each step reads what the earlier ones wrote.

```sh
W="$PWD/OmniPruning/work"; mkdir -p "$W"

# 1. Build both apps (Debug, arm64) so there are object files to read.
xcodebuild -workspace GraphSketcher-Mac.xcworkspace -scheme ALL -configuration Debug \
  -derivedDataPath "$W/DD" ARCHS=arm64 ONLY_ACTIVE_ARCH=NO MACOSX_DEPLOYMENT_TARGET=12.0 \
  GCC_TREAT_WARNINGS_AS_ERRORS=NO CODE_SIGN_IDENTITY=- CODE_SIGN_STYLE=Manual \
  DEVELOPMENT_TEAM= PROVISIONING_PROFILE_SPECIFIER= COMPILER_INDEX_STORE_ENABLE=NO build
xcodebuild -workspace GraphSketcher-iPad.xcworkspace -scheme GraphSketcher-iPad -configuration Debug \
  -sdk iphonesimulator -derivedDataPath "$W/DDiOS" -IDEBuildingContinueBuildingAfterErrors=YES \
  ARCHS=arm64 ONLY_ACTIVE_ARCH=NO IPHONEOS_DEPLOYMENT_TARGET=15.0 GCC_TREAT_WARNINGS_AS_ERRORS=NO \
  CODE_SIGNING_ALLOWED=NO COMPILER_INDEX_STORE_ENABLE=NO build

# 2. Gather inputs.
python3 OmniPruning/sdk_selectors.py     # selector names declared by the Apple SDKs
python3 OmniPruning/targets.py           # which target builds which file

# 3. Build the graphs.
python3 OmniPruning/depgraph.py                  # Mac  -> work/graph.json
PLATFORM=ios python3 OmniPruning/depgraph.py     # iPad -> work/graph_ios.json
```

Delete `work/DD` and `work/DDiOS` before rebuilding after source files have been removed. Stale object files and stale copied headers would otherwise hide problems.

The iPad build does not finish. Two files fail to compile with current Xcode (`OUIAppController.m`, `GraphViewController.m`) and two resource steps fail. `depgraph.py` models the two source files from their text instead, counting every identifier in them as a possible use.

## Scripts

| Script | What it does |
|---|---|
| `depgraph.py` | Reads every `.o` with `nm`/`otool` and writes the graph: one node per source file, one edge per symbol, class or category selector it uses. |
| `analyze.py dom\|unreach\|reach` | Dominator subtrees (what one reference holds up), or the unreachable / reachable file lists. |
| `cut.py FILE…` | Simulates removing all references to the given files and lists what else becomes unreachable. |
| `pairs.py` | Looks for pairs of files that together hold up a large subtree. |
| `why.py GRAPH FILE…` | Lists what references a file. |
| `headers.py`, `group.py` | For unreachable files: who still imports their headers, and a per-folder summary. |
| `autoonly.py`, `autocheck.py` | Files that are reachable only through a load-time hook (`+didLoad`, `+performPosing`, constructors). |
| `plan_deletion.py` | Decides which files can go with `#import` removals only, checking both the Mac and iPad graphs. Writes `work/delete_list.json`. |
| `apply_deletion.py [--dry-run]` | Deletes those files, their Xcode project entries and the `#import` lines. |
| `resources.py` | Lists every non-source file under `OmniGroup/Frameworks` and which source, nib or plist mentions its name. Writes `work/resources.json`. |
| `resources_dynamic.py` | For the unmentioned ones, flags names that a format string or string fragment in the code could build at run time. Writes `work/resource_candidates.json`; review the flags by hand. |
| `apply_deletion.py --resources [--dry-run]` | Deletes the files in `work/resource_delete_list.json` and their Xcode project entries. |

Two hand-maintained inputs:

- `uncompiled_sources.txt`: source files that are in no build phase and that nothing `#include`s.
- `keep_by_hand.json`: files the graphs call unused but that must stay, for reasons object files can't show (a protocol or macro used from the header, a build script that expects a strings table).
