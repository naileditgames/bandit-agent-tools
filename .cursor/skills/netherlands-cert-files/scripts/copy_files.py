#!/usr/bin/env python3
"""Flatten-copy a chosen set of source files into the deliverable folder.

Deterministic mechanics only — no selection logic lives here. You (the model)
decide which files belong by reading the game; this script copies the exact list
you give it, verbatim, into the manifest's `out` folder, and fails loudly if any
source is missing or two sources collide on one basename — so a typo or a stray
duplicate can never silently drop a math file.

Manifest (shared with build_description_xlsx.py):

  {
    "title": "RiptidePirates2",
    "out":   "/abs/.../G24-RiptidePirates2/Certification/NetherlandsFiles",
    "files": [
      {"src": "/abs/.../Game/Logic/Config/Variants/Variant.cs", "note": "Static Config common for all variants"},
      {"src": "/abs/.../Game/Logic/BaseRound.cs",               "note": "Base round entry point"}
    ]
  }

Usage:
  python3 copy_files.py --manifest /tmp/game_manifest.json
"""
import argparse
import json
import os
import shutil
import sys


def load_manifest(path):
    with open(path) as f:
        m = json.load(f)
    out = m.get("out")
    if not out:
        sys.exit("ERROR: manifest has no 'out' folder")
    srcs = []
    for i, entry in enumerate(m.get("files", [])):
        src = entry.get("src") if isinstance(entry, dict) else entry
        if not src:
            sys.exit(f"ERROR: file entry {i} has no 'src': {entry!r}")
        srcs.append(src)
    if not srcs:
        sys.exit("ERROR: manifest 'files' is empty — nothing to copy")
    return os.path.abspath(out), srcs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    out, srcs = load_manifest(args.manifest)

    missing = [s for s in srcs if not os.path.isfile(s)]
    if missing:
        sys.exit("ERROR: these source files do not exist:\n  " + "\n  ".join(missing))

    # guard against two different sources flattening onto the same filename
    seen = {}
    for s in srcs:
        base = os.path.basename(s)
        if base in seen and os.path.abspath(seen[base]) != os.path.abspath(s):
            sys.exit(f"ERROR: basename collision for {base}:\n  {seen[base]}\n  {s}")
        seen[base] = s

    os.makedirs(out, exist_ok=True)
    for s in srcs:
        shutil.copy2(s, os.path.join(out, os.path.basename(s)))

    print(f"Copied {len(srcs)} files into {out}")
    for s in srcs:
        print(f"  {os.path.basename(s)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
