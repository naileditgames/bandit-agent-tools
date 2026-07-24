use indexmap::IndexMap;
use rust_xlsxwriter::*;
use serde::Deserialize;
use std::{env, fs, io::BufReader};

const SKIP_LIMIT: usize = 500;

// ─── Typed data structures (mirroring generate_json_report.rs Serialize structs)
//
// Two separate wrapper structs let us deserialize each top-level section
// independently, opening the file twice and keeping only one section in
// memory at a time. Peak RSS is max(stats_size, rng_size) rather than their
// sum, which is critical for large BonusMin-style JSON files (1.9 GB+).

#[derive(Deserialize)]
struct StatsWrapper {
    stats: Stats,
}

#[derive(Deserialize)]
struct DistWrapper {
    rng_distribution: Distribution,
}

#[derive(Deserialize)]
struct Stats {
    #[serde(rename = "statsPerVariant")]
    stats_per_variant: IndexMap<String, VariantStats>,
}

#[derive(Deserialize)]
struct VariantStats {
    #[serde(rename = "uniqueContexts")]
    unique_contexts: i64,
    #[serde(rename = "uniqueWeightSets")]
    unique_weight_sets: i64,
    #[serde(rename = "weightSetsPerContext")]
    weight_sets_per_context: IndexMap<String, i64>,
}

#[derive(Deserialize)]
struct Distribution {
    variants: IndexMap<String, IndexMap<String, IndexMap<String, WeightSet>>>,
}

#[derive(Deserialize)]
struct WeightSet {
    #[serde(rename = "type")]
    type_: String,
    context: String,
    range: i64,
    chance: Option<f64>,
    weights: Option<Vec<serde_json::Value>>,
    #[serde(rename = "hitTable")]
    hit_table: IndexMap<String, i64>,
    #[serde(rename = "runStatsRng")]
    run_stats_rng: RunStats,
    #[serde(rename = "runStatsElements")]
    run_stats_elements: RunStats,
    meta: Meta,
}

#[derive(Deserialize)]
struct RunStats {
    up: i64,
    down: i64,
    same: i64,
}

#[derive(Deserialize)]
struct Meta {
    #[serde(rename = "numberOfCalls")]
    number_of_calls: i64,
}

// ─── Format helpers ───────────────────────────────────────────────────────────

fn b(left_thick: bool, right_thick: bool, top_thick: bool, bot_thick: bool) -> (bool, bool, bool, bool) {
    (left_thick, right_thick, top_thick, bot_thick)
}

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

fn m(ws: &mut Worksheet, row: u32, c1: u16, c2: u16, v: &str, fmt: &Format) -> Result<(), XlsxError> {
    if c1 == c2 {
        ws.write_with_format(row, c1, v, fmt)?;
    } else {
        ws.merge_range(row, c1, row, c2, v, fmt)?;
    }
    Ok(())
}

// ─── SUMMARY sheet ───────────────────────────────────────────────────────────

fn create_summary(wb: &mut Workbook, stats: &Stats) -> Result<(), XlsxError> {
    let ws = wb.add_worksheet().set_name("SUMMARY")?;
    let mut col: u16 = 1;

    for (variant, vstats) in &stats.stats_per_variant {
        print_variant_summary(ws, variant, vstats, col)?;
        col += 4;
    }

    for c in 0..col + 3 {
        ws.set_column_width(c, 18.0)?;
    }
    Ok(())
}

fn print_variant_summary(ws: &mut Worksheet, variant: &str, vstats: &VariantStats, sc: u16) -> Result<(), XlsxError> {
    let sr: u32 = 1;
    let ec = sc + 2;
    let wsc_len = vstats.weight_sets_per_context.len() as u32;
    let er = sr + 4 + 2 + wsc_len - 1;

    let e = |row: u32, c1: u16, c2: u16| blk(row, c1, c2, sr, sc, er, ec);

    m(ws, sr, sc, ec, "General Information", &hdr(e(sr, sc, ec)))?;

    w(ws, sr+1, sc, "variant", &sub(e(sr+1, sc, sc)))?;
    m(ws, sr+1, sc+1, ec, variant, &txt(e(sr+1, sc+1, ec)))?;

    w(ws, sr+2, sc, "contexts", &sub(e(sr+2, sc, sc)))?;
    m(ws, sr+2, sc+1, ec, &vstats.unique_contexts.to_string(), &txt(e(sr+2, sc+1, ec)))?;

    w(ws, sr+3, sc, "weight sets", &sub(e(sr+3, sc, sc)))?;
    m(ws, sr+3, sc+1, ec, &vstats.unique_weight_sets.to_string(), &txt(e(sr+3, sc+1, ec)))?;

    m(ws, sr+4, sc, ec, "Weight Sets Per Context", &hdr(e(sr+4, sc, ec)))?;

    w(ws, sr+5, sc, "context", &sub(e(sr+5, sc, sc)))?;
    w(ws, sr+5, sc+1, "weightSets", &sub(e(sr+5, sc+1, sc+1)))?;
    w(ws, sr+5, ec, "skipped", &sub(e(sr+5, ec, ec)))?;

    for (i, (ctx, hits)) in vstats.weight_sets_per_context.iter().enumerate() {
        let row = sr + 6 + i as u32;
        let skipped = if *hits > SKIP_LIMIT as i64 { "SKIP" } else { "" };
        w(ws, row, sc, ctx.as_str(), &txt(e(row, sc, sc)))?;
        w(ws, row, sc+1, &hits.to_string(), &txt(e(row, sc+1, sc+1)))?;
        w(ws, row, ec, skipped, &txt(e(row, ec, ec)))?;
    }
    Ok(())
}

