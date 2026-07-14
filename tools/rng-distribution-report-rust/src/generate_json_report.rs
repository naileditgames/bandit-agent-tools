use base64::Engine as _;
use flate2::read::DeflateDecoder;
use indexmap::IndexMap;
use md5::{Digest, Md5};
use serde::Serialize;
use serde_json::Value;
use std::io::Read;
use std::time::Instant;
use std::{env, fs};

const RANGE_LIMIT: i64 = 1_000_000;

// ─── Data structures ─────────────────────────────────────────────────────────

#[derive(Serialize)]
struct Report {
    rng_distribution: Distribution,
    stats: Stats,
}

#[derive(Serialize)]
struct Distribution {
    variants: IndexMap<String, IndexMap<String, IndexMap<String, WeightSet>>>,
}

#[derive(Serialize)]
struct Stats {
    #[serde(rename = "processedRngCalls")]
    processed_rng_calls: i64,
    #[serde(rename = "statsPerVariant")]
    stats_per_variant: IndexMap<String, VariantStats>,
    #[serde(rename = "uniqueContexts")]
    unique_contexts: i64,
    #[serde(rename = "uniqueWeightSets")]
    unique_weight_sets: i64,
}

#[derive(Serialize)]
struct VariantStats {
    #[serde(rename = "uniqueContexts")]
    unique_contexts: i64,
    #[serde(rename = "uniqueWeightSets")]
    unique_weight_sets: i64,
    #[serde(rename = "weightSetsPerContext")]
    weight_sets_per_context: IndexMap<String, i64>,
}

#[derive(Serialize)]
struct WeightSet {
    #[serde(rename = "type")]
    type_: String,
    variant: String,
    context: String,
    range: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    chance: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    elements: Option<Vec<Value>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    weights: Option<Vec<Value>>,
    #[serde(rename = "hitTable")]
    hit_table: IndexMap<String, i64>,
    #[serde(rename = "runStatsRng")]
    run_stats_rng: RunStats,
    #[serde(rename = "runStatsElements")]
    run_stats_elements: RunStats,
    meta: Meta,
}

#[derive(Serialize)]
struct RunStats {
    up: i64,
    down: i64,
    same: i64,
}

#[derive(Serialize)]
struct Meta {
    #[serde(rename = "hashText")]
    hash_text: String,
    hash: String,
    first: bool,
    #[serde(rename = "lastElement")]
    last_element: Value,
    #[serde(rename = "lastRngNumber")]
    last_rng_number: i64,
    #[serde(rename = "numberOfCalls")]
    number_of_calls: i64,
}

// ─── Processor ───────────────────────────────────────────────────────────────

struct RngStatsProcessor {
    processed_spins: u64,
    start_time: Instant,
    variants: IndexMap<String, IndexMap<String, IndexMap<String, WeightSet>>>,
    stats: Stats,
}

impl RngStatsProcessor {
    fn new() -> Self {
        RngStatsProcessor {
            processed_spins: 0,
            start_time: Instant::now(),
            variants: IndexMap::new(),
            stats: Stats {
                processed_rng_calls: 0,
                stats_per_variant: IndexMap::new(),
                unique_contexts: 0,
                unique_weight_sets: 0,
            },
        }
    }

    fn process_file(&mut self, path: &str) {
        self.start_time = Instant::now();
        eprintln!("start processing file: {}", path);

        let mut rdr = csv::ReaderBuilder::new()
            .flexible(true)
            .from_path(path)
            .expect("Cannot open CSV file");

        let header_idx: std::collections::HashMap<String, usize> = rdr
            .headers()
            .expect("Cannot read CSV headers")
            .iter()
            .enumerate()
            .map(|(i, h)| (h.to_string(), i))
            .collect();

        let cmd_idx = *header_idx.get("Command").expect("Missing 'Command' column");
        let extra_idx = *header_idx
            .get("AdditionalParameters")
            .expect("Missing 'AdditionalParameters' column");

        let mut records = rdr.records();
        while let Some(Ok(record)) = records.next() {
            let command = record.get(cmd_idx).unwrap_or("").to_string();
            let extra = record.get(extra_idx).unwrap_or("").to_string();

            self.processed_spins += 1;
            if self.processed_spins % 10_000 == 0 {
                eprint!(
                    "\rElapsed Time: {:.2}s Processed Spins: {} ",
                    self.start_time.elapsed().as_secs_f64(),
                    self.processed_spins
                );
            }

            if command == "CollectCommand" || extra.is_empty() {
                continue;
            }

            if let Some(rng_data) = Self::extract_rng_data(&extra) {
                if let Some(entries) = rng_data.as_array() {
                    for entry in entries.clone() {
                        self.process_rng_entry(&entry);
                    }
                }
            }
        }
        eprintln!(
            "\rElapsed Time: {:.2}s Processed Spins: {} ",
            self.start_time.elapsed().as_secs_f64(),
            self.processed_spins
        );
        eprintln!();
    }

