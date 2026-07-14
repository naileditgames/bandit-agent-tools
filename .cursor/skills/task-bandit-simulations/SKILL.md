---
name: task-bandit-simulations
description: Run Bandit game server RTP simulations, generate spin-level CSV data extracts for RNG certification, produce RNG distribution reports, upload results to GCS, and attach summaries to Jira tickets. Use when running simulations, verifying RTP, generating certification data, creating RNG distribution Excel reports, uploading simulation results to the bandit-simulation-results bucket, or executing a JIRA-triggered simulation task.
---

# Bandit Simulations Task

End-to-end workflow for running Bandit simulations and producing certification deliverables.

**Prerequisites:** Complete setup and build first — see the `bandit-server` skill.

**Reference:** Simulation CLI parameters and behaviour JSON — see `bandit-server` (Simulation Parameters, Behaviours).

## Task Progress

```
- [ ] Strategies determined (see Strategy selection below)
- [ ] Game repo cloned and built (bandit-server skill)
- [ ] Output directories created (one per variant/strategy)
- [ ] Simulation run(s) completed — one strategy activated per run
- [ ] RTP verified (if applicable)
- [ ] RNG distribution reports generated (if CSV extract)
- [ ] Results uploaded to GCS (if requested)
- [ ] Results attached to Jira + summary comment (Jira-triggered tasks only)
```

---

## Strategy selection

Run **one strategy per simulation** — strategies are chosen and activated in the TUI (Configure Session → Behaviours → Activate). `--behavioursPath` may contain multiple JSON files; what matters is that **only one is activated** for each run.

For convenience, keep a single strategy file in `--behavioursPath` per run so there is nothing else to accidentally activate. This is recommended, not required.

### JIRA-triggered tasks

If the task comes from JIRA (see `jira-nailedit` skill), fetch the issue and check attachments for behaviour JSON files before running anything.

1. Read the issue summary and description
2. List attachments — look for `.json` behaviour/strategy files
3. Decide which runs to execute:

| Situation | Action |
|---|---|
| No strategy attachments | Run **without strategy** (omit `--behavioursPath`) |
| Attachments present, description **names specific strategies** | Run only those named strategies — one simulation per strategy |
| Attachments present, description **does not specify** which to run | Run **without strategy** (default) — do not assume all attachments |

Download strategy files from JIRA into a local `--behavioursPath` directory. Run one simulation per selected strategy and activate **only that strategy** in the TUI before starting.

