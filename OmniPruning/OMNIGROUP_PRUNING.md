# Pruning the OmniGroup frameworks

Opportunities to delete large parts of `OmniGroup/Frameworks` with little or no refactoring.
Every item here needs **less than ~100 changed lines**. Items 0 and 1 have been carried out; the rest is still a plan.

Scope: the estimates below are for the **Mac app** (the `GraphSketcher-Mac` workspace: app, model framework, QuickLook and Spotlight plugins). Items 2 to 13 have not been checked against the iPad app yet.

Analysis date: 2026-11-11, against commit `ac60c96`.

## Status

**Items 0 and 1 are done** (2026-11-11): 241 files and about 40,900 lines deleted, with no code changes beyond removing 108 `#import` lines (3 of them in the project) and the files' Xcode project entries. The six Mac frameworks went from about 128,000 lines to about 87,000.

The deletion was checked against the iPad app as well as the Mac app. That made it smaller than the estimates in the table below, which were Mac-only:

- **Kept for the iPad app (15 source/header pairs).** The iPad graph reaches them, mostly through sync and document-store code: `OFSyncClient`, `OFNetReachability`, `OFNetStateNotifier`, `OFNetStateRegistration`, `OFBinding`, `OFBindingPoint`, `OFMultiValueDictionary`, `OFCredentials`, `OFBackgroundActivity`, `NSFileCoordinator-OFExtensions`, `NSFileWrapper-OAExtensions`, `NSData-OFCompression`, `CFData-OFCompression`, `CFData-OFFileIO`, `CFDictionary-OFExtensions`. `OFSimpleLock` also stays because an iOS target lists its header.
- **Kept because removing them needs more than an `#import` deletion.**
  - `OFRelativeDateParser`, `OFRelativeDateParser-Internal`, `OFRelativeDateFormatter`: a build script expects the `OFDateProcessing` strings table they generate.
  - `OAWindowCascade`: `OIInspectorRegistry` adopts its data-source protocol.
  - `OBExpectedDeallocation`: `OSStyleContext.m` calls `OBExpectDeallocation()`.
  - `OFLockFile`: referenced inside an `#if` in `OFXAccountAgent.m`.
  - `OFTransientObjectsTracker`: its macro gates an `#if` in `NSView-OAExtensions.h`.
- **Headers kept for their inline functions or types:** `CFDictionary-OFExtensions.h`, `OFDataBuffer.h`, `OATextAttachment.h`.

Verified after the deletion:

- The Mac workspace builds clean from an empty build folder, and the app launches without mentioning any deleted class in its log.
- The iPad workspace fails in exactly the same four steps as before the deletion (two source files that don't compile with current Xcode, two resource steps). Sixteen fewer files compile, and no remaining object file refers to a symbol or category method that was deleted.

Not done: a hands-on smoke test of the Mac app (see the end of this file), and resource files that belonged to deleted classes, such as `OAFindPanel.xib` and `OAPopupDatePicker.nib`, are still in place.

The scripts that produced all of this are in this folder; see [README.md](README.md).

## Summary

The six Omni frameworks the Mac app builds (OmniAppKit, OmniBase, OmniFoundation, OmniInspector, OmniQuartz, OmniUnzip) contain about **128,000 lines** of `.h/.m/.c`. Doing everything below would remove about **74,500 lines in ~445 files** (roughly 58%).

"Project lines" means lines changed under `GraphSketcher/`. "Omni edits" means lines changed in Omni files that stay. Deleting `#import` lines from umbrella headers and removing files from the framework `.xcodeproj` is mechanical and not counted as refactoring unless noted.

| # | Opportunity | Project lines | Omni edits | Omni deletable (files / lines) |
|---|---|---:|---:|---:|
| 0 | Source files that no target compiles (**done**) | 0 | 0 | 40 / ~9,640 |
| 1 | Compiled code that nothing references (**done**, less the iPad keeps above) | 4 (`#import`s) | ~127 `#import`s | 243 / ~40,050 |
| 2 | Code reached only through load-time patches | 0 | ~27 `#import`s | 62 / ~10,740 |
| 3 | Preferences window (the app has none) | 0 | ~8 | 15 / 2,346 |
| 4 | `OFScheduler` | 0 | ~6 | 8 / 980 |
| 5 | `OFBundleRegistry` → `registerDefaults:` | ~20 | ~3 | 10 / 1,036 (+2 / 487 with #3) |
| 6 | AppleScript toolbar items (`OAScriptToolbarHelper`) | 1 | ~5 | 4 / 642 |
| 7 | `OFMessageQueue` / `OFInvocation` → GCD (needs #4) | 0 | ~55 | 30 / 2,218 |
| 8 | `OAController` → `OFController` | ~45 | 0 | 11 / 1,628 |
| 9 | `OQDrawing` rounded rects (needs #2) | ~30 | ~1 | 3 / 592 |
| 10 | `NSUndoManager-OFExtensions` | 3 | 0 | 2 / 549 |
| 11 | `NSColor-OAExtensions` + `OAColorProfile` | ~6 | ~5 | 4 / 2,112 |
| 12 | Known-key dictionaries → `NSMutableDictionary` | ~45 | 0 | 4 / 568 |
| 13 | `OAToolbarWindowController` → plain `NSToolbar` delegate (includes #6) | ~80–100 | 0 | 8 / 965 beyond #6 |

Suggested order: 0, 1 and 2 first (no logic changes), then 4, 3, 10, 6, 5, 11, 9, 8, 7, 12, 13.

## How these numbers were found

1. Built the Mac workspace (Debug, arm64) and read every object file with `nm` and `otool`. Each compiled file became a node. Each reference became an edge: a class, function or global symbol it uses, or any selector it sends or names that an Omni category defines.
2. Started from the app, the model framework, both plugins, the classes and actions named in the app's xibs and plists, and Omni nibs loaded by name. Then found everything reachable.
3. Files with `+didLoad`, `+performPosing` or `__attribute__((constructor))` run without being referenced. They were kept in a separate tier (#2) and reviewed one by one.
4. Selector names that the macOS SDK also declares (`isEqual:`, `undoManager`, `title` and so on) were not counted as uses of an Omni category. Otherwise almost everything would look used.
5. For each candidate, simulated deleting the references to a file and listed what else stops being reachable. Dominator trees and pair searches found the cases where one or two references hold up a large subtree.
6. Inline functions and macros don't show up in object files, so every header of a deletable file was checked for live importers.

The graph errs toward keeping code. Protocol and ivar names count as selector uses, so a few files look live when they aren't. Blind spots remain, though: selectors built at runtime with `NSSelectorFromString`, KVC key paths and category methods whose names collide with SDK methods. Treat each item as a strong lead and verify it with a build plus the smoke test at the end.

---

## 0. Source files that no target compiles

**Project lines:** 0 · **Omni edits:** 0 · **Delete:** 40 files, ~9,640 lines

These files are on disk but in no build phase, and nothing `#include`s them. (`SFMT/SFMT.c` looks similar but stays: [OFRandom.m](../OmniGroup/Frameworks/OmniFoundation/DataStructures.subproj/OFRandom.m) includes it directly.)

- OmniAppKit/Widgets.subproj: `OAMultiColumnListView`, `OATypeAheadSelectionHelper`, `OAXTableView` (.h/.m)
- OmniBase: `OBPatchTrap.m`
- OmniFoundation: `OFUnit`, `OFUnits`, `OFDimensionedValue`, `OFClobberDetectionZone`, `OFTransformStream`, the whole `LZMA/` folder (11 files), `encode85.c`, `decode85.c`, `SFMT/test.c`
- OmniQuartz: `OQDrawing-Arcs.m`, `OQDrawing-Hatching.m`
- OmniUnzip/unzip: `minizip.c`, `miniunz.c`, `mztools.[ch]`, `iowin32.[ch]` (minizip's command-line tools)

`OFCredentials-iOS.m` is also not built for the Mac, but an iOS target lists it, so it's excluded here.

## 1. Compiled code that nothing references

**Project lines:** 4 `#import` lines · **Omni edits:** ~127 `#import` lines, 94 of them in the umbrella headers (`OmniAppKit.h`, `OmniFoundation.h`, `OmniQuartz.h`) · **Delete:** 243 files, ~40,050 lines

These files are built into the frameworks, but nothing reachable from the app uses them. None has a load-time hook.

| Folder | Files | Lines | Contents |
|---|---:|---:|---|
| OmniAppKit/Widgets.subproj | 60 | 10,128 | `OACalendarView`, `OASwoopView`, `OAScrollView`, `OAPopupDatePicker`, `OAHierarchicalPopUpController`, `OAStackView`, `OASearchField`, mouse tips, tab views, `OAWindowCascade`*, `OAAquaButton`*, and more |
| OmniFoundation (top level) | 36 | 9,212 | XML signatures / CDSA crypto, HTTP state machine, net reachability and net-state notifier, relative date parser, sync client, bindings |
| OmniFoundation/DataStructures.subproj | 30 | 6,014 | B-tree, trie (5 classes), bijection, multi-value dictionary, rational numbers, `OFDataBuffer`*, `OFTransientObjectsTracker`* |
| OmniFoundation/XML | 5 | 4,548 | `OFXMLReader`*, `OFXMLSignature` |
| OmniAppKit (top level) | 14 | 1,804 | `OAFindController`, `OAFontCache`, `OADragController`, `OAColorPalette`, `OATrackingLoop`* |
| OmniFoundation/Formatters.subproj | 6 | 1,609 | time-span formatter, date-format conversion |
| OmniAppKit/OpenStepExtensions.subproj | 32 | 1,291 | 16 small AppKit categories |
| OmniFoundation/OpenStepExtensions.subproj | 16 | 1,127 | 8 small Foundation categories |
| OmniFoundation/CoreFoundationExtensions | 6 | 977 | CFData compression and file I/O, `CFDictionary-OFExtensions`* |
| OmniQuartz | 10 | 909 | `CALayer` animation helpers, `OQGradient` |
| Other (lock file, credentials, locks, ColorSync leftovers, AppleScript commands, `OBExpectedDeallocation`, `OUZipRawFileMember`) | 31 | 3,035 | |

The folder rows add up to 246 files and 40,654 lines. They include three headers that must stay (603 lines; see the note below), which is why the deletable total is 243 files and ~40,050 lines.

\* A live file `#import`s this header. Delete the `#import` line; nothing from the header is used. Three headers must stay because live code uses their inline functions or types: `CFDictionary-OFExtensions.h` (inline helpers used by [OSStyle.m](../GraphSketcher/OmniStyle/Basic/OSStyle.m)), `OFDataBuffer.h` (used heavily by `NSData-OFEncoding.m`), and `OATextAttachment.h` (used in `NSAttributedString-OAExtensions.h`). The totals above already exclude them. `NSView-OAExtensions.h` has an `#if OF_TRANSIENT_OBJECTS_TRACKER_ENABLED` block to delete along with `OFTransientObjectsTracker`.

The four project `#import`s to delete:
- `OFXMLReader.h` in [OSStyledTextStorage-XML.m](../GraphSketcher/OmniStyle/Text/OSStyledTextStorage-XML.m)
- `OFAddScriptCommand.h` in [OSStyle.h](../GraphSketcher/OmniStyle/Basic/OSStyle.h)
- `NSFontManager-OAExtensions.h` in [OSStyle-AttributeExtensions.m](../GraphSketcher/OmniStyle/Basic/OSStyle-AttributeExtensions.m)
- `CFDictionary-OFExtensions.h` in [OSStyle.m](../GraphSketcher/OmniStyle/Basic/OSStyle.m), but only if that header is deleted. It stays, per the note above.

## 2. Code reached only through load-time patches

**Project lines:** 0 · **Omni edits:** ~27 `#import` lines · **Delete:** 62 files, ~10,740 lines

These files are only "used" because their `+didLoad` or `+performPosing` runs at launch, or because they override an AppKit method. Each hook was reviewed; none matters to GraphSketcher. This tier needs a behavior check, not just a build.

**2a. AppleScript and find support: 28 files, 3,016 lines.** The app sets `NSAppleScriptEnabled = NO` and has no `.sdef`, so these fixes never run. Files: `NSSetCommand-OFFixes`, `NSObjectSpecifier-OFFixes`, `NSScripting-OFDebugging`, `NSScriptSuiteRegistry-OFExtensions`, `NSScriptCommand-OFExtensions`, `NSScriptObjectSpecifier-OFExtensions`, `OFSubjectTargettingScriptCommand`, `NSObject-OFAppleScriptExtensions`, `NSScriptCommand-OAExtensions`, `NSApplication-OAExtensions`, `NSAppleEventManager-OAExtensions`, `NSTextStorage-OAExtensions`, `NSText-OAExtensions`, `OAFindPattern`, `OARegExFindPattern`. The find-pattern classes were only used by `OAFindController`, which #1 removes.

**2b. Fixes for old macOS versions and debug checks: 16 files, 2,291 lines.**
- `NSClipView-OAUpdateConstraintsFix`: only active before 10.9; the app targets macOS 12.
- `NSView-OALayerBackedFix`: only installs an assertion about a private class.
- `NSBundle-OFFixes`, `NSConditionLock-OFFixes`: workarounds for old OS bugs.
- `NSDocument-OAExtensions` (pulls in `NSWindowController-OAExtensions`), `NSDocumentController-OAExtensions`: launch-time checks for deprecated API use.
- `NSSplitView-OAExtensions`: an assertion only.
- `CALayer-OQExtensions`: its constructors only patch anything when animation-logging macros are defined.

**2c. AppKit overrides the app doesn't need: 10 files, 4,618 lines.**
- `NSBezierPath-OAExtensions` (3,690 lines): overrides `-[NSBezierPath isEqual:]` and `-hash`. Before deleting, confirm no code keeps bezier paths in sets or dictionaries or compares them.
- `NSColor-ColorSyncExtensions`: patches `-[NSColor set]`. It has no effect unless an `OAColorProfile` is active, and the app never activates one.
- `NSTableView-OAColumnConfigurationExtensions`: supports `OAConfigurableColumnTableView`, which #1 removes.
- `NSPopUpButton-OAExtensions`, `NSToolbarItem-OAExtensions`: the app's `itemWithTag:` calls are on `NSMenu`, and `NSToolbarItem.title` is now built in.

**2d. Unused categories that only looked used because of a name collision: 8 files, 814 lines.** `NSAttributedString-OFExtensions`, `NSData-OFExtensions`, `OFGeometry`, `CIColor-OQExtensions`.

**Keep:**
- `OAControlTextColorTransformer`: the inspector xibs bind through it (44 bindings).
- `OIFontInspector`: its patch lets the Fonts command toggle the font panel open and closed.
- `OFBundleRegistry`: it registers the app's default settings. See #5.

## 3. Preferences window

**Project lines:** 0 · **Omni edits:** ~8 · **Delete:** 15 files (12 source files, 2,346 lines, plus `OAPreferences.xib` and 2 PNGs)

GraphSketcher has no Preferences menu item and registers no preference clients. The only path to `OAPreferenceController` is `-showPreferencesPanel:` in [OAApplication.m:957](../OmniGroup/Frameworks/OmniAppKit/OAApplication.m#L957).

- Delete that method and the `#import "OAPreferenceController.h"` at [OAApplication.m:27](../OmniGroup/Frameworks/OmniAppKit/OAApplication.m#L27).
- Delete its declaration in `OAApplication.h` and the 3 preference imports in `OmniAppKit.h`.
- Delete the whole `OmniAppKit/Preferences.subproj/`.

Together with #5, `OFBundledClass` (2 files, 487 lines) also becomes unreachable.

## 4. OFScheduler

**Project lines:** 0 · **Omni edits:** ~6 · **Delete:** 8 files, 980 lines

The only live reference is one line that wakes the scheduler, at [OAApplication.m:329](../OmniGroup/Frameworks/OmniAppKit/OAApplication.m#L329). `OATypeAheadSelectionHelper` also uses it, but no target compiles that file (#0).

- Delete that line, 3 imports in `OmniFoundation.h` and 2 in [OmniFoundation_Prefix.h](../OmniGroup/Frameworks/OmniFoundation/OmniFoundation_Prefix.h).
- Delete `OFScheduler`, `OFScheduledEvent`, `OFChildScheduler` and `OFDedicatedThreadScheduler` from `Scheduling.subproj`.

## 5. OFBundleRegistry → registerDefaults:

**Project lines:** ~20 · **Omni edits:** ~3 · **Delete:** 10 files, 1,036 lines (`OFBundleRegistry`, `CFPropertyList-OFExtensions`, `NSUserDefaults-OFExtensions`, `NSException-OFExtensions`, `NSMutableSet-OFExtensions`). Adds `OFBundledClass` (487 lines) if #3 is also done.

At launch, `OFBundleRegistry` reads `OFRegistrations → NSUserDefaults → defaultsDictionary` from the Info.plists of the app, OmniAppKit and OmniFoundation, and registers those defaults. No other registration types are used.

- Replace it with a loop in [main.m](../GraphSketcher/App/main.m), before `NSApplicationMain`, over `NSBundle.mainBundle` and `NSBundle.allFrameworks` that calls `-[NSUserDefaults registerDefaults:]`.
- It must run before anything reads a default, which `main()` guarantees.

## 6. AppleScript toolbar items

**Project lines:** 1 · **Omni edits:** ~5 · **Delete:** 4 files, 642 lines (`OAScriptToolbarHelper`, `NSFileManager-OAExtensions`)

`OAToolbarWindowController`'s `+initialize` registers `OAScriptToolbarHelper` (3 lines plus an import, in [OAToolbarWindowController.m](../OmniGroup/Frameworks/OmniAppKit/OAToolbarWindowController.m)). Also delete `"OSAScriptTemplate"` from the allowed items in [Graph.toolbar](../GraphSketcher/App/Graph.toolbar).

Feature loss: users can no longer drag their own AppleScripts into the toolbar from the Customize sheet.

## 7. OFMessageQueue and OFInvocation → GCD

**Requires #4.** **Project lines:** 0 · **Omni edits:** ~55 · **Delete:** 30 files, 2,218 lines (`OFMessageQueue`, `OFQueueProcessor`, `OFRunLoopQueueProcessor`, `OFInvocation`, `OFConcreteInvocation`, the nine `OFIObject*` classes, `OAAppKitQueueProcessor`)

Live code uses only four methods from [OFObject-Queue](../OmniGroup/Frameworks/OmniFoundation/Scheduling.subproj/OFObject-Queue.m): `queueSelector:`, `queueSelectorOnce:`, `queueSelectorOnce:withObject:` and `queueSelector:withInt:withInt:`. The callers are `OIInspectorRegistry`, `OIInspectorController`, `NSView-OAExtensions` and `NSWindow-OAExtensions`.

- Rewrite those four on `dispatch_async(dispatch_get_main_queue(), …)`. For the "Once" variants, keep a set of pending object/selector pairs. That's about 40 lines and replaces the 185-line file.
- In [OFController.m](../OmniGroup/Frameworks/OmniFoundation/OFController.m), `queueSelector:forObject:whenStatus:` stores `OFInvocation`s (lines 272 and 722). Store blocks instead, about 10 lines.
- Delete the one `OFMessageQueue` use in `NSThread-OFExtensions`, or delete the whole file if #3 and #5 are done.

Risk: timing. OFMessageQueue ran on the main run loop in its own modes. Check that inspector updates still happen promptly while dragging and during menu tracking.

## 8. OAController → OFController

**Project lines:** ~45, plus 1 xib edit · **Omni edits:** 0 · **Delete:** 11 files, 1,628 lines (`OAController`, `OAAboutPanelController`, `NSLayoutManager-OAExtensions`, `OAInternetConfig`, `NSString-OFURLEncoding`, `OAAboutPanel.xib`)

`AppController` subclasses `OAController`. The app uses only four things from it: forwarding app-delegate events to `OFController`, `checkMessageOfTheDay`, `showMessageOfTheDay:` and `showAboutPanel:`.

- Make [AppController](../GraphSketcher/App/AppController.m) subclass `OFController` directly.
- Copy in the four delegate forwards: `applicationWillFinishLaunching:` → `didInitialize`, `applicationDidFinishLaunching:` → `startedRunning`, `applicationShouldTerminate:`, `applicationWillTerminate:`. Also copy `gotPostponedTerminateResult:`. About 25 lines.
- Copy in the message-of-the-day methods. They still use `OAWebPageViewer`, which `OAApplication`'s Help also uses. About 20 lines.
- Point the About menu item in [MainMenu.xib](../GraphSketcher/App/English.lproj/MainMenu.xib) at `orderFrontStandardAboutPanel:`.
- Trim the `sendFeedback:` and `showAboutPanel:` checks in `validateMenuItem:`.

Behavior change: the standard macOS About panel replaces Omni's. It still shows `Credits.rtf` if one is present.

## 9. OQDrawing rounded rects

**Requires #2 (`CALayer-OQExtensions`).** **Project lines:** ~30 · **Omni edits:** ~1 · **Delete:** 3 files, 592 lines (`OQDrawing.h`, `OQDrawing.m`, `OFExtent.m`)

[ButtonRibbonCell.m](../GraphSketcher/App/ButtonRibbonCell.m) draws rounded segment outlines with three OmniQuartz functions: `OQAppendRoundedRect`, `OQAppendRectWithRoundedLeft` and `OQAppendRectWithRoundedRight`.

- Replace them with a small local helper built on `CGPathAddArcToPoint`.
- Remove the unused `OQDrawing.h` import in [RSImageExporter.m](../GraphSketcher/Model/RSImageExporter.m).
- Keep `OFExtent.h`: OmniStyle uses its inline functions.

## 10. NSUndoManager-OFExtensions

**Project lines:** 3 · **Delete:** 2 files, 549 lines

The only use is two debug call-site markers in [OSStyle.m](../GraphSketcher/OmniStyle/Basic/OSStyle.m): `OFUndoManagerPushCallSite` at line 792 and `OFUndoManagerPopCallSite` at line 822, plus the import at line 25. Delete all three lines.

## 11. NSColor-OAExtensions and OAColorProfile

**Project lines:** ~6 · **Omni edits:** ~5 · **Delete:** 4 files, 2,112 lines. Together with #1 and #2, the whole `OmniAppKit/ColorSync/` folder is gone.

Two live call sites need this code:

- On the Mac, OmniStyle archives text colors with `-[NSColor appendXML:]` and `+[NSColor colorFromXML:]`, at [OSColorStyleAttribute.m:46 and :58](../GraphSketcher/OmniStyle/Basic/OSColorStyleAttribute.m#L46). Change these to go through `OQColor` (`[[OQColor colorWithPlatformColor:value] appendXML:doc]` and `[[OQColor colorFromXML:cursor] toColor]`). That is what the iPad build already does, and the rest of the model already archives colors with `OQColor`.
- [OQColor.m:326 and :337](../OmniGroup/Frameworks/OmniQuartz/OQColor.m#L326) call `newCGColorWithCGColorSpace:` and `colorFromCGColor:`. Replace them with `CGColorCreateCopyByMatchingToColorSpace(…, nsColor.CGColor, …)` and `+[NSColor colorWithCGColor:]`, both available on macOS 12.

Check: `OQColor-Archiving` is a port of the NSColor code and uses the same element and attribute names. Still, round-trip a document whose labels have colored text, including a color picked from a named color list, and diff the saved XML before and after.

## 12. Known-key dictionaries → NSMutableDictionary

**Project lines:** ~45 · **Delete:** 4 files, 568 lines (`OFMutableKnownKeyDictionary`, `OFKnownKeyDictionaryTemplate`)

Only OmniStyle uses these: `OSStyle`, `OSStyleAttributeRegistry` and `OSStyleChange`. Most of the change is renaming the type in about 30 places. Two helpers are needed, `addLocallyAbsentValuesFromDictionary:` and `enumerateKeysAndObjectPairsWithDictionary:usingBlock:`, about 8 lines each. The payoff is small, so do this one last, or only to simplify OmniStyle.

## 13. OAToolbarWindowController → plain NSToolbar delegate

**Includes #6.** **Project lines:** ~80–100 · **Delete:** 12 files, 1,607 lines in total (965 beyond #6): `OAToolbarWindowController`, `OAToolbar`, `OAToolbarItem`, `OmniInspector/OAToolbarWindowController-OIExtensions`, plus #6's files

[GraphWindowController](../GraphSketcher/App/GraphWindowController.m) subclasses `OAToolbarWindowController` only to build its toolbar from `Graph.toolbar` and `GraphToolbar.strings`.

- Subclass `NSWindowController` instead.
- Read the plist and implement `toolbar:itemForItemIdentifier:willBeInsertedIntoToolbar:`, `toolbarAllowedItemIdentifiers:` and `toolbarDefaultItemIdentifiers:`. Each item takes its label, image, action and tooltip from the plist and strings file.
- Keep the existing autosave and customization settings.

This is at the edge of the 100-line budget.

---

## Considered and rejected (more than ~100 lines, or it changes the product)

- **Replace `OAApplication` with `NSApplication`.** This would remove ~5,200 lines, but `OIInspectorRegistry` depends on its responder-chain walking (`applyToResponderChain:`) and its menu-validation overrides. It also provides Help and exception reporting. Items 3 and 4 take the cheap parts.
- **Drop the zip writer** (`OUZipArchive` and minizip's `zip.c`, 2,154 lines). Compressed `.ogs` files are zip archives holding `contents.xml` and the preview PDF that the QuickLook plugin shows. macOS has no public API for writing zip files, and writing only plain XML would lose QuickLook previews and compression.
- **OmniInspector, OFXML\*, OQColor.** These are the inspector UI, the document format and the color model, so replacing any of them is a rewrite.

## The iPad app

The iPad project (`GraphSketcher-iPad.xcworkspace`, iOS 7 target) hasn't been built in this fork. It is the only user of **OmniUI, OmniUIDocument, OmniDocumentStore, OmniFileExchange, OmniDAV and OmniFileStore**: 805 files and ~74,000 source lines. Dropping iPad support would delete all of that with no refactoring, but that's a product decision rather than a cleanup. Removing just the sync frameworks (OmniFileExchange and OmniDAV) would touch 28 OmniUI files, which is over budget.

The frameworks' iOS targets also compile many of the shared files deleted above. If the iPad project is kept, remove those files from the iOS targets too. They would have to be fixed before it could build again in any case.

## Verifying each step

1. Run `build.command` and check `build.log` for errors. Missing symbols show up at link time; missing headers show up at compile time.
2. Smoke test:
   - Launch, create a graph, add points, lines, fills and text labels with colored and styled text.
   - Open each inspector tab, use the toolbar (including Customize Toolbar…), and open About, Help and the message of the day.
   - Save as compressed and as plain XML, reopen both, and check the QuickLook preview in Finder.
3. For #2, #7 and #11 in particular, also compare behavior against the current build. These change runtime behavior rather than just linking.
