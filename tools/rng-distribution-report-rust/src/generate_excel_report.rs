use rust_xlsxwriter::*;
use serde_json::Value;
use std::{env, fs};

const SKIP_LIMIT: usize = 500;

// ─── Format helpers ───────────────────────────────────────────────────────────

fn b(left_thick: bool, right_thick: bool, top_thick: bool, bot_thick: bool) -> (bool, bool, bool, bool) {
    (left_thick, right_thick, top_thick, bot_thick)
}

/// Borders for a cell/range at (row, [c1..c2]) within block (sr..er, sc..ec).
fn blk(row: u32, c1: u16, c2: u16, sr: u32, sc: u16, er: u32, ec: u16) -> (bool, bool, bool, bool) {
    b(c1 == sc, c2 == ec, row == sr, row == er)
}

fn apply_border(fmt: Format, (lt, rt, tt, bt): (bool, bool, bool, bool)) -> Format {
    fmt.set_border_left(if lt { FormatBorder::Thick } else { FormatBorder::Thin })
        .set_border_right(if rt { FormatBorder::Thick } else { FormatBorder::Thin })
        .set_border_top(if tt { FormatBorder::Thick } else { FormatBorder::Thin })
        .set_border_bottom(if bt { FormatBorder::Thick } else { FormatBorder::Thin })
}

fn hdr(borders: (bool, bool, bool, bool)) -> Format {
    apply_border(
        Format::new()
            .set_background_color(Color::RGB(0x6D9EEB))
            .set_font_color(Color::RGB(0xFFFFFF))
            .set_bold()
            .set_align(FormatAlign::Center),
        borders,
    )
}

fn sub(borders: (bool, bool, bool, bool)) -> Format {
    apply_border(
        Format::new()
            .set_background_color(Color::RGB(0xA4C2F4))
            .set_font_color(Color::RGB(0x434343))
            .set_bold()
            .set_align(FormatAlign::Center),
        borders,
    )
}

fn txt(borders: (bool, bool, bool, bool)) -> Format {
    apply_border(Format::new().set_align(FormatAlign::Left), borders)
}

// ─── Cell write helpers ───────────────────────────────────────────────────────

fn w(ws: &mut Worksheet, row: u32, col: u16, v: &str, fmt: &Format) -> Result<(), XlsxError> {
    ws.write_with_format(row, col, v, fmt)?;
    Ok(())
}

/// Merge c1..=c2 on row, writing v as a string.
fn m(ws: &mut Worksheet, row: u32, c1: u16, c2: u16, v: &str, fmt: &Format) -> Result<(), XlsxError> {
    if c1 == c2 {
        ws.write_with_format(row, c1, v, fmt)?;
    } else {
        ws.merge_range(row, c1, row, c2, v, fmt)?;
    }
    Ok(())
}

/// Convert a JSON value to display string, matching Python's str() behaviour.
fn v2s(val: &Value) -> String {
    match val {
        Value::String(s) => s.clone(),
        Value::Number(n) => n.to_string(),
        Value::Bool(b) => if *b { "True" } else { "False" }.to_string(),
        Value::Null | Value::Array(_) | Value::Object(_) => String::new(),
    }
}

// ─── SUMMARY sheet ───────────────────────────────────────────────────────────

fn create_summary(wb: &mut Workbook, data: &Value) -> Result<(), XlsxError> {
    let ws = wb.add_worksheet().set_name("SUMMARY")?;
    let mut col: u16 = 1;

    if let Some(per_variant) = data["stats"]["statsPerVariant"].as_object() {
        for (variant, vstats) in per_variant {
            print_variant_summary(ws, variant, vstats, col)?;
            col += 4;
        }
    }

    for c in 0..col + 3 {
        ws.set_column_width(c, 18.0)?;
    }
    Ok(())
}