    fn process_rng_entry(&mut self, entry: &Value) {
        self.stats.processed_rng_calls += 1;

        let type_ = match entry["type"].as_str() {
            Some(t) => t.to_string(),
            None => return,
        };
        let variant = match entry["variant"].as_str() {
            Some(v) => v.to_string(),
            None => return,
        };
        let context = match entry["context"].as_str() {
            Some(c) => c.to_string(),
            None => return,
        };
        let range = entry["range"].as_i64().unwrap_or(0);

        if range > RANGE_LIMIT && type_ != "hasChance" {
            return;
        }

        // Ensure variant exists
        if !self.variants.contains_key(&variant) {
            self.variants.insert(variant.clone(), IndexMap::new());
            self.stats.stats_per_variant.insert(
                variant.clone(),
                VariantStats {
                    unique_contexts: 0,
                    unique_weight_sets: 0,
                    weight_sets_per_context: IndexMap::new(),
                },
            );
        }

        // Ensure context exists
        if !self.variants[&variant].contains_key(&context) {
            self.variants
                .get_mut(&variant)
                .unwrap()
                .insert(context.clone(), IndexMap::new());
            self.stats.unique_contexts += 1;
            self.stats
                .stats_per_variant
                .get_mut(&variant)
                .unwrap()
                .unique_contexts += 1;
        }

        match type_.as_str() {
            "randomIndex" => self.process_random_index(entry, &variant, &context, range),
            "randomWeighted" => self.process_random_weighted(entry, &variant, &context, range),
            "hasChance" => self.process_has_chance(entry, &variant, &context, range),
            _ => {}
        }
    }

    fn process_random_index(&mut self, entry: &Value, variant: &str, context: &str, range: i64) {
        let result = entry["result"].as_i64().unwrap_or(0);
        let hash_text = format!("randomIndex{}{}{}", variant, context, range);
        let hash = md5_hex(&hash_text);

        // Ensure entry exists (scoped borrow to avoid conflict with stats update)
        let is_new = !self.variants[variant][context].contains_key(&hash);
        if is_new {
            {
                let hit_table: IndexMap<String, i64> =
                    (0..range).map(|i| (i.to_string(), 0)).collect();
                self.variants
                    .get_mut(variant).unwrap()
                    .get_mut(context).unwrap()
                    .insert(hash.clone(), WeightSet {
                        type_: "randomIndex".to_string(),
                        variant: variant.to_string(),
                        context: context.to_string(),
                        range,
                        chance: None,
                        elements: None,
                        weights: None,
                        hit_table,
                        run_stats_rng: RunStats { up: 0, down: 0, same: 0 },
                        run_stats_elements: RunStats { up: 0, down: 0, same: 0 },
                        meta: Meta {
                            hash_text,
                            hash: hash.clone(),
                            first: true,
                            last_element: Value::String(String::new()),
                            last_rng_number: 0,
                            number_of_calls: 0,
                        },
                    });
            }
            self.register_weight_set(variant, context);
        }

        let ws = self.variants
            .get_mut(variant).unwrap()
            .get_mut(context).unwrap()
            .get_mut(&hash).unwrap();
        ws.meta.number_of_calls += 1;
        *ws.hit_table.entry(result.to_string()).or_insert(0) += 1;

        if ws.meta.first {
            ws.meta.first = false;
            ws.meta.last_element = Value::Number(result.into());
            ws.meta.last_rng_number = result;
        } else {
            let last_rng = ws.meta.last_rng_number;
            let last_elem_i = ws.meta.last_element.as_i64().unwrap_or(0);
            update_run_stats_i64(&mut ws.run_stats_rng, last_rng, result);
            update_run_stats_i64(&mut ws.run_stats_elements, last_elem_i, result);
            ws.meta.last_rng_number = result;
            ws.meta.last_element = Value::Number(result.into());
        }
    }

