---
name: task-test-gsbs-scripts
description: >-
  Test Gold Standard Bet Settings (GSBS) SQL scripts against an Axiom environment —
  verify that bet settings are correctly applied for all operators and currencies.
  Use when asked to test GSBS scripts, verify bet settings, check GSBS on Axiom,
  or run GSBS testing for a game.
---

# Task: Test GSBS Scripts

## Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Task Progress](#task-progress)
- [Steps](#steps)
  - [1. Read parameters from Jira](#1-read-parameters-from-jira-if-triggered-from-jira)
  - [2. Generate launch links](#2-generate-launch-links)
  - [3. Calculate MaxBet values](#3-calculate-maxbet-values-for-exposure-based-operators)
  - [4. Verify each link and capture screenshots](#4-verify-each-link-and-capture-screenshots)
    - [4a. Open the game link](#4a-open-the-game-link)
    - [4b. Dismiss splash and wait for game ready](#4b-dismiss-splash-and-wait-for-game-ready)
    - [4c. Open the bet panel and extract values](#4c-open-the-bet-panel-and-extract-values)
    - [4d. Record and verify the values](#4d-record-and-verify-the-values)
    - [4e. Take a screenshot](#4e-take-a-screenshot)

  - [5. Post results to Jira and attach screenshots](#5-post-results-to-jira-and-attach-screenshots)
    - [5a. Post results table](#5a-post-results-table)
    - [5b. Zip and attach screenshots](#5b-zip-and-attach-screenshots)
    - [5c. Attach links.json](#5c-attach-linksjson)
- [Notes](#notes)
  - [Bandit game HUD — automation constraints](#bandit-game-hud--automation-constraints)
  - [links.json structure](#linksjson-structure-reference)
  - [DOM structure reference](#dom-structure-reference-verified-against-dragonunchaineddesktop)
    - [Phase 1 — Preloader](#phase-1--preloader)
    - [Phase 2 — Splash screen](#phase-2--splash-screen)
    - [Phase 3 — Intro animation](#phase-3--intro-animation-buttons-disabled)
    - [Phase 4 — Game ready](#phase-4--game-ready-hud-interactive)
    - [Phase 5 — Bet panel open](#phase-5--bet-panel-open)

---

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

### 1. Read parameters from Jira (if triggered from Jira)

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

Only continue to Step 2 once all required parameters are confirmed present.

### 2. Generate launch links

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

### 3. Calculate MaxBet values for exposure-based operators

For each exposure level, calculate the MaxBet using the game's `max_win`:

```
MaxBet (smallest unit) = floor(Exposure × 100 / max_win)
```

Then scale per currency multiplier (×1 GBP, ×5 MYR, ×10 ZAR, ×20 ZMW, ×50 PHP, ×100 JPY, ×200 CLP). The game's bet ladder may not contain the exact value — use the nearest lower available bet.

See the `golden-standard-bet-settings` skill for the full list of exposure operators and currency multipliers.

### 4. Verify each link and capture screenshots

Create the screenshots folder structure:

```
tmp/gsbs_test_<game_name>/screenshots/<operatorId>/
```

One subfolder per operator ID. For each link in `links.json`, follow the full sequence below.

#### 4a. Open the game link

Use `new_page` (or `navigate_page` on an existing tab) with the URL from `currencyLinks`:

```js
// MCP call: new_page
{ "url": "<currencyLinks[currency]>" }
```

The page goes through two phases before the splash is ready:

1. **Preloader** — `#root` is empty, the engine renders a canvas loading bar. `#_pixi_root_` does not exist yet.
2. **Splash screen** — React has mounted; `#_pixi_root_` and `#_ui_root_` appear inside `#root`.

Poll until `#_pixi_root_` is present in the DOM, which confirms the preloader has finished and the splash screen is displayed:

```js
// MCP call: evaluate_script — repeat until returns true
{
  "script": "() => !!document.getElementById('_pixi_root_')"
}
```

Poll every ~1 second with a timeout of 30 seconds. If `#_pixi_root_` never appears, take a screenshot to diagnose the state (network error, missing token, etc.) and mark the entry as ❌ FAIL.

#### 4b. Dismiss splash and wait for game ready

Press Space to dismiss the splash screen, then poll until `#bet_button` has no `disabled-*` class — this covers both the splash dismissal and the intro animation in one step:

```js
// MCP call: press_key
{ "key": "Space" }
```

Then poll until the bet button is active:

```js
// MCP call: evaluate_script — repeat until returns true
{
  "script": `
    (() => {
      const btn = document.getElementById('bet_button');
      if (!btn) return false;
      return !btn.className.split(' ').some(c => c.startsWith('disabled'));
    })()
  `
}
```

Poll every ~1 second with a timeout of 30 seconds. If the button never becomes active, take a screenshot and mark the entry as ❌ FAIL.

#### 4c. Open the bet panel and extract values

Dispatch `pointerup` on the bet button — the game listens on `pointerup`, not `click`:

```js
// MCP call: evaluate_script
{
  "script": "document.getElementById('bet_button').dispatchEvent(new MouseEvent('pointerup', { bubbles: true }))"
}
```

Wait ~1 second for the panel to animate open, then extract the full bet ladder and the currently selected (default) bet:

```js
// MCP call: evaluate_script
{
  "script": `
    (() => {
      const itemList = document.querySelector('#bet_panel [class*="itemList"]');
      if (!itemList) return JSON.stringify({ error: 'itemList not found', bets: [], count: 0 });

      const items = Array.from(itemList.children);
      const bets = items.map(item => ({
        value: item.textContent.trim(),
        selected: item.className.split(' ').some(c => c.startsWith('selectedItem'))
      }));

      return JSON.stringify({ bets, count: bets.length });
    })()
  `
}
```

> **If the script returns `error: itemList not found`:** The bet panel may not have finished animating. Wait another second and retry. If it still fails, take a `take_snapshot` and inspect the accessibility tree to locate the bet value nodes.

Parse the returned JSON to obtain:

- **`defaultBet`** — the `value` of the entry where `selected === true`.
- **`betLadder`** — all `value` entries in order (already sorted ascending by the game).
- **`maxBet`** — the last entry in the ladder.

> **Currency number formatting:** Bet values are locale-formatted and vary by currency. Do not assume a fixed format. Observed formats:
> - GBP (`£`), MYR (`RM`), ZAR (`R`), ZMW (`K`), PHP (`₱`): comma thousands separator, period decimal — e.g. `1,234.56`
> - JPY (`¥`): comma thousands separator, no decimal places — e.g. `1,000`
> - CLP (`$`): **space** thousands separator, **comma** decimal — e.g. `1 000,00`
>
> For numeric comparison (MaxBet check), parse the raw string into a number using a helper that strips thousands separators and normalises the decimal marker:
> ```js
> function parseBetValue(str) {
>   // CLP uses space thousands + comma decimal; all others use comma thousands + period decimal
>   if (/\d \d/.test(str)) {
>     return parseFloat(str.replace(/ /g, '').replace(',', '.'));
>   }
>   return parseFloat(str.replace(/,/g, ''));
> }
> ```

#### 4d. Record and verify the values

| Field | Expected | Source |
|---|---|---|
| `defaultBet` | Operator/currency-specific configured default | GSBS table |
| `maxBet` | ≤ `floor(Exposure × 100 / max_win)` × currency multiplier | Calculated in Step 2 |

Apply outcome rules:

| Situation | Result |
|---|---|
| MaxBet in game ≤ calculated MaxBet | ✅ OK |
| MaxBet in game > calculated MaxBet | ❌ FAIL — reports violation |
| MaxBet in game < calculated MaxBet / 2 | ⚠️ WARNING — MaxBet is more than 2× lower than allowed; flag for review |
| DefaultBet does not match expected | ❌ FAIL — default bet misconfigured |

#### 4e. Take a screenshot

After recording the values, take a screenshot with the bet panel open:

```js
// MCP call: take_screenshot
{ "filePath": "tmp/gsbs_test_<game_name>/screenshots/<operatorId>/<currency>.png" }
```

### 5. Post results to Jira and attach screenshots

Once all operators and currencies have been verified, post a summary comment to the Jira ticket and attach the screenshots.

#### 5a. Post results table

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

#### 5b. Zip and attach screenshots

Zip the entire screenshots folder and attach it to the Jira ticket:

```bash
cd tmp/gsbs_test_<game_name>
zip -r screenshots_<game_name>.zip screenshots/
```

Then use the `jira-nailedit` skill to upload `screenshots_<game_name>.zip` as an attachment to the ticket.

#### 5c. Attach links.json

Use the `jira-nailedit` skill to upload `tmp/gsbs_test_<game_name>/links.json` as an attachment to the ticket.

---

## Notes

### Bandit game HUD — automation constraints

Bandit games render on an HTML5 canvas with an HTML overlay (HUD) on top. Canvas elements are not in the accessibility tree, but the HUD buttons are.

**Why `.click()` does not work:** The HUD uses React with `pointerup`-based handlers. Standard `.click()` and manually dispatched `click`/`mousedown`/`mouseup` events are ignored because the game checks `event.isTrusted` for those event types. The `pointerup` handler does not perform this check, making it the reliable automation path.

### links.json structure (reference)

The file generated by `golden-bet-scripts` has this shape:

```json
{
  "<operatorId>": {
    "operatorId": 8000000,
    "serverId": 5555,
    "operatorName": "DefaultMinQuickfire",
    "operatorNameLink": "MinQuickFire",
    "currencyLinks": {
      "GBP": "https://mobile-app1-<axiom_name>.installprogram.eu/mobilewebservices/casino/game/launch/MinQuickFire/<game_name>/en?logintype=VanguardSessionToken&externaltoken=<token>"
    }
  }
}
```

Iterate `Object.entries(links)` → then `Object.entries(operator.currencyLinks)` to visit every operator/currency pair.

### DOM structure reference (verified against dragonUnchainedDesktop)

This section documents the actual DOM state at each loading phase as verified by live browser inspection.

#### Phase 1 — Preloader

The browser navigates to the game URL. A canvas-based progress bar is rendered by the engine before React mounts.

- `#root` exists but is **empty** (`children.length === 0`, `innerHTML` is whitespace only).
- `#_pixi_root_` and `#_ui_root_` do **not** exist yet.

**Signal to wait on:** poll until `document.getElementById('_pixi_root_')` is non-null, or until `#root` has at least one child.

#### Phase 2 — Splash screen

React has mounted. The game shows a "press anywhere to continue" splash screen.

- `#root` now has children.
- `#_pixi_root_` and `#_ui_root_` are both present inside `#root`.
- Inside `#_ui_root_`, there is a root wrapper div (class `root-*`) containing:
  - A `scalableContainer-*` div — **empty** at this stage (`children.length === 0`).
  - A `windowsRoot-*` div.
- `#bet_button` does **not** exist yet.

**Signal to dismiss:** dispatch `pointerup` anywhere on the page, or press `Space`.

```js
document.body.dispatchEvent(new MouseEvent('pointerup', { bubbles: true, clientX: 512, clientY: 300 }));
// or:
// press_key { key: "Space" }
```

#### Phase 3 — Intro animation (buttons disabled)

After the splash is dismissed, the game plays an intro animation. The HUD mounts during this phase but all controls are locked.

- `#bet_button`, `#spin_button`, `#autoplay_button`, `#turbo_button`, `#menu_button` now exist.
- The `scalableContainer-*` div now has children.
- `#bet_button` has one or more JSS classes that **start with `disabled`** (e.g. `disabled-0-2-71`). The exact number suffix varies per build — always check by prefix, not exact match.

**Signal to wait on:** poll until no class on `#bet_button` starts with `disabled`:

```js
const betBtn = document.getElementById('bet_button');
const isDisabled = betBtn.className.split(' ').some(c => c.startsWith('disabled'));
```

#### Phase 4 — Game ready (HUD interactive)

Intro animation has finished. All HUD buttons are active.

- `#bet_button` classes contain only `buttonRoot-*` and `betButton-*` — no `disabled-*` prefix.
- The bottom bar shows the current bet in a `betBox-*` element (class matched via `[class*="betBox"]`).

**Extract default bet from HUD (without opening the panel):**

```js
const betBox = document.querySelector('[class*="betBox"]');
const text = betBox.textContent.trim();               // e.g. "BET (£)0.20" or "BET ($)40,00"
const defaultBet = text.match(/([\d,. ]+)$/)[1].trim(); // "0.20" / "40,00" / "1 000,00"
```

Note: the trailing match includes spaces to handle CLP-style formatting (`1 000,00`). Always `.trim()` the result.

#### Phase 5 — Bet panel open

Open the bet panel by dispatching `pointerup` on `#bet_button`:

```js
document.getElementById('bet_button').dispatchEvent(new MouseEvent('pointerup', { bubbles: true }));
```

Wait ~1 second for the animation, then `#bet_panel` appears.

**DOM structure inside `#bet_panel`:**

```
#bet_panel
  .content-*
    .topBar-*          ← game name + "BET (currency)" label + close button
    .betPanel-*
      .itemList-*      ← direct children are the bet items
        div.item-* .item-d0-*                                        ← unselected item
        div.item-* .item-d0-* .selectedItem-* .selectedItem-d2-*    ← selected (current) item
        ...
          .fitDiv-* .textFit-*
            (text node: "0.20")
```

**Key class patterns (JSS — suffixes vary per build, always match by base name):**

| Element | Class prefix | Notes |
|---|---|---|
| Bet item wrapper | `item-` | Every bet in the ladder has this |
| Selected bet | `selectedItem-` | Added alongside `item-*` only on the active bet |
| Bet value text container | `fitDiv-` / `textFit-` | Leaf text node directly inside |

The selected item also gets `background-color: rgb(63, 81, 181)` (indigo/blue).

**Extract full bet ladder and default/max bet:**

```js
(() => {
  const itemList = document.querySelector('#bet_panel [class*="itemList"]');
  const items = Array.from(itemList.children);
  const ladder = items.map(item => ({
    value: item.textContent.trim(),
    isSelected: item.className.split(' ').some(c => c.startsWith('selectedItem'))
  }));
  const defaultBet = ladder.find(b => b.isSelected)?.value;
  const maxBet = ladder[ladder.length - 1].value;
  return { defaultBet, maxBet, ladder: ladder.map(b => b.value) };
})()
```

**Example outputs by currency (dragonUnchainedDesktop / DefaultMinQuickfire):**

GBP (`£`) — comma thousands, period decimal:
```json
{ "defaultBet": "0.20", "maxBet": "40.00", "ladder": ["0.20","0.40","0.60","0.80","1.00","1.20","2.00","3.00","4.00","5.00","6.00","8.00","10.00","12.00","15.00","20.00","30.00","40.00"] }
```

MYR (`RM`) — same format as GBP:
```json
{ "defaultBet": "1.00", "maxBet": "120.00", "ladder": ["1.00","1.20","2.00","3.00","4.00","5.00","6.00","8.00","10.00","12.00","15.00","20.00","30.00","40.00","60.00","80.00","100.00","120.00"] }
```

ZAR (`R`) — same format as GBP:
```json
{ "defaultBet": "2.00", "maxBet": "300.00", "ladder": ["2.00","3.00","4.00","5.00","6.00","8.00","10.00","12.00","15.00","20.00","30.00","40.00","60.00","80.00","100.00","120.00","200.00","300.00"] }
```

JPY (`¥`) — comma thousands, **no decimal places**:
```json
{ "defaultBet": "20", "maxBet": "3,000", "ladder": ["20","30","40","60","80","100","120","200","300","400","500","600","800","1,000","1,200","1,500","2,000","3,000"] }
```

CLP (`$`) — **space** thousands, **comma** decimal:
```json
{ "defaultBet": "40,00", "maxBet": "3 000,00", "ladder": ["40,00","60,00","80,00","100,00","120,00","200,00","300,00","400,00","500,00","600,00","800,00","1 000,00","1 200,00","1 500,00","2 000,00","3 000,00"] }
```

**Currency symbol reference (as displayed in HUD and bet panel header):**

| Currency | Symbol in game |
|---|---|
| GBP | `£` |
| MYR | `RM` |
| ZAR | `R` |
| ZMW | `K` |
| PHP | `₱` |
| JPY | `¥` |
| CLP | `$` |
