---
name: golden-standard-bet-settings
description: >-
  Gold Standard Bet Settings (GSBS) — understand what they are, how they work,
  and how to generate the SQL scripts for any game module. Use when the user
  mentions GSBS, Gold Standard, bet settings, golden bet, golden standard,
  or needs to create/update SQL bet setting scripts for a game.
---

# Gold Standard Bet Settings (GSBS)

## What are GSBS?

Instead of deploying a game's individual Bet Settings, IT makes use of predefined presets. These presets are referred to as the Gold Standard.

There are roughly 100 Operators that subscribe to one of the 18 custom Bet Setting presets. An Operator can subscribe to any of these presets, and when the game is deployed live, the presets of Bet Settings that they have subscribed to will override the default settings of the game in the Operator's casinos.

Each game must therefore be compatible with every custom Bet Setting option, or preset, to ensure that all Operators are catered for within the managed service.

## SQL File Structure

One SQL file is produced **per game module ID** (i.e. per RTP variant — each variant is treated as a separate game with its own module ID).

USA operators (USD currency) use separate files:

| File pattern | Contents |
|---|---|
| `GSBS_<ModuleID>.sql` | Standard presets — all non-USD operators |
| `GSBS_USA_<ModuleID>.sql` | USA presets — USD operators only |

See `example/` for reference files.

## SQL Functions

### Default (GBP / multi-currency default)

```sql
EXEC pr_GoldStandard_UpdateDefaultModuleSetting
  ModuleID, ClientID, SettingId, SettingValue, null, OperatorID, null
```

### Per-currency override

```sql
EXEC pr_GoldStandard_UpdateCurrencyModuleSetting
  CurrencyId, ModuleID, ClientID, SettingId, SettingValue, null, OperatorID, null
```

### ClientID values

| ClientID | Platform |
|---|---|
| `50300` | HTML5 Desktop |
| `40300` | HTML5 Mobile |

Both blocks must appear in every file (desktop first, then mobile).

### SettingID values

| SettingID | Meaning |
|---|---|
| `105` | MaxBet |
| `955` | MaxCoinsPerLineOrWay |
| `214` | DefaultBet |
| `956` | DefaultCoinsPerLineOrWay |

## Currency Multipliers & IDs

Values are stored in the **smallest currency unit** (pence, sen, etc.). The multiplier scales GBP values to the target currency.

| Multiplier | Currency | CurrencyId |
|---|---|---|
| 1× | GBP (default — no CurrencyId call) | — |
| 5× | MYR — Malaysian Ringgit | `20` |
| 10× | ZAR — South African Rand | `3` |
| 20× | ZMW — Zambian Kwacha | `177` |
| 50× | PHP — Philippine Peso | `23` |
| 100× | JPY — Japanese Yen | `4` |
| 200× | CLP — Chilean Peso | `49` |

EUR-only operators use CurrencyId `26` for both default and currency calls.  
USD-only operators use `UpdateDefaultModuleSetting` only (no currency override needed).

## Operator Presets Reference

> **Currency scaling note:** All MaxBet and DefaultBet values in the tables below refer to the **1x base currency (GBP)**. For other currencies they must be multiplied by the currency multiplier (e.g. ×5 for MYR, ×10 for ZAR, etc.). Exposure-based MaxBet is calculated as `Exposure / game_max_win` and must also be scaled per currency.

### Standard presets (18 total)

| OperatorID | ServerID | Preset Name | Operator Name | GBP MaxBet | GBP DefaultBet | Currencies | Notes |
|---|---|---|---|---|---|---|---|
| `8000000` | 5555 | DefaultBetAsMin | DefaultMinQuickfire | *(game default)* | = min bet | GBP + 6 | DefaultBet set to game minimum bet |
| `8000001` | 5556 | DefaultBetOf1 | IslandParadise_Default_1_Bet | *(game default)* | £1.00 | GBP | DefaultBet set to £1.00 |
| `8000002` | 5557 | DefaultBetOf2 | IslandParadise_Default_2_Bet | *(game default)* | £2.00 | GBP | DefaultBet set to £2.00 |
| `8001099` | 5570 | MaxBetOf2 | NewMaxbetof2 | £2.00 | £2.00 | GBP | MaxBet set to £2.00, DefaultBet set to £2.00 |
| `8000005` | 5567 | MaxBetOf5 | NewMaxbetof5 | £5.00 | *(game default)* | GBP | MaxBet set to £5.00 |
| `8000010` | 5568 | MaxBetOf10 | NewMaxbetof10 | £10.00 | *(game default)* | GBP | MaxBet set to £10.00 |
| `8000020` | 5569 | MaxBetOf20 | NewMaxbetof20 | £20.00 | *(game default)* | GBP | MaxBet set to £20.00 |
| `8000050` | 5560 | MaxBetOf50 | 50KMaxBet | £50.00 | *(game default)* | GBP | MaxBet set to £50.00 |
| `8000100` | 5561 | MaxBetOf100 | 100KMaxBet | £100.00 | *(game default)* | GBP | MaxBet set to £100.00 |
| `8000150` | 5562 | MaxBetOf150 | 150KMaxBet | £150.00 | *(game default)* | GBP | MaxBet set to £150.00 |
| `8000031` | 5558 | GermanyMaxBetOf1 | Germany Quickfire | €1.00 | €1.00 | EUR only | MaxBet set to €1.00, DefaultBet set to €1.00 |
| `8000037` | 5559 | MaxBetOf20-ExposureOf140k | Greece140K | ≤£20.00 | *(game default)* | GBP | MaxBet derived from 140K exposure, capped at £20.00 |
| `8050000` | 5549 | Exposure50k | 50KMaxExposure | exposure ÷ MaxWin | *(game default)* | GBP + 6 | MaxBet = £50,000 ÷ game MaxWin multiplier |
| `8100000` | 5550 | Exposure100k | 100KMaxExposure | exposure ÷ MaxWin | *(game default)* | GBP + 6 | MaxBet = £100,000 ÷ game MaxWin multiplier |
| `8125000` | 5551 | Exposure125k | 125KMaxExposure | exposure ÷ MaxWin | *(game default)* | GBP + 6 | MaxBet = £125,000 ÷ game MaxWin multiplier |
| `8250000` | 5552 | Exposure250k | 250KMaxExposure | exposure ÷ MaxWin | *(game default)* | GBP + 6 | MaxBet = £250,000 ÷ game MaxWin multiplier |
| `8500000` | 5553 | Exposure500k | 500KMaxExposure | exposure ÷ MaxWin | *(game default)* | GBP + 6 | MaxBet = £500,000 ÷ game MaxWin multiplier |
| `8750000` | 5554 | Exposure750k | 750KMaxExposure | exposure ÷ MaxWin | *(game default)* | GBP + 6 | MaxBet = £750,000 ÷ game MaxWin multiplier |