fn print_variant_summary(ws: &mut Worksheet, variant: &str, vstats: &Value, sc: u16) -> Result<(), XlsxError> {
    let sr: u32 = 1;
    let ec = sc + 2;
    let wsc_len = vstats["weightSetsPerContext"]
        .as_object()
        .map(|m| m.len())
        .unwrap_or(0) as u32;
    let er = sr + 4 + 2 + wsc_len - 1; // 6 rows fixed + wsc rows

    let e = |row: u32, c1: u16, c2: u16| blk(row, c1, c2, sr, sc, er, ec);

    // Row sr: "General Information" header
    m(ws, sr, sc, ec, "General Information", &hdr(e(sr, sc, ec)))?;

    // Row sr+1: variant
    w(ws, sr+1, sc, "variant", &sub(e(sr+1, sc, sc)))?;
    m(ws, sr+1, sc+1, ec, variant, &txt(e(sr+1, sc+1, ec)))?;

    // Row sr+2: contexts
    w(ws, sr+2, sc, "contexts", &sub(e(sr+2, sc, sc)))?;
    m(ws, sr+2, sc+1, ec, &v2s(&vstats["uniqueContexts"]), &txt(e(sr+2, sc+1, ec)))?;

    // Row sr+3: weight sets
    w(ws, sr+3, sc, "weight sets", &sub(e(sr+3, sc, sc)))?;
    m(ws, sr+3, sc+1, ec, &v2s(&vstats["uniqueWeightSets"]), &txt(e(sr+3, sc+1, ec)))?;

    // Row sr+4: "Weight Sets Per Context" header
    m(ws, sr+4, sc, ec, "Weight Sets Per Context", &hdr(e(sr+4, sc, ec)))?;

    // Row sr+5: sub-headers
    w(ws, sr+5, sc, "context", &sub(e(sr+5, sc, sc)))?;
    w(ws, sr+5, sc+1, "weightSets", &sub(e(sr+5, sc+1, sc+1)))?;
    w(ws, sr+5, ec, "skipped", &sub(e(sr+5, ec, ec)))?;

    // Rows sr+6..: per-context data
    if let Some(wsc_map) = vstats["weightSetsPerContext"].as_object() {
        for (i, (ctx, hits_val)) in wsc_map.iter().enumerate() {
            let row = sr + 6 + i as u32;
            let hits = hits_val.as_i64().unwrap_or(0);
            let skipped = if hits > SKIP_LIMIT as i64 { "SKIP" } else { "" };

            w(ws, row, sc, ctx.as_str(), &txt(e(row, sc, sc)))?;
            w(ws, row, sc+1, &hits.to_string(), &txt(e(row, sc+1, sc+1)))?;
            w(ws, row, ec, skipped, &txt(e(row, ec, ec)))?;
        }
    }
    Ok(())
}

// ─── Variant sheets ───────────────────────────────────────────────────────────

fn create_variants_stats(wb: &mut Workbook, data: &Value) -> Result<(), XlsxError> {
    if let Some(variants) = data["rng_distribution"]["variants"].as_object() {
        for (variant_name, variant_data) in variants {
            eprintln!("processing variant: {}", variant_name);
            create_variant_sheet(wb, variant_name, variant_data)?;
        }
    }
    Ok(())
}

fn create_variant_sheet(wb: &mut Workbook, variant_name: &str, variant_data: &Value) -> Result<(), XlsxError> {
    let ws = wb.add_worksheet().set_name(variant_name)?;
    let mut col: u16 = 1;

    if let Some(contexts) = variant_data.as_object() {
        for (context, context_data) in contexts {
            let ws_count = context_data.as_object().map(|m| m.len()).unwrap_or(0);
            if ws_count > SKIP_LIMIT {
                eprintln!("skipping context: {}", context);
                continue;
            }
            eprintln!("processing context: {}", context);
            print_context(ws, context_data, col)?;
            col += 4;
        }
    }

    for c in 0..col + 3 {
        ws.set_column_width(c, 12.0)?;
    }
    Ok(())
}

fn print_context(ws: &mut Worksheet, context_data: &Value, start_col: u16) -> Result<(), XlsxError> {
    let margin: u32 = 2;
    let mut row: u32 = 1;

    if let Some(ctx_map) = context_data.as_object() {
        for (_hash, weight_set_data) in ctx_map {
            let height = print_weight_set(ws, weight_set_data, start_col, row)?;
            row += height + margin;
        }
    }
    Ok(())
}

