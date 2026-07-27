# golden-bet-scripts

Python CLI tool for generating Axiom game launch links across all Gold Standard Bet Settings (GSBS) operators and currencies. Used during GSBS testing to quickly obtain playable links for every operator/currency combination without manually configuring each one.

## What it does

1. Fetches the `Web.config` from the target Axiom environment.
2. For each currency group, updates the `defaultcurrency` in `Web.config` and re-uploads it.
3. Creates a temporary user session (external token) for each operator × currency combination.
4. Builds a launch link per combination and writes all results to a JSON file.

## Setup

```bash
cd tools/golden-bet-scripts
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Usage

```bash
.venv/bin/python main.py \
  --axiom-name <axiom_name> \
  --api-key    <api_key> \
  --game-name  <game_name> \
  --username   <base_username> \
  --output     <output_file>
```

| Argument | Required | Example | Description |
|---|---|---|---|
| `--axiom-name` | ✅ | `gtp727` | Axiom environment name |
| `--api-key` | ✅ | `fe07827d-...` | API key from the Axiom **Api Keys** tab |
| `--game-name` | ✅ | `dragonUnchainedDesktop` | Game ID as registered in Axiom (the `gameId` URL param on the launch link) |
| `--username` | ✅ | `user883738` | Base username; each token is suffixed with an index (e.g. `user8837381`, `user8837382`, …) |
| `--output` | — | `links.json` | Output JSON file path (default: `golden-bet-links.json`) |

**Important:** use a fresh random username on every run — tokens are single-use and re-running with the same username will fail with a 404.

### Example

```bash
.venv/bin/python main.py \
  --axiom-name gtp727 \
  --api-key    fe07827d-a154-4ddb-b671-83e61ae3f4b8 \
  --game-name  dragonUnchainedDesktop \
  --username   user883738 \
  --output     tmp/gsbs_test_dragonUnchainedDesktop/links.json
```

## Output format

```json
{
  "8000000": {
    "operatorId": 8000000,
    "serverId": 5555,
    "operatorName": "DefaultMinQuickfire",
    "operatorNameLink": "MinQuickFire",
    "currencyLinks": {
      "GBP": "https://mobile-app1-gtp727.installprogram.eu/mobilewebservices/casino/game/launch/MinQuickFire/dragonUnchainedDesktop/en?logintype=VanguardSessionToken&externaltoken=user8837381",
      "MYR": "https://mobile-app1-gtp727.installprogram.eu/...",
      ...
    }
  },
  ...
}
```

Each key is the operator ID. Each `currencyLinks` entry is a ready-to-open browser link for that operator/currency combination.

## Files

| File | Description |
|---|---|
| `main.py` | CLI entry point — orchestrates the full link generation flow |
| `operators.py` | `OPERATOR_DATA_SET` — all GSBS operators with their IDs, server IDs, and supported currencies |
| `web_config.py` | Fetch, modify (`defaultcurrency`), and upload `Web.config` via Axiom API |
| `create_user.py` | Create a temporary user session and return an external launch token |
| `requirements.txt` | Python dependencies |

## Adding or updating operators

Edit `operators.py`. Each entry is an `OperatorData` dataclass:

```python
OperatorData(
    operator_id=8000000,
    server_id=5555,
    operator_name="DefaultMinQuickfire",
    operator_name_link="MinQuickFire",   # used in the launch URL path
    currencies=["GBP", "MYR", "ZAR", "ZMW", "PHP", "JPY", "CLP"],
)
```
