#!/usr/bin/env python3
"""Write `description.xlsx` for a Netherlands cert "Files" package, matching the
hand-made reference packages.

The workbook is built as a zip of XML parts using ONLY the Python standard library
(`zipfile`) — no openpyxl or any third-party dependency — so the skill runs on any
Python 3, even where pip is broken.

Reference format:
  - one worksheet named "data", gridlines hidden
  - font Arial 10 throughout; column A width ~47, B ~108
  - row 1 : game display name in A1 (regular weight)
  - row 2 : header "File" | "Note" (bold)
  - row 3+: one row per file -> filename | short note

The note column is the whole point of the deliverable, so this refuses to write a
row with an empty note — that almost always means a file was left undescribed.

Manifest (shared with copy_files.py — basename of each src becomes the File cell):
  {
    "title": "RiptidePirates2",
    "out":   "/abs/.../G24-RiptidePirates2/Certification/NetherlandsFiles",
    "files": [ {"src": "/abs/.../Variant.cs", "note": "Static Config common for all variants"}, ... ]
  }

Usage:
  python3 build_description_xlsx.py --manifest /tmp/game_manifest.json
"""
import argparse
import json
import os
import sys
import zipfile

A_WIDTH = "47.1719"
B_WIDTH = "107.852"

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    '</Types>'
)

ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    '</Relationships>'
)

WORKBOOK = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheets><sheet name="data" sheetId="1" r:id="rId1"/></sheets>'
    '</workbook>'
)

WORKBOOK_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    '</Relationships>'
)

# Two cell formats: s=0 regular Arial 10, s=1 bold Arial 10.
STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2">'
    '<font><sz val="10"/><name val="Arial"/></font>'
    '<font><b/><sz val="10"/><name val="Arial"/></font>'
    '</fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="2">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    '</cellXfs>'
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    '</styleSheet>'
)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def cell(ref, text, style):
    return (f'<c r="{ref}" t="inlineStr" s="{style}">'
            f'<is><t xml:space="preserve">{esc(text)}</t></is></c>')


def sheet_xml(title, rows):
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetViews><sheetView showGridLines="0" workbookViewId="0"/></sheetViews>',
        '<cols>',
        f'<col min="1" max="1" width="{A_WIDTH}" customWidth="1"/>',
        f'<col min="2" max="2" width="{B_WIDTH}" customWidth="1"/>',
        '</cols>',
        '<sheetData>',
        f'<row r="1">{cell("A1", title, 0)}</row>',
        f'<row r="2">{cell("A2", "File", 1)}{cell("B2", "Note", 1)}</row>',
    ]
    for i, (fname, note) in enumerate(rows):
        r = 3 + i
        parts.append(f'<row r="{r}">{cell(f"A{r}", fname, 0)}{cell(f"B{r}", note, 0)}</row>')
    parts.append('</sheetData></worksheet>')
    return "".join(parts)


def build(title, rows, out_path):
    norm, bad = [], []
    for i, row in enumerate(rows):
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            sys.exit(f"ERROR: row {i} must be [file, note]: {row!r}")
        fname, note = row[0], row[1]
        if not str(note).strip():
            bad.append(fname)
        norm.append((fname, note))
    if bad:
        sys.exit("ERROR: empty note for: " + ", ".join(bad) +
                 "\n  Every file needs a short content-based note before writing the workbook.")

    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": ROOT_RELS,
        "xl/workbook.xml": WORKBOOK,
        "xl/_rels/workbook.xml.rels": WORKBOOK_RELS,
        "xl/styles.xml": STYLES,
        "xl/worksheets/sheet1.xml": sheet_xml(title, norm),
    }
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    print(f"Wrote {out_path}  ({len(norm)} files described)")
    print_summary(title, norm)


def print_summary(title, rows):
    """Emit a Markdown File|Note table for the model to relay to the user."""
    def md(s):
        return str(s).replace("|", "\\|").strip()
    print()
    print(f"### {title} — Netherlands certification files ({len(rows)})")
    print()
    print("| File | Note |")
    print("|------|------|")
    for fname, note in rows:
        print(f"| {md(fname)} | {md(note)} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    with open(args.manifest) as f:
        m = json.load(f)
    title = m["title"]
    out_dir = m["out"]
    out_path = out_dir if out_dir.endswith(".xlsx") else os.path.join(out_dir, "description.xlsx")
    rows = [[os.path.basename(e["src"] if isinstance(e, dict) else e),
             (e.get("note", "") if isinstance(e, dict) else "")] for e in m["files"]]

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    build(title, rows, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
