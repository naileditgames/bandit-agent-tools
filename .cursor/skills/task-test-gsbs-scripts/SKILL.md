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
- [ ] Screenshots zip + links.json attached to Jira ticket
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
python3 main.py \
  --axiom-name <axiom_name> \
  --api-key <api_key> \
  --game-name <game_name> \
  --username <random_username> \
  --output tmp/gsbs_test_<game_name>/links.json
```

Use a unique random username (e.g. `user883738`) each run — using the same base username for a second run will produce conflicting tokens.

Store output in `tmp/gsbs_test_<game_name>/` (the `tmp/` folder in this repo, not `/tmp`).

> **Token lifetime:** Each token is created with `numLaunchTokens: 10`, meaning it can be used for up to **10 game launches**, not just one. If verification of a link fails, you can retry using the **same link from `links.json`** without regenerating. Only generate new links if the original run's `links.json` is lost or if tokens have been exhausted.

> **Operator name vs lobby name:** The launch URL uses the `operatorNameLink` field, not `operatorName`. These may differ (e.g. operator `50KMaxExposure` uses lobby name `50KMEQuickfire` in the URL). **Always use the link directly from `links.json`** — never reconstruct it from the operator name.

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
3. Identify **DefaultBet** — the bet highlighted in blue (selected) when the panel first opens is the game's configured default. Do **not** use the minimum value in the ladder as the default.
4. Identify **MaxBet** — the highest available bet button in the menu. Read it from the screenshot visually; see [Extracting bet values reliably](#extracting-bet-values-reliably) below for automation guidance.
5. Verify MaxBet does not exceed the calculated limit for that operator/currency.
6. Take a screenshot and save it to `screenshots/<operatorId>/<currency>.png`.

**Outcome rules:**

| Situation | Result |
|---|---|
| MaxBet in game ≤ calculated MaxBet | ✅ OK |
| MaxBet in game > calculated MaxBet | ❌ FAIL — reports violation |
| MaxBet in game < calculated MaxBet / 2 | ⚠️ WARNING — MaxBet is more than 2× lower than allowed; flag for review |

### 4. Post results to Jira and attach screenshots

Once all operators and currencies have been verified, post a summary comment to the Jira ticket and attach the screenshots and links file.

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

> ✅ All 72 operator/currency combinations passed.

or

> ❌ 2 failures and 1 warning detected — see table below.

#### 4b. Zip and attach screenshots + links

Zip the entire screenshots folder and attach it to the Jira ticket, and also attach `links.json`:

```bash
cd tmp/gsbs_test_<game_name>
zip -r screenshots_<game_name>.zip screenshots/
```

Then use the `jira-nailedit` skill to upload both `screenshots_<game_name>.zip` and `links.json` as attachments to the ticket.

---

## Notes

### Navigating the game with Playwright

Bandit games render on an HTML5 canvas with an HTML overlay (HUD) on top. Canvas elements are not in the accessibility tree, but the HUD buttons are. Use Playwright (headless Chromium) to automate navigation.

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

Wait ~1.5 seconds after dispatching before reading values or taking the screenshot.

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

---

### Extracting bet values reliably

> **IMPORTANT:** Automated DOM text extraction is unreliable for bet values. Visual inspection of screenshots is the ground truth. Use the extraction approach below only as a starting point; always confirm suspicious results from the screenshot.

#### The balance false-positive problem

The player balance is displayed in the bottom HUD (left side of screen). A generic text-walker will capture it alongside bet values, making it appear as an extra bet option. Example: the balance "£250.00" gets captured as `250`, causing a false FAIL for any operator whose MaxBet cap is below £250.

**Rule:** The bet panel is rendered on the **right half of the screen** (x > 600 px at 1280×720). Only read elements positioned in that region.

#### Locale-specific number formatting

Different currency locales use different decimal and thousands separators, which breaks naive regex parsing:

| Currency | Display example | Parsing issue |
|---|---|---|
| GBP/USD | `2.00` | No issue |
| EUR (DE/GR) | `0,20` (comma = decimal) | `replace(',','')` → `020` → 20 ❌ |
| CLP | `1 000,00` (space = thousands, comma = decimal) | Space splits the number; only "1" is captured ❌ |
| ZMW/JPY | `1,000.00` or `1000` | Usually no issue |

**Correct parsing approach:** Strip spaces, then replace the last comma (if followed by exactly 2 digits at end) with a dot for decimal, remove remaining commas/dots used as thousands separators. Or, more simply, read the `innerText` of each bet button element directly and parse `parseFloat(text.replace(/\s/g,'').replace(',','.'))`.

#### Reliable bet value extraction snippet

```javascript
() => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
  const values = [];
  let node;
  while ((node = walker.nextNode())) {
    const parent = node.parentElement;
    if (!parent) continue;
    const rect = parent.getBoundingClientRect();
    // Only the bet panel on the right half of the screen
    if (!rect || rect.x < 600 || rect.width < 20 || rect.height < 20) continue;
    // Normalise locale separators: strip spaces, replace comma-decimal
    const raw = node.textContent.trim().replace(/\s/g, '');
    const normalised = raw.replace(',', '.');
    const num = parseFloat(normalised);
    if (!isNaN(num) && num >= 0.01 && num <= 500000) {
      values.push(num);
    }
  }
  values.sort((a, b) => a - b);
  const unique = [...new Set(values)];
  return { values: unique, max: unique.length > 0 ? unique[unique.length - 1] : null };
}
```

#### Identifying DefaultBet from the screenshot

The bet that is **highlighted in blue** when the panel first opens is the game's configured DefaultBet. The extraction script's minimum-value heuristic is wrong — do not use it. Read the DefaultBet from the screenshot (bottom HUD shows `BET (£) X.XX`) or from the highlighted button.

#### Scrollable bet panels (high-multiplier currencies)

For CLP and other high-multiplier currencies the bet panel may extend beyond the visible area. If the extracted `max` seems low, check whether the panel is scrollable — look at the screenshot for a scroll indicator or truncated list. The DOM extraction will miss values that are off-screen but present in the DOM only when scrolled into view.

---

### Handling verification failures

#### "Login failed." in-game error

The game loads but shows "Login failed." inside the canvas. Causes:
- **Token already used up** (unlikely with `numLaunchTokens: 10`, but possible after many retries).
- **Web.config default currency mismatch**: the token was created when a different currency was active in Web.config, so the FakeAPI session is inconsistent. Wait for the Web.config to be restored and retry with the same link.
- **Session expired**: the token is still valid but the session timed out on the server. Retry by navigating to the link again in a fresh browser context.

> Always retry with the **same link** (same token) before generating new links — tokens have 10 uses.

#### HTTP 406 "Missing information" error

The game launch URL returns a raw 406 JSON error page (not the game). This means the FakeAPI could not find the game configuration for the requested operator/currency combination. Causes:
- The Web.config was set to a different currency than the one the user account was created for.
- The operator lobby is not configured for that currency on this Axiom environment.

To distinguish these: if other operators load fine for the same currency, the operator lobby is likely not configured. If all operators for that currency fail, the Web.config is probably wrong.

> For operators that fail with 406 for certain currencies: note them as ⚠️ WARNING (not configured on environment) and report to the ticket owner.

#### Web.config management

The `golden-bet-scripts` tool manages Web.config automatically during link generation. The correct endpoints are:

```
# Fetch Web.config
GET https://axiomcore-app1-{axiom_name}.installprogram.eu/Manage/Content/FileContent
    ?filePath=M%3A%5CMGS_IISWebSites%5CCasino%5CSGIFakeAPI%5CWeb.config
    Header: x-api-key: <api_key>

# Upload Web.config
PATCH https://axiomcore-app1-{axiom_name}.installprogram.eu/Manage/Content/FileContent
    Header: x-api-key: <api_key>
```

Do **not** use `api5-rhel1-{axiom}.installprogram.eu/casino/admin/v1/webconfig` — that endpoint does not exist.

If multiple partial runs have left the Web.config in an unknown state, restore it to GBP before starting a new run.