// ─── Variant sheets ───────────────────────────────────────────────────────────

fn create_variants_stats(wb: &mut Workbook, dist: &Distribution) -> Result<(), XlsxError> {
    for (variant_name, variant_data) in &dist.variants {
        eprintln!("processing variant: {}", variant_name);
        create_variant_sheet(wb, variant_name, variant_data)?;
    }
    Ok(())
}

fn create_variant_sheet(
    wb: &mut Workbook,
    variant_name: &str,
    variant_data: &IndexMap<String, IndexMap<String, WeightSet>>,
) -> Result<(), XlsxError> {
    let ws = wb.add_worksheet().set_name(variant_name)?;
    let mut col: u16 = 1;

    for (context, context_data) in variant_data {
        if context_data.len() > SKIP_LIMIT {
            eprintln!("skipping context: {}", context);
            continue;
        }
        eprintln!("processing context: {}", context);
        print_context(ws, context_data, col)?;
        col += 4;
    }

    for c in 0..col + 3 {
        ws.set_column_width(c, 12.0)?;
    }
    Ok(())
}

fn print_context(
    ws: &mut Worksheet,
    context_data: &IndexMap<String, WeightSet>,
    start_col: u16,
) -> Result<(), XlsxError> {
    let margin: u32 = 2;
    let mut row: u32 = 1;

    for wsd in context_data.values() {
        let height = print_weight_set(ws, wsd, start_col, row)?;
        row += height + margin;
    }
    Ok(())
}

