# rng-report-rs

Rust reimplementation of the RNG distribution report tools. Replaces the Python scripts with low-memory, fast binaries.

## Why Rust?

The Python `generate_excel_report.py` uses `openpyxl`, which builds the entire workbook in memory before writing. For large reports this causes OOM errors. `rust_xlsxwriter` streams directly to the XLSX ZIP file — constant memory regardless of report size.

## Build

Requires Rust (install via https://rustup.rs):

```bash
cargo build --release
```

Binaries land in `target/release/`.

## Usage

**Step 1 — JSON report from CSV data extract:**

```bash
./target/release/generate_json_report <input.csv> <output.json>
```

**Step 2 — Excel report from JSON:**

```bash
./target/release/generate_excel_report <input.json> <output.xlsx>
```

## Compatibility

Produces identical output to the Python scripts. Preserves insertion order in all JSON maps (using `indexmap`) so element ordering in hit tables is correct.