    fn process_random_weighted(&mut self, entry: &Value, variant: &str, context: &str, range: i64) {
        let element = match entry["element"].as_str() {
            Some(e) => e.to_string(),
            None => return,
        };
        let result = entry["result"].as_i64().unwrap_or(0);
        let elements: Vec<Value> = entry["elements"].as_array().cloned().unwrap_or_default();
        let weights: Vec<Value> = entry["weights"].as_array().cloned().unwrap_or_default();

        let hash_text = format!(
            "randomWeighted{}{}{}{}{}",
            variant, context, range,
            serde_json::to_string(&elements).unwrap_or_default(),
            serde_json::to_string(&weights).unwrap_or_default()
        );
        let hash = md5_hex(&hash_text);

        let is_new = !self.variants[variant][context].contains_key(&hash);
        if is_new {
            {
                let hit_table: IndexMap<String, i64> = elements
                    .iter()
                    .filter_map(|e| e.as_str().map(|s| (s.to_string(), 0i64)))
                    .collect();
                self.variants
                    .get_mut(variant).unwrap()
                    .get_mut(context).unwrap()
                    .insert(hash.clone(), WeightSet {
                        type_: "randomWeighted".to_string(),
                        variant: variant.to_string(),
                        context: context.to_string(),
                        range,
                        chance: None,
                        elements: Some(elements.clone()),
                        weights: Some(weights.clone()),
                        hit_table,
                        run_stats_rng: RunStats { up: 0, down: 0, same: 0 },
                        run_stats_elements: RunStats { up: 0, down: 0, same: 0 },
                        meta: Meta {
                            hash_text,
                            hash: hash.clone(),
                            first: true,
                            last_element: Value::String(String::new()),
                            last_rng_number: 0,
                            number_of_calls: 0,
                        },
                    });
            }
            self.register_weight_set(variant, context);
        }

        let ws = self.variants
            .get_mut(variant).unwrap()
            .get_mut(context).unwrap()
            .get_mut(&hash).unwrap();
        ws.meta.number_of_calls += 1;
        *ws.hit_table.entry(element.clone()).or_insert(0) += 1;

        if ws.meta.first {
            ws.meta.first = false;
            ws.meta.last_element = Value::String(element.clone());
            ws.meta.last_rng_number = result;
        } else {
            let last_rng = ws.meta.last_rng_number;
            let last_elem = ws.meta.last_element.as_str().unwrap_or("").to_string();
            update_run_stats_i64(&mut ws.run_stats_rng, last_rng, result);
            let last_idx = elem_index(&elements, &last_elem);
            let curr_idx = elem_index(&elements, &element);
            update_run_stats_usize(&mut ws.run_stats_elements, last_idx, curr_idx);
            ws.meta.last_rng_number = result;
            ws.meta.last_element = Value::String(element);
        }
    }

