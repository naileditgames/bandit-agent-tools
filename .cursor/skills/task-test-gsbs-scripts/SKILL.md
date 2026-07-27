---
name: task-test-gsbs-scripts
description: >-
  Test Gold Standard Bet Settings (GSBS) SQL scripts against an Axiom environment —
  verify that bet settings are correctly applied for all operators and currencies.
  Use when asked to test GSBS scripts, verify bet settings, check GSBS on Axiom,
  or run GSBS testing for a game.
---

# Task: Test GSBS Scripts

<!-- TODO: fill in with task description from user -->

## Overview

This task verifies that GSBS SQL scripts have been correctly applied on the target Axiom environment. The SQL files are assumed to have already been generated and executed against Axiom before this task starts — there is nothing to generate or deploy. The sole purpose of this task is to open the game for each operator/currency combination and confirm that the bet settings (DefaultBet, MaxBet) visible in-game match what the GSBS scripts configured.

## Prerequisites

The GSBS SQL scripts must already be generated and executed against the target Axiom environment before starting. This task only verifies the result — it does not generate or apply any SQL.

The following parameters are required before starting:

| Parameter | Example | Description |
|---|---|---|
| `axiom_name` | `gtp727` | Axiom environment name |
| `api_key` | — | API key for the target Axiom environment. Can be generated in Axiom under the **Api Keys** tab. |
| `game_name` | `dragonUnchainedDesktop` | Game name as registered in Axiom. Can be extracted from the game's Axiom launch link as the `gameId` URL parameter. |
| `max_win` | `5486.5` | Game's maximum win multiplier (x times bet, bet-normalised). Used to calculate MaxBet for exposure-based operators: `MaxBet = Exposure / max_win`. |


## Task Progress

```
- [ ] Parameters gathered (axiom_name, api_key, game_name, max_win)
- [ ] Launch links generated → tmp/gsbs_test_<game_name>/links.json
- [ ] MaxBet values calculated for all exposure operators
- [ ] Screenshots folder structure created
- [ ] All operator/currency links verified with screenshots
- [ ] Results table posted as Jira comment
- [ ] Screenshots zipped and attached to Jira ticket
```

**Reference:** For operator IDs, server IDs, currencies, and preset details — see the [`golden-standard-bet-settings`](./../golden-standard-bet-settings/SKILL.md) skill.

## Steps

### 0. Read parameters from Jira (if triggered from Jira)

If this task was triggered from a Jira ticket, read all required parameters from the ticket description before doing anything else. Use the `jira-nailedit` skill to fetch the ticket.

