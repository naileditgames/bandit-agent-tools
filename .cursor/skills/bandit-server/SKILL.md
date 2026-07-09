---
name: bandit-server
description: Setup and build GamesGlobal Bandit slot game server repositories — cloning, NuGet configuration, FakeRng setup for macOS/Linux, building, running simulations, generating RNG distribution reports, and uploading results to GCP. Use when setting up a Bandit game server project for the first time, running RTP simulations, generating RNG certification reports, or uploading simulation results to the GCS bucket.
---

# Bandit Game Server

## Table of Contents

- [Repository Structure](#repository-structure)
- [Setup Before Building](#setup-before-building)
  - [1. Create Directory.Build.props](#1-create-directorybuildprops)
  - [2. Configure NuGet credentials](#2-configure-nuget-credentials)
  - [3. Fix RNG for macOS/Linux](#3-fix-rng-for-macoslinux)
  - [4. Build](#4-build)
- [Simulations](#simulations)
  - [Simulation Parameters](#simulation-parameters)
  - [Navigating the TUI (macOS)](#navigating-the-tui-macos)
  - [Behaviours](#behaviours)
  - [Process: RTP Simulation](#process-rtp-simulation)
  - [Process: Data Extract (CSV for RNG Certification)](#process-data-extract-csv-for-rng-certification)
- [RNG Distribution Report](#rng-distribution-report)
  - [Output organisation](#output-organisation)
  - [Setup](#setup)
  - [Step 1: Generate JSON report](#step-1-generate-json-report)
  - [Step 2: Generate Excel report](#step-2-generate-excel-report)
- [GCP Upload](#gcp-upload)
  - [Setup](#setup-1)
  - [Upload](#upload)

---

Bandit is the C# game server framework provided by GamesGlobal. Each game has its own repository under `naileditgames` on GamesGlobal GitLab. See the `gamesglobal-gitlab` skill for cloning.

## Repository Structure

```
src/
├── <GameName>.sln
├── <GameName>/                    # Main game math service
│   ├── Config/
│   │   ├── V90/                   # RTP variant 90%
│   │   ├── V92/                   # RTP variant 92%
│   │   ├── V94/                   # RTP variant 94%
│   │   └── V96/                   # RTP variant 96%
│   │       ├── GameProperties.json
│   │       ├── Install.xml        # Contains ModuleId for this variant
│   │       ├── EmptyReels.xml
│   │       └── SkinMapping.xml
│   ├── Properties/
│   │   └── launchSettings.json    # Run profiles including Simulation
│   └── rng.config.json
├── <GameName>.Tests/
└── <GameName>.Tools/
```

## Setup Before Building

### 1. Create Directory.Build.props

Before building, create `src/Directory.Build.props` specifying the RTP variant and Module ID:

```xml
<Project>
  <PropertyGroup>
    <GameVariant>V96</GameVariant>
    <GameMid>104800</GameMid>
  </PropertyGroup>
</Project>
```

Find the correct `GameMid` for each variant from `Config/<Variant>/Install.xml`:

```bash
for v in V90 V92 V94 V96; do
  mid=$(grep "ModuleId" src/<GameName>/Config/$v/Install.xml | grep -o '[0-9]*')
  echo "$v -> $mid"
done
```

### 2. Configure NuGet credentials

The game depends on private NuGet packages hosted on GamesGlobal GitLab. Create `src/nuget.config`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
    <add key="GameTechGit" value="https://gametechgit.gamesglobal.com/api/v4/projects/229/packages/nuget/index.json" />
    <add key="BanditExternalFeed" value="https://gametechgit.gamesglobal.com/api/v4/projects/802/packages/nuget/index.json" />
  </packageSources>
  <packageSourceCredentials>
    <GameTechGit>
      <add key="Username" value="${GG_GITLAB_USERNAME}" />
      <add key="ClearTextPassword" value="${GG_GITLAB_TOKEN}" />
    </GameTechGit>
    <BanditExternalFeed>
      <add key="Username" value="${GG_GITLAB_USERNAME}" />
      <add key="ClearTextPassword" value="${GG_GITLAB_TOKEN}" />
    </BanditExternalFeed>
  </packageSourceCredentials>
</configuration>
```

Use credentials from `.env` (`GG_GITLAB_USERNAME`, `GG_GITLAB_TOKEN`).

### 3. Fix RNG for macOS/Linux

The default `rng.config.json` uses `MGS.Random.Pool.dll` which depends on Windows API (`QueryPerformanceCounter`) and crashes on macOS/Linux. Skip this step on Windows.

Edit `src/<GameName>/rng.config.json`:

```json
{
  "RngConfig" : {
    "Kind" : "MGS.RNG",
    "Assembly": "HttpGames.FakeRng.dll",
    "Type": "FakeRandomPoolFactory"
  }
}
```

Add the FakeRng package to `<GameName>.csproj` (same version as other CasinoServices packages):

```xml
<PackageReference Include="CasinoServices.Library.HttpGames.FakeRng" Version="5.4.3.8"/>
```

### 4. Build

```bash
cd src
dotnet build <GameName>.sln
```

## Simulations

### Simulation Parameters

| Parameter | Description |
|---|---|
| `-c` | Required — starts in interactive console mode |
| `--csv` | Generates spin-level CSV file (omit if not needed) |
| `--numOfGames` | Number of spins to simulate |
| `--numOfThreads` | Number of parallel threads |
| `--logFrequency` | Write to CSV every N games — keep low (e.g. 5000) to avoid running out of RAM |
| `--logMethod` | `latest` = overwrite file, `append` = append to existing |
| `--logPath` | Output directory for `.txt` summary and `.csv` spin data — use absolute path |
| `--behavioursPath` | Directory containing behaviour JSON files — use absolute path |

> **Always add `--no-launch-profile`** to the `dotnet run` command. Without it, `dotnet run` picks up the `Simulation` profile from `launchSettings.json` and appends its own arguments (including a conflicting `--behavioursPath=../../`) to yours, causing the app to fail.

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

**Standard flow (no behaviours):**
- `1` → Simulation → `1` → Start → wait for COMPLETE

**With behaviours:**
- `4` → Configure Session → `2` → Behaviours → `1` → Activate → Esc → Esc → `1` → Simulation → `1` → Start

Read terminal state at any time:
```bash
osascript -e 'tell application "Terminal" to get contents of window 1'
```

### Behaviours

Behaviour JSON files in `--behavioursPath` override session parameters (bet size, game mode, etc.). They are `DISABLED` by default — must be activated via Configure Session → Behaviours → Activate.

Example `MaxBetStrategy.json`:

```json
[
  {
    "ModuleId": 104800,
    "ClientId": 50300,
    "ProductId": 0,
    "Username": "",
    "BehaviourName": "Core.Slots.StockSpinStrategy",
    "Guid": "f486ee5a-ee86-4756-99d8-2a97db9a4470",
    "Options": {
      "NumCoins$0": "Max",
      "CoinSize$0": "Max",
      "BetMultiplier$0": "Max"
    }
  }
]
```

The `ModuleId` in the file does not need to exactly match the running game's MID. Save each behaviour run to its own output directory (e.g. `results/V94/maxbet/`).

### Process: RTP Simulation

Use to verify a game variant's RTP is within the expected range. If no variant is specified, run 1M spins for **V96** only.

1. Clone the game repository into `tmp/` (see `gamesglobal-gitlab` skill):
   ```bash
   source .env
   git clone "https://${GG_GITLAB_USERNAME}:${GG_GITLAB_TOKEN}@gametechgit.gamesglobal.com/naileditgames/<repo>.git" tmp/<repo>
   ```
2. Complete all setup steps above (Directory.Build.props, nuget.config, FakeRng, build)
3. Create output directory: `mkdir -p tmp/results/<GameName><Variant>_default/`
4. Launch — **without** `--csv` (not needed for RTP verification):
   ```bash
   cd tmp/<repo>/src/<GameName>
   dotnet run --no-build -- -c \
     --numOfGames=1000000 \
     --numOfThreads=8 \
     --logFrequency=5000 \
     --logMethod=latest \
     --logPath=/absolute/path/to/tmp/results/<GameName><Variant>_default/
   ```
5. Navigate the TUI: press `1` (Simulation) → `1` (Start)
6. Wait for `COMPLETE` — verify Actual RTP is within the Target RTP range shown on screen

### Process: Data Extract (CSV for RNG Certification)

Use to generate spin-level data required for game server certification. Same as RTP Simulation with these differences:

- Add `--csv` to generate the CSV file
- Keep `--logFrequency` low (e.g. `5000`) — CSV is flushed to disk every N games; too high risks running out of RAM
- **Always save to a unique output directory** per variant and strategy — `.txt` gets overwritten and new CSV data is appended to any existing file if the directory is reused

```bash
cd src/<GameName>
dotnet run --no-build -- -c \
  --csv \
  --numOfGames=1000000 \
  --numOfThreads=8 \
  --logFrequency=5000 \
  --logMethod=latest \
  --logPath=/absolute/path/to/results/<Variant>/default/ \
  --behavioursPath=/absolute/path/to/behaviours/
```

Output: `<ModuleId>-<variant>.csv` (1M spins ≈ 1 GB) and `<ModuleId>-<variant>.txt`.

## RNG Distribution Report

Tool location: `tools/rng-distribution-report/`

Generates an Excel RNG distribution report for certification purposes from a data extract CSV. Two-step process: CSV → JSON → Excel.

### Output organisation

When generating reports for multiple variants or strategies, keep results in separate directories named after the game variant and behaviour strategy:

```
results/
├── StarsBonanza3x3V90_default/
│   ├── 104928-v90.csv
│   ├── 104928-v90.txt
│   ├── 104928-v90.json
│   └── 104928-v90.xlsx
├── StarsBonanza3x3V90_maxbet/
│   ├── 104928-v90.csv
│   ├── 104928-v90.txt
│   ├── 104928-v90.json
│   └── 104928-v90.xlsx
└── StarsBonanza3x3V96_default/
    ├── 104800-v96.csv
    ├── 104800-v96.txt
    ├── 104800-v96.json
    └── 104800-v96.xlsx
```

### Setup

```bash
cd tools/rng-distribution-report
pip install -r requirements.txt
```

Dependencies: `openpyxl`

### Step 1: Generate JSON report

Processes the data extract CSV spin by spin, decoding base64+deflate RNG data from each row. For 1M spins this takes a few minutes.

```bash
python tools/rng-distribution-report/generate_json_report.py \
  <input.csv> \
  <output.json>
```

Example:
```bash
python tools/rng-distribution-report/generate_json_report.py \
  tmp/results/V94/default/104801-v94.csv \
  tmp/results/V94/default/104801-v94.json
```

### Step 2: Generate Excel report

```bash
python tools/rng-distribution-report/generate_excel_report.py \
  <input.json> \
  <output.xlsx>
```

Example:
```bash
python tools/rng-distribution-report/generate_excel_report.py \
  tmp/results/V94/default/104801-v94.json \
  tmp/results/V94/default/104801-v94.xlsx
```

## GCP Upload

**GCP details:**
- Project: `gameslobby`
- Bucket: `bandit-simulation-results`
- Service account: `bandit-simulation-tool-job@gameslobby.iam.gserviceaccount.com` (role: `legacyBucketWriter`)

### Bucket structure

All simulations from one session share a single timestamped folder. Each simulation variant/strategy gets its own subdirectory within it.

```
bandit-simulation-results/
└── <GameName>/
    └── <YYYY-MM-DD_HH-MM-SS>/          ← one folder per session
        ├── <GameName><Variant>_default/
        │   ├── <mid>-<variant>.csv
        │   ├── <mid>-<variant>.txt
        │   ├── <mid>-<variant>.json
        │   └── <mid>-<variant>.xlsx
        ├── <GameName><Variant>_maxbet/
        └── <GameName><Variant2>_default/
```

Example for RobinBanksBonanza:

```
bandit-simulation-results/
└── RobinBanksBonanza/
    └── 2026-07-08_21-46-55/
        ├── RobinBanksBonanzaV96_default/
        │   ├── 105049-v96.csv
        │   ├── 105049-v96.txt
        │   ├── 105049-v96.json
        │   └── 105049-v96.xlsx
        ├── RobinBanksBonanzaV94_default/
        └── RobinBanksBonanzaV92_default/
```

### Upload via MCP

Use the `gcloud` MCP server (configured in `.cursor/mcp.json`) to run `gsutil` commands directly. Generate a session timestamp once and reuse it for all variants:

```bash
SESSION_TS=$(date -u '+%Y-%m-%d_%H-%M-%S')

gsutil -m cp -r tmp/results/RobinBanksBonanzaV96_default \
  gs://bandit-simulation-results/RobinBanksBonanza/$SESSION_TS/

gsutil -m cp -r tmp/results/RobinBanksBonanzaV94_default \
  gs://bandit-simulation-results/RobinBanksBonanza/$SESSION_TS/

gsutil -m cp -r tmp/results/RobinBanksBonanzaV92_default \
  gs://bandit-simulation-results/RobinBanksBonanza/$SESSION_TS/
```

### MCP servers

Two GCP MCP servers are configured in `.cursor/mcp.json`:

- **`gcloud`** (`@google-cloud/gcloud-mcp`) — executes any `gcloud`/`gsutil` command; use this for uploads
- **`google-cloud-storage`** — Google's managed Cloud Storage MCP (`https://storage.googleapis.com/storage/mcp`); use for browsing bucket contents, reading text files, checking object metadata