Name output directories after the strategy (e.g. `_default`, `_maxbet`) — see [Output directories](#output-directories).

### Non-JIRA tasks

Follow the same one-strategy-per-run rule. If the user specifies strategy files, run only those explicitly requested. If none are specified, run without strategy.

---

## Process: RTP Simulation

Use to verify a game variant's RTP is within the expected range. If no variant is specified, run 1M spins for **V96** only.

1. Determine strategies — see [Strategy selection](#strategy-selection)
2. Clone the game repository into `tmp/` (see `gamesglobal-gitlab` skill):
   ```bash
   source .env
   git clone "https://${GG_GITLAB_USERNAME}:${GG_GITLAB_TOKEN}@gametechgit.gamesglobal.com/naileditgames/<repo>.git" tmp/<repo>
   ```
3. Complete all setup steps from `bandit-server` (Directory.Build.props, nuget.config, FakeRng, build)
4. Create output directory: `mkdir -p tmp/results/<GameName><Variant>_default/` (or `_<strategy>/` if running a strategy)
5. Launch — **without** `--csv` (not needed for RTP verification). Omit `--behavioursPath` when running without strategy:
   ```bash
   cd tmp/<repo>/src/<GameName>
   dotnet run --no-build --no-launch-profile -- -c \
     --numOfGames=1000000 \
     --numOfThreads=8 \
     --logFrequency=5000 \
     --logMethod=latest \
     --logPath=/absolute/path/to/tmp/results/<GameName><Variant>_default/
   ```
6. Navigate the TUI — see [Tips](#tips). Without strategy: Simulation → Start. With strategy: activate **only the intended strategy**, then Simulation → Start.
7. Wait for `COMPLETE` — verify Actual RTP is within the Target RTP range shown on screen
8. Repeat steps 4–7 for each additional strategy

## Process: Data Extract (CSV for RNG Certification)

Use to generate spin-level data required for game server certification. Same as RTP Simulation but add `--csv` and optionally `--behavioursPath`.

1. Determine strategies — see [Strategy selection](#strategy-selection)
2. Complete setup and build (`bandit-server` skill)
3. Create a **unique** output directory per variant and strategy: `mkdir -p tmp/results/<GameName><Variant>_<strategy>/`
4. Launch with `--behavioursPath` when running a strategy (omit when running without):
   ```bash
   cd src/<GameName>
   dotnet run --no-build --no-launch-profile -- -c \
     --csv \
     --numOfGames=1000000 \
     --numOfThreads=8 \
     --logFrequency=5000 \
     --logMethod=latest \
     --logPath=/absolute/path/to/results/<GameName><Variant>_<strategy>/ \
     --behavioursPath=/absolute/path/to/behaviours/   # omit when running without strategy
   ```
5. Navigate the TUI — see [Tips](#tips). Without strategy: Simulation → Start. With strategy: activate **only the intended strategy**, then Simulation → Start.
6. Confirm output: `<ModuleId>-<variant>.csv` (1M spins ≈ 1 GB) and `<ModuleId>-<variant>.txt`
7. Repeat steps 3–6 for each additional strategy

## Process: RNG Distribution Report

Tool location: `tools/rng-distribution-report/`. Two-step process: CSV → JSON → Excel.

Use the **Rust binaries** (`rng-report-rs`) — much lower memory usage than the Python scripts.

1. Build the Rust tools (once, requires Rust/Cargo):
   ```bash
   cd tools/rng-distribution-report-rust
   cargo build --release
   ```
   Binaries are placed in `target/release/`.

2. Generate JSON report (1M spins takes a few minutes):
   ```bash
   tools/rng-distribution-report-rust/target/release/generate_json_report \
     tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.csv \
     tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.json
   ```

3. Generate Excel report:
   ```bash
   tools/rng-distribution-report-rust/target/release/generate_excel_report \
     tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.json \
     tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.xlsx
   ```

## Process: GCP Upload

Upload all variant/strategy directories from one session under a shared timestamp folder.

1. Generate a session timestamp once and reuse for all variants:
   ```bash
   SESSION_TS=$(date -u '+%Y-%m-%d_%H-%M-%S')
   ```
2. Upload each result directory via the `gcloud` MCP server:
   ```bash
   gsutil -m cp -r tmp/results/<GameName><Variant>_default \
     gs://bandit-simulation-results/<GameName>/$SESSION_TS/
   ```
3. Repeat for each variant/strategy directory from the session

## Post-completion: Attach results to Jira

**Only when the task was triggered from a Jira ticket** — e.g. the user references a ticket key (`NKIT-676`) or the workflow started from a Jira issue. Skip this step for standalone local runs.

Use the `jira-nailedit` skill for authentication and API calls.

**Files to attach** — upload only:
- `*.txt` — simulation summary (always)
- `*.xlsx` — RNG distribution report (when generated)

**Never attach** `*.csv` or `*.json` — too large or intermediate artifacts.

Then post a comment summarising results — extract Actual RTP and Target Range from each `.txt` file and present as a table. Introduce yourself briefly at the start of the comment.

---

## Tips

### Navigating the TUI (macOS)

The simulation app is an interactive TUI. Use AppleScript `key code` to navigate:

```bash
osascript << 'EOF'
tell application "Terminal" to activate
delay 0.5
tell application "System Events"
  key code 18   # 1
end tell
EOF
```

Key codes: `18` = 1, `19` = 2, `20` = 3, `21` = 4, `53` = Esc

**Standard flow (no behaviours):** `1` → Simulation → `1` → Start → wait for COMPLETE

**With behaviours:** `4` → Configure Session → `2` → Behaviours → select and activate **one** strategy → Esc → Esc → `1` → Simulation → `1` → Start

If multiple JSON files are in `--behavioursPath`, pick only the strategy for this run — do not activate others.

Read terminal state: `osascript -e 'tell application "Terminal" to get contents of window 1'`

### Output directories

Use one directory per variant and strategy (e.g. `StarsBonanza3x3V96_default/`, `StarsBonanza3x3V90_maxbet/`). Reusing a directory overwrites `.txt` and appends to any existing CSV.

Expected files per directory after full pipeline:

```
results/<GameName><Variant>_<strategy>/
├── <mid>-<variant>.csv
├── <mid>-<variant>.txt
├── <mid>-<variant>.json
└── <mid>-<variant>.xlsx
```

### GCS bucket layout

- Project: `gameslobby`
- Bucket: `bandit-simulation-results`
- Path: `gs://bandit-simulation-results/<GameName>/<YYYY-MM-DD_HH-MM-SS>/<GameName><Variant>_<strategy>/`

Use **`gcloud`** MCP for uploads (`gsutil`), **`google-cloud-storage`** MCP for browsing and reading objects.
