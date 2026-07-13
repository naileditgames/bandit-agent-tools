# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
`bandit-agent-tools` is an agent-tooling repo, not a deployable app. It contains:
- `.cursor/skills/` — SOP docs (markdown only, no build) for setting up GamesGlobal Bandit game servers, running RTP simulations, GitLab/GCS/Jira workflows.
- `tools/rng-distribution-report/` — the only runnable code in this repo: a two-step Python pipeline that turns a simulation data-extract CSV into a JSON report and then an Excel (`.xlsx`) RNG distribution report.

### RNG distribution report tool (primary local service)
- Dependencies (`openpyxl`, `et_xmlfile`) are installed by the update script from `tools/rng-distribution-report/requirements.txt`; Python 3.12 is preinstalled.
- Both scripts now take **positional args** `input output` (via argparse):
  - `python3 tools/rng-distribution-report/generate_json_report.py <extract.csv> <report.json>`
  - `python3 tools/rng-distribution-report/generate_excel_report.py <report.json> <report.xlsx>`
  - Note: `tools/rng-distribution-report/readme.md` shows the older no-arg invocation; the argparse form above is current.
- There is no configured linter/test suite; use `python3 -m py_compile` on the scripts for a quick syntax check.
- Data-extract CSV format (non-obvious): the `AdditionalParameters` column is multi-line; line index 1 is a 9-char prefix + base64(raw-DEFLATE(JSON)) + 2-char suffix. `generate_json_report.py` strips `[9:-2]`, base64-decodes, then `zlib.decompress(..., -zlib.MAX_WBITS)`. Rows where `Command == "CollectCommand"` or `AdditionalParameters == ""` are skipped. Real extracts come from the .NET simulation `--csv` output (see skills); ~1M spins ≈ 1 GB.

### Bandit game servers (external, not in this repo)
Running actual simulations is a separate, heavy workflow driven by the `bandit-server` and `task-bandit-simulations` skills: it requires the .NET 6 SDK, private GamesGlobal GitLab NuGet feeds, and cloning a game repo into `tmp/` (gitignored). This is intentionally out of scope for the update script (game repos are external and per-task). Follow those skills when a task needs a real simulation.

### Secrets
`GG_GITLAB_USERNAME`, `GG_GITLAB_TOKEN`, `GCP_SERVICE_ACCOUNT_KEY_B64`, `JIRA_TOKEN`, `JIRA_EMAIL` are injected as environment variables (see `.env.example`). `.venv`, `.env`, and `tmp/` are gitignored.
