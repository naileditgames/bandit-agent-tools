# bandit-agent-tools

Agent tooling for NaileditGames Bandit slot-game certification workflows — simulations, RNG distribution reports, and Netherlands certification file packages.

## Contents

- `tools/rng-distribution-report/` — Python scripts (CSV → JSON → Excel) for RNG distribution reports
- `tools/rng-distribution-report-rust/` — Rust binaries; preferred over Python for large CSV files (lower memory)
- `.cursor/skills/` — Agent skills for GitLab, Jira, game servers, simulations, and cert file generation
- `tmp/` — Cloned game repos and simulation results (not committed)

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| [.NET SDK](https://dotnet.microsoft.com/download/dotnet/6.0) | 6.0 | Required to build and run Bandit game servers |
| [Rust / Cargo](https://rustup.rs) | stable | Required to build the Rust RNG distribution report binaries |
| [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) | latest | Required to upload simulation results to GCS (`gsutil`) |

---

## Environment Setup

### Cursor Agent

When running via Cursor Agent, all required environment variables are configured in the **Cursor Cloud Agent Settings** page — no `.env` file is needed. The `.env` file is not committed to git and is not present in the agent environment.

### Local Development

All credentials are read from a `.env` file in the project root. Copy the example and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set each variable:

```env
# Games Global GitLab (gametechgit.gamesglobal.com)
GG_GITLAB_USERNAME=           # your GitLab username
GG_GITLAB_TOKEN=              # personal access token with read_repository scope

# Google Cloud Platform — service account for GCS uploads
# Base64-encoded JSON key: base64 -i key.json | tr -d '\n'
GCP_SERVICE_ACCOUNT_KEY_B64=

# Jira (NaileditGames instance)
JIRA_EMAIL=                   # your Atlassian account email
JIRA_TOKEN=                   # Atlassian API token (account.atlassian.com → Security → API tokens)
```

#### Getting each credential

| Variable | Where to get it |
|---|---|
| `GG_GITLAB_USERNAME` | Your username on `gametechgit.gamesglobal.com` |
| `GG_GITLAB_TOKEN` | GitLab → User Settings → Access Tokens → create token with `read_repository` + `api` scopes |
| `GCP_SERVICE_ACCOUNT_KEY_B64` | GCP Console → IAM → Service Accounts → key JSON, then `base64 -i key.json \| tr -d '\n'` |
| `JIRA_EMAIL` | Your email on `naileditgames.atlassian.net` |
| `JIRA_TOKEN` | [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens) |

---

## Tools

### RNG Distribution Report

Generates the RNG distribution Excel deliverable from a simulation CSV extract.

**Rust binaries (preferred):**

```bash
# Build once
cd tools/rng-distribution-report-rust
cargo build --release

# Generate JSON report from CSV
tools/rng-distribution-report-rust/target/release/generate_json_report \
  tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.csv \
  tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.json

# Generate Excel report from JSON
tools/rng-distribution-report-rust/target/release/generate_excel_report \
  tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.json \
  tmp/results/<GameName><Variant>_<strategy>/<mid>-<variant>.xlsx
```

**Python scripts** (requires Python 3.9+):

```bash
cd tools/rng-distribution-report
pip install -r requirements.txt
python generate_json_report.py
python generate_excel_report.py
```

---

## Agent Skills

| Skill | Description |
|---|---|
| `task-bandit-simulations` | Run RTP simulations, generate CSV data extracts, produce RNG distribution reports, upload to GCS, attach to Jira |
| `task-netherlands-files` | Clone a game repo, generate Netherlands cert Files package (JSON configs + C# math + description.xlsx), zip, and attach to Jira |
| `netherlands-cert-files` | Core logic for selecting result-affecting math files and building the `NetherlandsFiles/` folder |
| `bandit-server` | Setup and build a Bandit game server repo (NuGet config, FakeRng, dotnet build) |
| `nailedit-game-servers` | Reference for development vs production game server types |
| `gamesglobal-gitlab` | Search, list, and clone repos from `gametechgit.gamesglobal.com` |
| `jira-nailedit` | Read issues, post comments, upload and download attachments on `naileditgames.atlassian.net` |

---

## GCS Simulation Results

- **Project:** `gameslobby`
- **Bucket:** `bandit-simulation-results`
- **Path pattern:** `gs://bandit-simulation-results/<GameName>/<YYYY-MM-DD_HH-MM-SS>/<GameName><Variant>_<strategy>/`
