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

### Install and authenticate gsutil (cloud agents)

`gsutil` is not pre-installed on cloud agent VMs. Install the Google Cloud SDK and authenticate using the `GCP_SERVICE_ACCOUNT_KEY_B64` secret (a base64-encoded service account JSON key):

```bash
curl -sSL https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
  | sudo tar -xz -C /usr/local/
sudo ln -sf /usr/local/google-cloud-sdk/bin/gsutil /usr/local/bin/gsutil
sudo ln -sf /usr/local/google-cloud-sdk/bin/gcloud /usr/local/bin/gcloud

echo "$GCP_SERVICE_ACCOUNT_KEY_B64" | base64 -d > /tmp/gcp-sa-key.json
gcloud auth activate-service-account --key-file=/tmp/gcp-sa-key.json
gcloud config set project gameslobby

# Verify access
gsutil ls gs://bandit-simulation-results/
```

On macOS with the `gcloud` MCP server available, use that instead.

### Upload

1. Generate a session timestamp once and reuse for all variants:
   ```bash
   SESSION_TS=$(date -u '+%Y-%m-%d_%H-%M-%S')
   ```
2. Upload each result directory:
   ```bash
   gsutil -m cp -r tmp/results/<GameName><Variant>_default \
     gs://bandit-simulation-results/<GameName>/$SESSION_TS/
   ```
3. Repeat for each variant/strategy directory from the session

## Running many simulations sequentially (Linux / cloud agents)

When running a large batch of simulations (e.g. 4 variants × 3 strategies), use a tmux-backed script so the work survives any connection drop. Run all simulations one at a time in a loop, navigating the TUI with `tmux send-keys` for each.

See [Navigating the TUI (Linux)](#navigating-the-tui-linux) below for the key sequence.

Template script structure:

```bash
#!/usr/bin/env bash
run_simulation() {
  local variant="$1" strategy="$2" mid="$3"
  local session="sim-${variant,,}-${strategy,,}"
  session="${session:0:30}"   # tmux session names are capped at ~30 chars

  tmux -f /exec-daemon/tmux.portal.conf new-session -d -s "$session" -- bash -l

  tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$session" \
    "dotnet /path/to/builds/$variant/$mid.dll -c \
     --numOfGames=10000000 --numOfThreads=8 \
     --logFrequency=5000 --logMethod=latest \
     --logPath=/path/to/results/${GameName}${variant}_${strategy}/ \
     --behavioursPath=/path/to/behaviours/run_${variant}_${strategy}/" Enter

  # Wait for TUI main menu
  until tmux -f /exec-daemon/tmux.portal.conf capture-pane -t "$session" -p | grep -q "Configure session"; do
    sleep 2
  done

  # Activate behaviour and start
  sleep 1
  tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$session" "4" ""   # Configure session
  sleep 1; tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$session" "2" ""   # Behaviours
  sleep 1; tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$session" "1" ""   # Activate Behaviours
  sleep 1; tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$session" "Escape" ""
  sleep 1; tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$session" "Escape" ""
  sleep 1; tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$session" "1" ""   # Simulation
  sleep 1; tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$session" "1" ""   # Start

  # Poll for COMPLETE
  until tmux -f /exec-daemon/tmux.portal.conf capture-pane -t "$session" -p | grep -q "COMPLETE"; do
    sleep 30
  done

  tmux -f /exec-daemon/tmux.portal.conf kill-session -t "$session"
}

# Run sequentially
for variant in V96 V94 V92 V90; do
  for strategy in AlwaysBaseBetMinStrategy AlwaysBonusBetMinStrategy AllPermutationsStrategy; do
    run_simulation "$variant" "$strategy" "${MIDS[$variant]}"
  done
done
```

Launch the script inside its own persistent tmux session:

```bash
SESSION="chr2-simulations"
tmux -f /exec-daemon/tmux.portal.conf new-session -d -s "$SESSION" -- bash -l
tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$SESSION" "bash /path/to/run_simulations.sh" Enter
```

## Post-completion: Attach results to Jira

**Only when the task was triggered from a Jira ticket** — e.g. the user references a ticket key (`NKIT-676`) or the workflow started from a Jira issue. Skip this step for standalone local runs.

Use the `jira-nailedit` skill for authentication and API calls.

**Create a single zip** containing all result files across all variant/strategy directories, then attach that one zip. Include only:
- `*.txt` — simulation summary (always)
- `*.xlsx` — RNG distribution report (when generated)
- A combined `.zip` of all result TXT files (useful when there are many simulations)

**Never include** `*.csv` or `*.json` — too large or intermediate artifacts.

```bash
# Collect eligible files and zip them (run from the results root)
find tmp/results -name "*.txt" -o -name "*.xlsx" | \
  zip -j tmp/<GameName>_simulation_results.zip -@
```

Attach `tmp/<GameName>_simulation_results.zip` as a **single attachment** to the Jira ticket.

When creating the zip, rename TXT files to be descriptive (include variant and strategy in the filename) since all result files are named `<mid>-<variant>.txt` and would collide in a flat zip:

```bash
mkdir -p zip_staging
for v in V96 V94 V92 V90; do
  for s in AlwaysBaseBetMinStrategy AlwaysBonusBetMinStrategy AllPermutationsStrategy; do
    cp results/<GameName>${v}_${s}/*.txt "zip_staging/<GameName>${v}_${s}.txt"
  done
done
cd zip_staging && zip ../<GameName>_simulation_results.zip *.txt
```

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

**With behaviours:** `4` → Configure Session → `2` → Behaviours → `1` → Activate Behaviours → Esc → Esc → `1` → Simulation → `1` → Start

Read terminal state: `osascript -e 'tell application "Terminal" to get contents of window 1'`

### Navigating the TUI (Linux)

On Linux, use `tmux send-keys` to drive the TUI. The key sequence is identical to macOS — only the mechanism differs:

```bash
SESSION="my-sim-session"

# Send a single character key
tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$SESSION" "4" ""

# Send Escape
tmux -f /exec-daemon/tmux.portal.conf send-keys -t "$SESSION" "Escape" ""

# Read the current pane content
tmux -f /exec-daemon/tmux.portal.conf capture-pane -t "$SESSION" -p
```

**Full key sequence with behaviours:**
1. Wait until pane contains `Configure session` (main menu loaded)
2. Send `4` — Configure session
3. Send `2` — Behaviours
4. Send `1` — Activate Behaviours (activates **all** files in `--behavioursPath`)
5. Send `Escape` — back to Configure session
6. Send `Escape` — back to main menu
7. Send `1` — Simulation
8. Send `1` — Start
9. Poll pane for `COMPLETE`

Add a `sleep 1` between each key send to allow the TUI to update.

**Standard flow (no behaviours):** skip steps 2–6 above; at main menu send `1` then `1` to start directly.

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

Use the `gsutil` CLI for uploads (install via Google Cloud SDK on cloud agents — see [GCP Upload](#process-gcp-upload) above).