/// Print a single weight-set block. Returns the block height (number of rows).
fn print_weight_set(ws: &mut Worksheet, wsd: &Value, sc: u16, sr: u32) -> Result<u32, XlsxError> {
    let ec = sc + 2;
    let ws_type = wsd["type"].as_str().unwrap_or("");

    let hit_len = wsd["hitTable"].as_object().map(|m| m.len()).unwrap_or(0) as u32;
    let length: u32 = match ws_type {
        "hasChance" => 15,
        _ => 13 + hit_len,
    };
    let er = sr + length - 1;

    let e = |row: u32, c1: u16, c2: u16| blk(row, c1, c2, sr, sc, er, ec);

    // Row sr: "General Information"
    m(ws, sr, sc, ec, "General Information", &hdr(e(sr, sc, ec)))?;

    // Row sr+1: context
    w(ws, sr+1, sc, "context", &sub(e(sr+1, sc, sc)))?;
    m(ws, sr+1, sc+1, ec, &v2s(&wsd["context"]), &txt(e(sr+1, sc+1, ec)))?;

    // Row sr+2: type
    w(ws, sr+2, sc, "type", &sub(e(sr+2, sc, sc)))?;
    m(ws, sr+2, sc+1, ec, &v2s(&wsd["type"]), &txt(e(sr+2, sc+1, ec)))?;

    // Row sr+3: range
    w(ws, sr+3, sc, "range", &sub(e(sr+3, sc, sc)))?;
    m(ws, sr+3, sc+1, ec, &v2s(&wsd["range"]), &txt(e(sr+3, sc+1, ec)))?;

    // Row sr+4: rng calls
    w(ws, sr+4, sc, "rng calls", &sub(e(sr+4, sc, sc)))?;
    m(ws, sr+4, sc+1, ec, &v2s(&wsd["meta"]["numberOfCalls"]), &txt(e(sr+4, sc+1, ec)))?;

    // Row sr+5: "Run Statistics (rng)"
    m(ws, sr+5, sc, ec, "Run Statistics (rng)", &hdr(e(sr+5, sc, ec)))?;

    // Row sr+6: up/down/same sub-headers
    w(ws, sr+6, sc, "up", &sub(e(sr+6, sc, sc)))?;
    w(ws, sr+6, sc+1, "down", &sub(e(sr+6, sc+1, sc+1)))?;
    w(ws, sr+6, ec, "same", &sub(e(sr+6, ec, ec)))?;

    // Row sr+7: rng run stats values
    w(ws, sr+7, sc, &v2s(&wsd["runStatsRng"]["up"]), &txt(e(sr+7, sc, sc)))?;
    w(ws, sr+7, sc+1, &v2s(&wsd["runStatsRng"]["down"]), &txt(e(sr+7, sc+1, sc+1)))?;
    w(ws, sr+7, ec, &v2s(&wsd["runStatsRng"]["same"]), &txt(e(sr+7, ec, ec)))?;

    // Row sr+8: "Run Statistics (elements)"
    m(ws, sr+8, sc, ec, "Run Statistics (elements)", &hdr(e(sr+8, sc, ec)))?;

    // Row sr+9: up/down/same sub-headers
    w(ws, sr+9, sc, "up", &sub(e(sr+9, sc, sc)))?;
    w(ws, sr+9, sc+1, "down", &sub(e(sr+9, sc+1, sc+1)))?;
    w(ws, sr+9, ec, "same", &sub(e(sr+9, ec, ec)))?;

    // Row sr+10: element run stats values
    w(ws, sr+10, sc, &v2s(&wsd["runStatsElements"]["up"]), &txt(e(sr+10, sc, sc)))?;
    w(ws, sr+10, sc+1, &v2s(&wsd["runStatsElements"]["down"]), &txt(e(sr+10, sc+1, sc+1)))?;
    w(ws, sr+10, ec, &v2s(&wsd["runStatsElements"]["same"]), &txt(e(sr+10, ec, ec)))?;

    // Row sr+11: "Hit Table"
    m(ws, sr+11, sc, ec, "Hit Table", &hdr(e(sr+11, sc, ec)))?;

    match ws_type {
        "hasChance" => {
            let row_h = sr + 12;
            w(ws, row_h, sc, "element", &sub(e(row_h, sc, sc)))?;
            w(ws, row_h, sc+1, "chance", &sub(e(row_h, sc+1, sc+1)))?;
            w(ws, row_h, ec, "hits", &sub(e(row_h, ec, ec)))?;

            let chance = v2s(&wsd["chance"]);
            let not_chance = format!("1 - {}", chance);
            let true_hits = v2s(&wsd["hitTable"]["True"]);
            let false_hits = v2s(&wsd["hitTable"]["False"]);

            let row_t = sr + 13;
            w(ws, row_t, sc, "True", &txt(e(row_t, sc, sc)))?;
            w(ws, row_t, sc+1, &chance, &txt(e(row_t, sc+1, sc+1)))?;
            w(ws, row_t, ec, &true_hits, &txt(e(row_t, ec, ec)))?;

            let row_f = sr + 14;
            w(ws, row_f, sc, "False", &txt(e(row_f, sc, sc)))?;
            w(ws, row_f, sc+1, &not_chance, &txt(e(row_f, sc+1, sc+1)))?;
            w(ws, row_f, ec, &false_hits, &txt(e(row_f, ec, ec)))?;
        }
        "randomIndex" => {
            let row_h = sr + 12;
            w(ws, row_h, sc, "element", &sub(e(row_h, sc, sc)))?;
            w(ws, row_h, sc+1, "weight", &sub(e(row_h, sc+1, sc+1)))?;
            w(ws, row_h, ec, "hits", &sub(e(row_h, ec, ec)))?;

            if let Some(ht) = wsd["hitTable"].as_object() {
                for (i, (elem, hits)) in ht.iter().enumerate() {
                    let row = sr + 13 + i as u32;
                    w(ws, row, sc, elem.as_str(), &txt(e(row, sc, sc)))?;
                    w(ws, row, sc+1, "1", &txt(e(row, sc+1, sc+1)))?;
                    w(ws, row, ec, &v2s(hits), &txt(e(row, ec, ec)))?;
                }
            }
        }
        "randomWeighted" => {
            let row_h = sr + 12;
            w(ws, row_h, sc, "element", &sub(e(row_h, sc, sc)))?;
            w(ws, row_h, sc+1, "weight", &sub(e(row_h, sc+1, sc+1)))?;
            w(ws, row_h, ec, "hits", &sub(e(row_h, ec, ec)))?;

            if let Some(ht) = wsd["hitTable"].as_object() {
                let weights = wsd["weights"].as_array();
                for (i, (elem, hits)) in ht.iter().enumerate() {
                    let row = sr + 13 + i as u32;
                    let weight = weights
                        .and_then(|w| w.get(i))
                        .map(|v| v2s(v))
                        .unwrap_or_else(|| "?".to_string());
                    w(ws, row, sc, elem.as_str(), &txt(e(row, sc, sc)))?;
                    w(ws, row, sc+1, &weight, &txt(e(row, sc+1, sc+1)))?;
                    w(ws, row, ec, &v2s(hits), &txt(e(row, ec, ec)))?;
                }
            }
        }
        _ => {}
    }

    Ok(length)
}

// ─── Main ─────────────────────────────────────────────────────────────────────

fn main() -> Result<(), XlsxError> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("Usage: {} <input.json> <output.xlsx>", args[0]);
        std::process::exit(1);
    }

    eprintln!("Loading JSON...");
    let json_str = fs::read_to_string(&args[1]).expect("Cannot read input JSON");
    let data: Value = serde_json::from_str(&json_str).expect("Cannot parse JSON");

    let mut workbook = Workbook::new();

    eprintln!("Creating SUMMARY sheet...");
    create_summary(&mut workbook, &data)?;

    eprintln!("Creating variant sheets...");
    create_variants_stats(&mut workbook, &data)?;

    eprintln!("Saving Excel file...");
    workbook.save(&args[2])?;
    eprintln!("Done.");

    Ok(())
}
