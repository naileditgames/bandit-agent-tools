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

1. Install dependencies (once):
   ```bash
   cd tools/rng-distribution-report
   pip install -r requirements.txt
   ```
2. Generate JSON report (1M spins takes a few minutes):
   ```bash
   python tools/rng-distribution-report/generate_json_report.py \
     tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.csv \
     tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.json
   ```
3. Generate Excel report:
   ```bash
   python tools/rng-distribution-report/generate_excel_report.py \
     tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.json \
     tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.xlsx
   ```

## Process: GCP Upload

Upload all variant/strategy directories from one session under a shared timestamp folder.

1. Generate a session timestamp once and reuse for all variants:
   ```bash
   SESSION_TS=$(date -u '+%Y-%m-%d_%H-%M-%S')
   ```
2. Upload each result directory via `gsutil` (install gcloud CLI if missing):
   ```bash
   # Install (cloud agents)
   curl -sSL https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz -o /tmp/gcloud.tar.gz
   tar -xzf /tmp/gcloud.tar.gz -C /tmp
   export PATH="/tmp/google-cloud-sdk/bin:$PATH"

   # Auth with service account (decode via python — echo|base64 may fail on multiline values)
   python3 -c "import os,base64; open('/tmp/gcp-sa.json','wb').write(base64.b64decode(os.environ['GCP_SERVICE_ACCOUNT_KEY_B64']))"
   gcloud auth activate-service-account --key-file=/tmp/gcp-sa.json
   gcloud config set project gameslobby

   gsutil -m cp -r tmp/results/<GameName><Variant>_default \
     gs://bandit-simulation-results/<GameName>/$SESSION_TS/
   ```
3. Repeat for each variant/strategy directory from the session

## Post-completion: Attach results to Jira

**Only when the task was triggered from a Jira ticket** — e.g. the user references a ticket key (`NKIT-676`) or the workflow started from a Jira issue. Skip this step for standalone local runs.

Use the `jira-nailedit` skill for authentication and API calls. On cloud agents, run Jira upload/comment scripts inside the **tmux session** where `JIRA_TOKEN` is available — see `jira-nailedit` skill.

**Files to attach** — upload only:
- `*.txt` — simulation summary (always)
- `*.xlsx` — RNG distribution report (when generated)

**Never attach** `*.csv` or `*.json` — too large or intermediate artifacts.

Then post a comment summarising results — extract Actual RTP and Target Range from each `.txt` file and present as a table. Introduce yourself briefly at the start of the comment.

---

## Tips

### Navigating the TUI (Linux / Cloud Agents)

The simulation TUI (Spectre.Console) **requires a large terminal**. A small or `TERM=dumb` shell crashes with:

```
System.InvalidOperationException: Ratio must be equal to or greater than 1
```

Run simulations inside **tmux** with explicit size and term type:

```bash
TMUX=/exec-daemon/tmux
$TMUX -f /exec-daemon/tmux.portal.conf new-session -d -s sim-run -x 200 -y 50
$TMUX -f /exec-daemon/tmux.portal.conf send-keys -t sim-run \
  'export DOTNET_ROOT=$HOME/.dotnet PATH=$PATH:$HOME/.dotnet TERM=xterm-256color; \
   cd /path/to/src/<GameName>; \
   dotnet run --no-build -c Release --no-launch-profile -- -c --csv ...' C-m
```

**Wait for the main menu** (`Configure session` visible) before sending navigation keys. Poll with:

```bash
$TMUX -f /exec-daemon/tmux.portal.conf capture-pane -t sim-run -p | grep 'Configure session'
```

**Standard flow (no behaviours):** `1` → Start → wait for COMPLETE

**With behaviours:** `4` → Configure session → `2` → Behaviours → `1` → Activate Behaviours → `Esc` → `Esc` → `1` → Simulation → `1` → Start

> The Behaviours submenu shows **"1 Activate Behaviours"** — press `1`, not `a`. With a single JSON file in `--behavioursPath`, activation enables that strategy automatically.

Send keys **without** `C-m` (Enter) for menu digits — only the initial `dotnet run` command needs Enter.

**Verify simulation started:** pane shows `Games Played` increasing, or `Games Left` decreasing. If keys were sent before the app loaded, bash will report `-bash: 4: command not found` — kill the session and retry.

**Completion:** wait for `COMPLETE` in pane, or `Games Left    0` plus `.txt` file present in `--logPath`.

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

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Framework: Microsoft.NETCore.App, version 6.0.0` not found | Only .NET 8 SDK installed | Install .NET 6.0 runtimes — see `bandit-server` skill |
| `Ratio must be equal to or greater than 1` | Terminal too small / wrong `TERM` | tmux session `-x 200 -y 50`, `TERM=xterm-256color` |
| `-bash: 4: command not found` after launch | TUI never started; keys hit bash | Install .NET 6 runtime, wait for menu before sending keys |
| Jira 404 / empty `$JIRA_TOKEN` in agent shell | Secrets only in tmux session | Run Jira scripts via tmux `send-keys` — see `jira-nailedit` skill |
| `base64: invalid input` decoding GCP key | Shell `echo` corrupts multiline b64 | `python3 -c "import os,base64; ..."` |
| No output files in `--logPath` | Directory does not exist | `mkdir -p` before launching simulation |
| Simulation stuck at menu, `Games Played 0` | Wrong key sequence or Enter sent with menu keys | Use `4` `2` `1` `Esc` `Esc` `1` `1` without Enter between menu items |

### Smoke test vs production run

Use a **small** `--numOfGames` (e.g. 1000) only to verify TUI navigation and runtime setup after fixing environment issues. Ticket/production runs use the count from the Jira description (commonly 250K or 1M). Always confirm the pane shows the expected game count before walking away.