    fn process_has_chance(&mut self, entry: &Value, variant: &str, context: &str, range: i64) {
        let chance = entry["chance"].as_f64().unwrap_or(0.0);
        let element = match entry["element"].as_str() {
            Some(e) => e.to_string(),
            None => return,
        };
        let result = entry["result"].as_i64().unwrap_or(0);
        let hash_text = format!("hasChance{}{}{}{}", variant, context, range, chance);
        let hash = md5_hex(&hash_text);

        let is_new = !self.variants[variant][context].contains_key(&hash);
        if is_new {
            {
                let mut hit_table: IndexMap<String, i64> = IndexMap::new();
                hit_table.insert("True".to_string(), 0);
                hit_table.insert("False".to_string(), 0);
                self.variants
                    .get_mut(variant).unwrap()
                    .get_mut(context).unwrap()
                    .insert(hash.clone(), WeightSet {
                        type_: "hasChance".to_string(),
                        variant: variant.to_string(),
                        context: context.to_string(),
                        range,
                        chance: Some(chance),
                        elements: None,
                        weights: None,
                        hit_table,
                        run_stats_rng: RunStats { up: 0, down: 0, same: 0 },
                        run_stats_elements: RunStats { up: 0, down: 0, same: 0 },
                        meta: Meta {
                            hash_text,
                            hash: hash.clone(),
                            first: true,
                            last_element: Value::String(String::new()),
                            last_rng_number: 0,
                            number_of_calls: 0,
                        },
                    });
            }
            self.register_weight_set(variant, context);
        }

        let ws = self.variants
            .get_mut(variant).unwrap()
            .get_mut(context).unwrap()
            .get_mut(&hash).unwrap();
        ws.meta.number_of_calls += 1;
        *ws.hit_table.entry(element.clone()).or_insert(0) += 1;

        if ws.meta.first {
            ws.meta.first = false;
            ws.meta.last_element = Value::String(element.clone());
            ws.meta.last_rng_number = result;
        } else {
            let last_rng = ws.meta.last_rng_number;
            let last_elem = ws.meta.last_element.as_str().unwrap_or("").to_string();
            update_run_stats_i64(&mut ws.run_stats_rng, last_rng, result);
            let bool_elems = ["True", "False"];
            let last_idx = bool_elems.iter().position(|&e| e == last_elem).unwrap_or(0);
            let curr_idx = bool_elems.iter().position(|e| *e == element).unwrap_or(0);
            update_run_stats_usize(&mut ws.run_stats_elements, last_idx, curr_idx);
            ws.meta.last_rng_number = result;
            ws.meta.last_element = Value::String(element);
        }
    }

    /// Update stats (weight set counters). Called after inserting a new WeightSet.
    fn register_weight_set(&mut self, variant: &str, context: &str) {
        self.stats.unique_weight_sets += 1;
        let vs = self.stats.stats_per_variant.get_mut(variant).unwrap();
        vs.unique_weight_sets += 1;
        *vs.weight_sets_per_context.entry(context.to_string()).or_insert(0) += 1;
    }

    /// Consume self and serialize the report to JSON.
    fn save_json(self, path: &str) {
        let report = Report {
            rng_distribution: Distribution { variants: self.variants },
            stats: self.stats,
        };
        let json = serde_json::to_string_pretty(&report).expect("Serialization failed");
        fs::write(path, json).expect("Cannot write JSON file");
    }

    fn extract_rng_data(extra_parameters: &str) -> Option<Value> {
        let lines: Vec<&str> = extra_parameters.splitn(3, '\n').collect();
        if lines.len() < 2 {
            return None;
        }
        let wrapped = lines[1];
        let len = wrapped.len();
        if len < 11 {
            return None;
        }
        let b64 = &wrapped[9..len - 2];
        let compressed = base64::engine::general_purpose::STANDARD
            .decode(b64)
            .ok()?;
        let mut decoder = DeflateDecoder::new(compressed.as_slice());
        let mut json_bytes = Vec::new();
        decoder.read_to_end(&mut json_bytes).ok()?;
        let json_str = std::str::from_utf8(&json_bytes).ok()?;
        serde_json::from_str(json_str).ok()
    }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

fn md5_hex(text: &str) -> String {
    let mut hasher = Md5::new();
    hasher.update(text.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn elem_index(elements: &[Value], target: &str) -> usize {
    elements
        .iter()
        .position(|e| e.as_str() == Some(target))
        .unwrap_or(0)
}

fn update_run_stats_i64(stats: &mut RunStats, last: i64, current: i64) {
    match last.cmp(&current) {
        std::cmp::Ordering::Equal => stats.same += 1,
        std::cmp::Ordering::Less => stats.up += 1,
        std::cmp::Ordering::Greater => stats.down += 1,
    }
}

fn update_run_stats_usize(stats: &mut RunStats, last: usize, current: usize) {
    match last.cmp(&current) {
        std::cmp::Ordering::Equal => stats.same += 1,
        std::cmp::Ordering::Less => stats.up += 1,
        std::cmp::Ordering::Greater => stats.down += 1,
    }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        eprintln!("Usage: {} <input.csv> <output.json>", args[0]);
        std::process::exit(1);
    }
    let mut processor = RngStatsProcessor::new();
    processor.process_file(&args[1]);
    processor.save_json(&args[2]);
}
