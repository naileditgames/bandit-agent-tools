#!/usr/bin/env python3
"""Zip the deliverable folder into a clean `<out>.zip` next to it.

Deterministic mechanics only. Reads the same manifest as the other two scripts,
takes its `out` folder (e.g. `<game>/Certification/NetherlandsFiles`), and writes
`<game>/Certification/NetherlandsFiles.zip` containing the folder's files **flat**
(matching the most recent reference deliverable) — no nested folder, and no macOS
junk (`.DS_Store`, `__MACOSX/`). Run it after copy_files.py + build_description_xlsx.py.

The zip is a regenerable artifact and is git-ignored (see repo .gitignore); the
folder itself (the `.cs` files + description.xlsx) is what gets committed.

It also copies the zip onto the clipboard as a file (not a path) so you can paste
it straight into Mail/Slack/Finder — macOS and Windows reliably, Linux best-effort
(GNOME file managers, needs wl-clipboard/xclip). Pass --no-clipboard to skip.

Usage:
  python3 make_zip.py --manifest /tmp/game_manifest.json
  python3 make_zip.py --manifest /tmp/game_manifest.json --no-clipboard
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import zipfile

SKIP = {".DS_Store"}


def copy_to_clipboard(path):
    """Put the zip file itself on the clipboard so it can be pasted/attached.

    Cross-platform best-effort — never fails the run, and always prints what
    happened (and the path) so the file is findable even if the copy didn't take:
      - macOS   : osascript — pastes the file in Finder/Mail/Slack.
      - Windows : PowerShell Set-Clipboard -Path — pastes the file in Explorer/Outlook.
      - Linux   : wl-copy / xclip with the GNOME file-copy target (Nautilus/Nemo/Caja);
                  desktop-specific and needs those tools — may not work on KDE/others.
    """
    plat = sys.platform
    try:
        if plat == "darwin":
            esc = path.replace("\\", "\\\\").replace('"', '\\"')
            subprocess.run(["osascript", "-e", f'set the clipboard to POSIX file "{esc}"'],
                           check=True, capture_output=True, text=True)
            print("  Copied the zip to the clipboard — paste (Cmd+V) to attach/move it")
            return
        if plat == "win32" or plat == "cygwin":
            ps = "Set-Clipboard -Path '{}'".format(path.replace("'", "''"))
            subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           check=True, capture_output=True, text=True)
            print("  Copied the zip to the clipboard — paste (Ctrl+V) to attach/move it")
            return
        if plat.startswith("linux") and _linux_copy_file(path):
            print("  Copied the zip to the clipboard — paste (Ctrl+V) in your file manager")
            return
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        detail = (getattr(e, "stderr", "") or str(e)).strip()
        print(f"  (clipboard copy failed — the zip is still written: {detail})")
        return
    print(f"  (clipboard copy unavailable on this setup — the zip is at: {path})")


def _linux_copy_file(path):
    """GNOME-family file-managers read the URI list under x-special/gnome-copied-files.
    Use wl-copy on Wayland, else xclip on X11. Returns False if neither tool exists."""
    payload = "copy\nfile://" + urllib.parse.quote(os.path.abspath(path))
    mime = "x-special/gnome-copied-files"
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
        subprocess.run(["wl-copy", "--type", mime], input=payload, text=True,
                       check=True, capture_output=True)
        return True
    if shutil.which("xclip"):
        subprocess.run(["xclip", "-selection", "clipboard", "-t", mime],
                       input=payload, text=True, check=True, capture_output=True)
        return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--zip-out", help="where to write the zip (default: <out>.zip). "
                    "Use this to write the committed NetherlandsFiles.zip while the "
                    "deliverable folder itself is a throwaway temp dir.")
    ap.add_argument("--no-clipboard", action="store_true",
                    help="don't copy the resulting zip to the macOS clipboard")
    args = ap.parse_args()

    with open(args.manifest) as f:
        out = json.load(f).get("out")
    if not out:
        sys.exit("ERROR: manifest has no 'out' folder")
    out = os.path.abspath(out)
    if not os.path.isdir(out):
        sys.exit(f"ERROR: deliverable folder does not exist yet: {out}\n  Run copy_files.py + build_description_xlsx.py first.")

    names = sorted(n for n in os.listdir(out)
                   if n not in SKIP and os.path.isfile(os.path.join(out, n)))
    if not names:
        sys.exit(f"ERROR: nothing to zip in {out}")

    zip_path = os.path.abspath(args.zip_out) if args.zip_out else out + ".zip"
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.write(os.path.join(out, n), arcname=n)

    print(f"Wrote {zip_path}  ({len(names)} files)")
    if not args.no_clipboard:
        copy_to_clipboard(zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