Additional MaxExposure presets (higher tiers):

| OperatorID | ServerID | Preset Name | Operator Name | MaxBet | DefaultBet | Currencies | Notes |
|---|---|---|---|---|---|---|---|
| `8111000` | 5602 | 1MillionMaxExposure | 1MillionMaxExposure | exposure ÷ MaxWin | *(game default)* | USD only | MaxBet = $1,000,000 ÷ game MaxWin multiplier |
| `8112000` | 5603 | 2MillionMaxExposure | 2MillionMaxExposure | exposure ÷ MaxWin | *(game default)* | USD only | MaxBet = $2,000,000 ÷ game MaxWin multiplier |
| `8113000` | 5604 | 3MillionMaxExposure | 3MillionMaxExposure | exposure ÷ MaxWin | *(game default)* | USD only | MaxBet = $3,000,000 ÷ game MaxWin multiplier |
| `8115000` | 5605 | 5MillionMaxExposure | 5MillionMaxExposure | exposure ÷ MaxWin | *(game default)* | USD only | MaxBet = $5,000,000 ÷ game MaxWin multiplier |
| `8110000` | 5606 | 10MillionMaxExposure | 10MillionMaxExposure | exposure ÷ MaxWin | *(game default)* | USD only | MaxBet = $10,000,000 ÷ game MaxWin multiplier |

### USA presets (separate file)

| OperatorID | ServerID | Preset Name | Operator Name | MaxBet | DefaultBet | Currencies | Notes |
|---|---|---|---|---|---|---|---|
| `8000006` | 5581 | Default200MaxExposure250k | Default200MaxExposure250k | exposure ÷ MaxWin | $2.00 | USD only | DefaultBet set to $2.00, MaxBet = $250,000 ÷ game MaxWin multiplier |
| `8000007` | 5582 | Default200MaxExposure500k | Default200MaxExposure500k | exposure ÷ MaxWin | $2.00 | USD only | DefaultBet set to $2.00, MaxBet = $500,000 ÷ game MaxWin multiplier |
| `8000008` | 5583 | Default200MaxExposure750k | Default200MaxExposure750k | exposure ÷ MaxWin | $2.00 | USD only | DefaultBet set to $2.00, MaxBet = $750,000 ÷ game MaxWin multiplier |

## File Generation Rules

1. **One file per module ID** — repeat all operator blocks for each variant.
2. **Each operator block** is preceded by a comment header:  
   `-- PresetName - Operator: <OperatorID>`
3. **Both clients** (50300 desktop, 40300 mobile) must be covered in every block.
4. **Currency rows** — for operators that apply to GBP + 6 currencies, add one `UpdateCurrencyModuleSetting` call per non-GBP currency using the multiplied value.
5. **Requested vs Applied values** — include both in the inline comment:  
   `--Requested Value: X | Applied Value: Y | <mult> <currency> <SettingName>`  
   Applied value may differ if the game's bet ladder doesn't contain the exact requested amount.
6. **USA files** — only include operators 8000006, 8000007, 8000008; no currency multiplier calls needed (USD has no multiplier variants).

## Example Snippet

```sql
------------------------------------------------------------------------------------------------------
-- DefaultBetAsMin - Operator: 8000000
------------------------------------------------------------------------------------------------------
-- Nailed It! Games - HTML5 Desktop - Slot - GameName (BANDIT)
EXEC pr_GoldStandard_UpdateDefaultModuleSetting 105049, 50300, 214, 20, null, 8000000, null --Requested Value: 20 | Applied Value: 20 | 1x One to One DefaultBet
EXEC pr_GoldStandard_UpdateDefaultModuleSetting 105049, 50300, 956, 1,  null, 8000000, null --Requested Value: 20 | Applied Value: 20 | 1x One to One DefaultCoinsPerLineOrWay
EXEC pr_GoldStandard_UpdateCurrencyModuleSetting 20,  105049, 50300, 214, 100,  null, 8000000, null --Requested Value: 100 | Applied Value: 100 | 5x MYR DefaultBet
-- ... (ZAR, ZMW, PHP, JPY, CLP follow)
-- Nailed It! Games - HTML5 - Slot - GameName (BANDIT)
EXEC pr_GoldStandard_UpdateDefaultModuleSetting 105049, 40300, 214, 20, null, 8000000, null --Requested Value: 20 | Applied Value: 20 | 1x One to One DefaultBet
-- ...
```