fn print_weight_set(ws: &mut Worksheet, wsd: &WeightSet, sc: u16, sr: u32) -> Result<u32, XlsxError> {
    let ec = sc + 2;
    let hit_len = wsd.hit_table.len() as u32;
    let length: u32 = match wsd.type_.as_str() {
        "hasChance" => 15,
        _ => 13 + hit_len,
    };
    let er = sr + length - 1;

    let e = |row: u32, c1: u16, c2: u16| blk(row, c1, c2, sr, sc, er, ec);

    m(ws, sr, sc, ec, "General Information", &hdr(e(sr, sc, ec)))?;

    w(ws, sr+1, sc, "context", &sub(e(sr+1, sc, sc)))?;
    m(ws, sr+1, sc+1, ec, &wsd.context, &txt(e(sr+1, sc+1, ec)))?;

    w(ws, sr+2, sc, "type", &sub(e(sr+2, sc, sc)))?;
    m(ws, sr+2, sc+1, ec, &wsd.type_, &txt(e(sr+2, sc+1, ec)))?;

    w(ws, sr+3, sc, "range", &sub(e(sr+3, sc, sc)))?;
    m(ws, sr+3, sc+1, ec, &wsd.range.to_string(), &txt(e(sr+3, sc+1, ec)))?;

    w(ws, sr+4, sc, "rng calls", &sub(e(sr+4, sc, sc)))?;
    m(ws, sr+4, sc+1, ec, &wsd.meta.number_of_calls.to_string(), &txt(e(sr+4, sc+1, ec)))?;

    m(ws, sr+5, sc, ec, "Run Statistics (rng)", &hdr(e(sr+5, sc, ec)))?;

    w(ws, sr+6, sc, "up", &sub(e(sr+6, sc, sc)))?;
    w(ws, sr+6, sc+1, "down", &sub(e(sr+6, sc+1, sc+1)))?;
    w(ws, sr+6, ec, "same", &sub(e(sr+6, ec, ec)))?;

    w(ws, sr+7, sc, &wsd.run_stats_rng.up.to_string(), &txt(e(sr+7, sc, sc)))?;
    w(ws, sr+7, sc+1, &wsd.run_stats_rng.down.to_string(), &txt(e(sr+7, sc+1, sc+1)))?;
    w(ws, sr+7, ec, &wsd.run_stats_rng.same.to_string(), &txt(e(sr+7, ec, ec)))?;

    m(ws, sr+8, sc, ec, "Run Statistics (elements)", &hdr(e(sr+8, sc, ec)))?;

    w(ws, sr+9, sc, "up", &sub(e(sr+9, sc, sc)))?;
    w(ws, sr+9, sc+1, "down", &sub(e(sr+9, sc+1, sc+1)))?;
    w(ws, sr+9, ec, "same", &sub(e(sr+9, ec, ec)))?;

    w(ws, sr+10, sc, &wsd.run_stats_elements.up.to_string(), &txt(e(sr+10, sc, sc)))?;
    w(ws, sr+10, sc+1, &wsd.run_stats_elements.down.to_string(), &txt(e(sr+10, sc+1, sc+1)))?;
    w(ws, sr+10, ec, &wsd.run_stats_elements.same.to_string(), &txt(e(sr+10, ec, ec)))?;

    m(ws, sr+11, sc, ec, "Hit Table", &hdr(e(sr+11, sc, ec)))?;

    match wsd.type_.as_str() {
        "hasChance" => {
            let row_h = sr + 12;
            w(ws, row_h, sc, "element", &sub(e(row_h, sc, sc)))?;
            w(ws, row_h, sc+1, "chance", &sub(e(row_h, sc+1, sc+1)))?;
            w(ws, row_h, ec, "hits", &sub(e(row_h, ec, ec)))?;

            let chance_str = wsd.chance.map(|c| c.to_string()).unwrap_or_default();
            let not_chance = format!("1 - {}", chance_str);
            let true_hits = wsd.hit_table.get("True").map(|v| v.to_string()).unwrap_or_default();
            let false_hits = wsd.hit_table.get("False").map(|v| v.to_string()).unwrap_or_default();

            let row_t = sr + 13;
            w(ws, row_t, sc, "True", &txt(e(row_t, sc, sc)))?;
            w(ws, row_t, sc+1, &chance_str, &txt(e(row_t, sc+1, sc+1)))?;
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

            for (i, (elem, hits)) in wsd.hit_table.iter().enumerate() {
                let row = sr + 13 + i as u32;
                w(ws, row, sc, elem.as_str(), &txt(e(row, sc, sc)))?;
                w(ws, row, sc+1, "1", &txt(e(row, sc+1, sc+1)))?;
                w(ws, row, ec, &hits.to_string(), &txt(e(row, ec, ec)))?;
            }
        }
        "randomWeighted" => {
            let row_h = sr + 12;
            w(ws, row_h, sc, "element", &sub(e(row_h, sc, sc)))?;
            w(ws, row_h, sc+1, "weight", &sub(e(row_h, sc+1, sc+1)))?;
            w(ws, row_h, ec, "hits", &sub(e(row_h, ec, ec)))?;

            for (i, (elem, hits)) in wsd.hit_table.iter().enumerate() {
                let row = sr + 13 + i as u32;
                let weight = wsd.weights
                    .as_ref()
                    .and_then(|w| w.get(i))
                    .map(|v| match v {
                        serde_json::Value::Number(n) => n.to_string(),
                        serde_json::Value::String(s) => s.clone(),
                        _ => String::new(),
                    })
                    .unwrap_or_else(|| "?".to_string());
                w(ws, row, sc, elem.as_str(), &txt(e(row, sc, sc)))?;
                w(ws, row, sc+1, &weight, &txt(e(row, sc+1, sc+1)))?;
                w(ws, row, ec, &hits.to_string(), &txt(e(row, ec, ec)))?;
            }
        }
        _ => {}
    }

    Ok(length)
}

// ─── Main ─────────────────────────────────────────────────────────────────────

fn open_reader(path: &str) -> BufReader<fs::File> {
    BufReader::new(fs::File::open(path).expect("Cannot open input JSON"))
}

fn main() -> Result<(), XlsxError> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("Usage: {} <input.json> <output.xlsx>", args[0]);
        std::process::exit(1);
    }
    let input = &args[1];

    let mut workbook = Workbook::new();

    // Pass 1: load only the "stats" section → SUMMARY sheet → drop.
    eprintln!("Pass 1: loading stats...");
    {
        let wrapper: StatsWrapper =
            serde_json::from_reader(open_reader(input)).expect("Cannot parse JSON (stats pass)");
        eprintln!("Creating SUMMARY sheet...");
        create_summary(&mut workbook, &wrapper.stats)?;
    } // wrapper (and the stats tree) is dropped here

    // Pass 2: load only the "rng_distribution" section → variant sheets → drop.
    eprintln!("Pass 2: loading rng_distribution...");
    {
        let wrapper: DistWrapper =
            serde_json::from_reader(open_reader(input)).expect("Cannot parse JSON (dist pass)");
        eprintln!("Creating variant sheets...");
        create_variants_stats(&mut workbook, &wrapper.rng_distribution)?;
    } // wrapper (and the distribution tree) is dropped here

    eprintln!("Saving Excel file...");
    workbook.save(&args[2])?;
    eprintln!("Done.");

    Ok(())
}
