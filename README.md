# GraphSketcher

A fast, simple graph drawing and data plotting app for OS X and iPad. 

## About This Fork

This fork keeps the Mac app building and running on current macOS (Tahoe 26.5+) and Xcode, targeting Apple Silicon. The upstream project hasn't been updated since ~2018 and no longer builds as-is on modern tooling.

Notable changes from upstream:

- Builds clean on Xcode 26 / Apple Silicon (arm64-only; Intel/x86_64 is no longer targeted), with a minimum deployment target of macOS 14 (Sonoma).
- Zero build warnings and no launch-time assertion failures.
- LinkBack (the old inter-app linking mechanism) has been removed — it depended on Distributed Objects, which is incompatible with the App Sandbox.
- Finder integration for `.ograph` files: Quick Look thumbnails/previews and Spotlight metadata indexing.
- The original toolbar and inspector appearance is preserved on Tahoe (opting out of the Liquid Glass redesign), since the app wasn't updated for the new design language.
- The iPad target is **not maintained** in this fork (see [Supported Targets](#supported-targets)).
- This is a local, from-source build only — no notarization, Developer ID signing, or Mac App Store distribution (see [Prerequisites](#prerequisites)).

None of this is upstreamed; treat this branch as a personal maintenance fork rather than a drop-in replacement for the original.

## Download 

This fork doesn't publish binary releases — build it from source (see below). If you just want to download a working build of the original app, head over to the [The Releases Page](https://github.com/graphsketcher/GraphSketcher/releases) for GraphSketcher for Mac (note: that release predates the changes in this fork).

## Introduction

GraphSketcher is a simple, elegant tool for quickly sketching graphs and plotting data — but you don’t even need data to get started. It’s perfect for reports, presentations, and problem sets where you need to produce sharp-looking graphs on the fly.

## Setting it Free

Graph Sketcher was created by Robin Stewart in 2007. The Omni Group further developed OmniGraphSketcher for Mac and brought it to the iPad in 2010. All GraphSketcher-related source code was open-sourced in 2014.

## What’s Inside

The Mac app is located inside the `App` folder, including its Quick Look thumbnail/preview app extensions (`GraphSketcherThumbnail`, `GraphSketcherPreview`). The iPad source is in the `iPad` folder (currently unmaintained). Shared model code lives in `Model` and `OmniStyle`. `QuickLook` and `Spotlight` hold the Finder plugins (a Quick Look generator and a Spotlight metadata importer) that give `.ograph` files thumbnails, previews, and Spotlight search support.

## How to Build

### Checking out the source

    git clone --recurse-submodules https://github.com/kyusik-thistle/GraphSketcher.git

If you already have a clone without the submodule, run this from the repo root instead:

    git submodule update --init --recursive

### Dependencies

GraphSketcher includes the OmniGroup open source frameworks as a git submodule, pinned to [a fork](https://github.com/kyusik-thistle/OmniGroup) carrying the patches needed to build on modern Xcode/macOS, patched in place on top of the same old snapshot the app was already built against — not rebased onto current upstream OmniGroup, which has diverged far enough that reintegrating it would be its own project.

`.gitmodules` pins the submodule to that fork's `tahoe-modernization` branch, so it's safe to run:

	git submodule update --remote

This only ever pulls further commits pushed to `tahoe-modernization` on the fork — it will not wander onto upstream OmniGroup's unrelated history.

### Supported Targets

The Mac app targets Apple Silicon (arm64) running macOS 14 (Sonoma) or later.

The iPad app and Intel (x86_64) Mac builds are **not maintained** in this fork — the source and Xcode project are still present, but haven't been touched as part of this modernization work and may not build.

### Prerequisites

Building GraphSketcher requires Xcode 26.5 or later.

#### GraphSketcher for Mac

GraphSketcher for Mac is sandboxed. The build is configured for local, ad-hoc code signing (`OMNI_MAC_CODE_SIGN_IDENTITY = -` in `OmniGroup/Configurations/Target-Mac-Common.xcconfig`), so no paid Apple Developer account or code signing identity is required to build and run it on your own Mac.

Ad-hoc signing isn't sufficient for notarization or distribution to other Macs — that would require its own code signing identity and further setup, which this fork doesn't currently do.

#### GraphSketcher for iPad

**Not maintained.** The iPad target and workspace (`GraphSketcher-iPad.xcworkspace`) haven't been updated for modern Xcode/toolchains as part of this work, and may not build. If you want to try anyway, you'll need an iOS code signing identity in your keychain, same as any iOS project.

### Building GraphSketcher-Mac

Open “GraphSketcher-Mac.xcworkspace”.

Build the “ALL” scheme.

There is no step 3.

## License

MIT-style Omni Source License 2007.

See OmniSourceLicense.html in this package.

Enjoy!