The ticket description must contain all required parameters listed in [Prerequisites](#prerequisites). Parameters may appear as a table, a bullet list, or inline key/value pairs — parse whatever format is present.

**If any required parameter is missing:**

1. Post a comment to the Jira ticket listing every missing parameter, e.g.:

   > ❌ Cannot start GSBS testing — the following required parameters are missing from the ticket description:
   > - `api_key`
   > - `max_win`
   >
   > Please update the ticket description with these values and re-trigger the task.

2. Stop execution immediately. Do not proceed to any further steps.

Only continue to Step 1 once all required parameters are confirmed present.

### 1. Generate launch links

Use the `golden-bet-scripts` tool to generate links for all operators:

```bash
cd tools/golden-bet-scripts
.venv/bin/python main.py \
  --axiom-name <axiom_name> \
  --api-key <api_key> \
  --game-name <game_name> \
  --username <random_username> \
  --output tmp/gsbs_test_<game_name>/links.json
```

Use a unique random username (e.g. `user883738`) each run — tokens are single-use and re-running with the same username will fail with 404.

Store output in `tmp/gsbs_test_<game_name>/` (the `tmp/` folder in this repo, not `/tmp`).

### 2. Calculate MaxBet values for exposure-based operators

For each exposure level, calculate the MaxBet using the game's `max_win`:

```
MaxBet (smallest unit) = floor(Exposure × 100 / max_win)
```

Then scale per currency multiplier (×1 GBP, ×5 MYR, ×10 ZAR, ×20 ZMW, ×50 PHP, ×100 JPY, ×200 CLP). The game's bet ladder may not contain the exact value — use the nearest lower available bet.

See the `golden-standard-bet-settings` skill for the full list of exposure operators and currency multipliers.

### 3. Verify each link and capture screenshots

Create the screenshots folder structure:

```
tmp/gsbs_test_<game_name>/screenshots/<operatorId>/
```

One subfolder per operator ID. For each link in `links.json`:

1. Open the link in the browser.
2. Open the game's bet selection menu.
3. Verify **DefaultBet** — confirm it matches the expected value for the operator/currency.
4. Verify **MaxBet** — the highest available bet in the menu **must not exceed** the calculated MaxBet for that exposure/currency.
5. Take a screenshot and save it to `screenshots/<operatorId>/<currency>.png`.

**Outcome rules:**

| Situation | Result |
|---|---|
| MaxBet in game ≤ calculated MaxBet | ✅ OK |
| MaxBet in game > calculated MaxBet | ❌ FAIL — reports violation |
| MaxBet in game < calculated MaxBet / 2 | ⚠️ WARNING — MaxBet is more than 2× lower than allowed; flag for review |

### 4. Post results to Jira and attach screenshots

Once all operators and currencies have been verified, post a summary comment to the Jira ticket and attach the screenshots.

#### 4a. Post results table

Use the `jira-nailedit` skill to post a comment with a results table covering every tested operator/currency combination:

```
Tested game: <game_name> on <axiom_name>

| Operator ID | Operator Name | Currency | Default Bet | Max Bet (game) | Max Bet (allowed) | Result |
|---|---|---|---|---|---|---|
| 8000000 | DefaultMinQuickfire | GBP | 0.20 | 40.00 | — | ✅ OK |
| 8000000 | DefaultMinQuickfire | MYR | 1.00 | 120.00 | — | ✅ OK |
| ... | | | | | | |
```

Use ✅ OK, ⚠️ WARNING, or ❌ FAIL in the Result column. Add a short summary line at the top of the comment, e.g.:

> ✅ All 68 operator/currency combinations passed.

or

> ❌ 2 failures and 1 warning detected — see table below.

#### 4b. Zip and attach screenshots

Zip the entire screenshots folder and attach it to the Jira ticket:

```bash
cd tmp/gsbs_test_<game_name>
zip -r screenshots_<game_name>.zip screenshots/
```

Then use the `jira-nailedit` skill to upload `screenshots_<game_name>.zip` as an attachment to the ticket.

---

## Notes

### Navigating the game with Chrome DevTools MCP

Bandit games render on an HTML5 canvas with an HTML overlay (HUD) on top. Canvas elements are not in the accessibility tree, but the HUD buttons are.

#### Dismiss the intro screen

After the game loads, a "Press anywhere to continue" splash is shown. Dismiss it with a trusted key press:

```js
press_key("Space")
```

Wait ~3 seconds after the key press before interacting with the HUD to let the intro animation finish.

#### Open the bet panel

The bet button is an HTML element with `id="bet_button"`. Dispatch a `pointerup` event — the game listens on `pointerup`, not `click`, and does **not** check `isTrusted`:

```js
document.getElementById('bet_button').dispatchEvent(new MouseEvent('pointerup', { bubbles: true }));
```

Wait ~1 second after dispatching before taking the screenshot.

#### Close the bet panel

The close (✕) button has no stable ID. Find it by locating the SVG icon in the top-right corner of the panel and dispatching `pointerup` on its parent:

```js
const svgs = document.querySelectorAll('svg');
for (const svg of svgs) {
  const r = svg.getBoundingClientRect();
  if (r.x > 1100 && r.y > 40 && r.y < 80) {
    svg.parentElement.dispatchEvent(new MouseEvent('pointerup', { bubbles: true }));
    break;
  }
}
```

#### Why `.click()` does not work

The HUD uses React with `pointerup`-based handlers. Standard `.click()` and manually dispatched `click`/`mousedown`/`mouseup` events are ignored because the game checks `event.isTrusted` for those event types. The `pointerup` handler does not perform this check, making it the reliable automation path.
