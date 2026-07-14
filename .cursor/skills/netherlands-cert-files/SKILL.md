---
name: netherlands-cert-files
description: >-
  Build the Netherlands certification "Files" deliverable for a GamesGlobal Bandit
  slot-game repo: collect the result-affecting math source (JSON variant configs + C#
  game logic) of one game into a flat folder and write a description.xlsx listing every
  file with a short, content-based note. Use whenever the user wants to prepare a
  Netherlands certification / regulator / testing-lab package for a Bandit game,
  "export the math files", "make the NetherlandsFiles folder", "do the cert files for
  StarsBonanza3x3", or asks for the same files-plus-Excel bundle — works for any Bandit
  game shape (lines, ways, hold, bonus-buy, free spins).
---

# Netherlands certification Files package

A "Files" package is what gets handed to the Netherlands certification lab: a flat
folder containing only the **result-affecting math source** of one game, plus a
`description.xlsx` that tells the reader what each file is for. The reader is a
non-author (an auditor) who needs to find the math fast.

**Output location:** build the deliverable in a **temp dir outside the repo** —
e.g. `/tmp/<GameName>-nl/NetherlandsFiles` — then write the zip there too
(e.g. `/tmp/<GameName>-nl/NetherlandsFiles.zip`). The loose files are regenerable
and are not committed — the zip is the deliverable (to attach to Jira or hand off).

Building outside the cloned repo avoids the trap where copied source files get
picked up by the project's build globs and break the build.

## How the work is split

**You do the thinking; the scripts do the mechanics.** Deciding which files are
"result-affecting math" and writing each note requires reading and understanding
the game — that is your job. The only deterministic, no-judgment steps — copying
the chosen files verbatim and rendering the spreadsheet in the exact house format —
are three stdlib-only scripts so their output is always identical:

- `scripts/copy_files.py` — flatten-copies the files you chose into the folder.
- `scripts/build_description_xlsx.py` — writes `description.xlsx` and prints the
  `File | Note` summary table you show the user.
- `scripts/make_zip.py` — writes the clean `NetherlandsFiles.zip` (pass `--zip-out`).

All three read **one manifest you assemble** (the product of your analysis):

```json
{
  "title": "StarsBonanza3x3",
  "out":   "/tmp/StarsBonanza3x3-nl/NetherlandsFiles",
  "files": [
    {"src": "/abs/.../src/StarsBonanza3x3/Config/V90/GameProperties.json", "note": "Math configuration for V90 RTP variant"},
    {"src": "/abs/.../src/StarsBonanza3x3/Config/V96/GameProperties.json", "note": "Math configuration for V96 RTP variant"},
    {"src": "/abs/.../src/StarsBonanza3x3/Game/BaseRound.cs",              "note": "Base round entry point"},
    {"src": "/abs/.../src/StarsBonanza3x3/Game/BaseSpin.cs",               "note": "Base spin logic"}
  ]
}
```

## Workflow

```
- [ ] 1. Resolve the game source folder (repo must be cloned already)
- [ ] 2. Analyse the game and decide the file set
- [ ] 3. Read each chosen file, write its note → assemble the manifest
- [ ] 4. Copy + build the xlsx + zip (run the three scripts)
- [ ] 5. Verify, then show the summary table
```

### 1. Resolve the game source folder

The repo is expected to be already cloned (the `task-netherlands-files` skill handles
cloning). The game source lives at `<repo-root>/src/<GameName>/`.

- `GameName` is the C# project name (e.g. `StarsBonanza3x3`) — it matches the folder
  name under `src/`.
- Confirm the folder exists before proceeding. The display title for the xlsx is the
  `GameName` exactly as it appears in the folder name.
- If the path is uncertain, list `src/` to confirm.

### 2. Analyse the game and decide the file set

Inventory the source first, then apply the one test to every file:
**"does this carry result-affecting math?"**

#### Bandit repo structure reference

```
src/
└── <GameName>/
    ├── Config/
    │   ├── V90/
    │   │   ├── GameProperties.json   ← math config (reels, paytable, bets, features)
    │   │   ├── Install.xml           ← deployment config — EXCLUDE
    │   │   ├── EmptyReels.xml        ← client display only — EXCLUDE
    │   │   └── SkinMapping.xml       ← client display only — EXCLUDE
    │   ├── V92/ ... V94/ ... V96/   (same layout per variant)
    ├── Game/                         ← core game logic C# files
    ├── Features/                     ← feature-specific C# files (free spins, bonus, etc.)
    ├── Behaviours/TestScenarios/     ← EXCLUDE (test scenarios)
    └── SDK/                          ← shared SDK — include only referenced win-utils
```

**Include (definite):**

| Source | Which files |
|--------|-------------|
| `Config/V<XX>/GameProperties.json` | One per RTP variant that exists (V90, V92, V94, V96). This is the primary math config: reel strips, paytable weights, bet sizes, feature trigger probabilities, RTP target. Include **all variants present**. |
| `Game/**/*.cs` | Every `.cs` that computes rounds, spins, feature triggers, or wins. Read each file — include if result-affecting. Typical examples: `BaseRound.cs`, `BaseSpin.cs`, `FreeSpin.cs`, `BonusRound.cs`, `WinCalculator.cs`, `Helpers.cs`. |
| `Features/**/*.cs` | Feature-specific logic (free spins, collect, bonus game, hold, respin, etc.). Same rule — read the file and include only if result-affecting. |
| SDK win-util | Any SDK or shared utility the game calls for win calculations. Detect with `grep -rlE 'LinesUtils\|WaysUtils\|WinUtils' src/<GameName>/` and include the referenced file if found under `SDK/`. |

**Exclude (never):**

- `Config/V<XX>/Install.xml` — module ID and deployment metadata, not math.
- `Config/V<XX>/EmptyReels.xml` — initial visual reel state for the client, not math.
- `Config/V<XX>/SkinMapping.xml` — client skin configuration, not math.
- `rng.config.json` — RNG provider selection, not math.
- `Behaviours/TestScenarios/**` — NCheat and test scenario definitions.
- `src/<GameName>.Tests/**` — unit and RTP tests.
- `src/<GameName>.Tools/**` — code generation tools.
- Pure model/DTO classes (state containers with no logic: `GameRound.cs`, `SpinResult.cs`,
  `Prize.cs`, etc.).
- `Program.cs`, launcher files, integration adapters, stats/simulation drivers.

**Judgment calls (read the file, then decide):**

- **Dispatcher or entry-point `GameLogic.cs`** — drop it when a dedicated round file
  exists (`BaseRound.cs`, `BonusRound.cs`); it is just action routing. Keep only when
  it *is* the substantive entry point.
- **`Helpers.cs` or thin utilities** (only empty-spin creation or label strings, no
  result-affecting logic) — when in doubt, keep. Over-including is harmless; silently
  dropping math is not.
- **Serializer / deserializer files** — drop if they only persist and restore state;
  keep only if they re-compute result-affecting math (rare).
- **SDK files** — include only the win-util the game actually calls. Do not include the
  full SDK or framework helpers.

If a file's role is genuinely unclear, **ask** rather than guess.

### 3. Read each file, write its note → assemble the manifest

For every file you include, **read it** and write one short, content-based note about
*what it does for the math* — not how the code is written. A generic note for a file
you did not open is a defect.

**Config notes:**

| File | Note |
|------|------|
| `GameProperties.json` (V90) | `Math configuration for V90 RTP variant` |
| `GameProperties.json` (V92) | `Math configuration for V92 RTP variant` |
| `GameProperties.json` (V94) | `Math configuration for V94 RTP variant` |
| `GameProperties.json` (V96) | `Math configuration for V96 RTP variant` |

When only two variants exist (e.g. V92 and V96), use the variant number exactly.

**Logic / win-util notes (templates — read the file to confirm):**

| File | Note |
|------|------|
| `BaseRound.cs` | `Base round entry point` (add `for Base Bet` if a BonusBetRound also exists) |
| `BonusRound.cs` · `FreeSpinsRound.cs` · `BuyBonusRound.cs` | `Bonus round logic` · `Free spins round logic` · `Buy bonus round logic` |
| `BaseSpin.cs` · `FreeSpin.cs` · `BonusSpin.cs` | `Base spin logic` · `Free spins logic` · `Bonus spin logic` |
| `WinCalculator.cs` · `WinHelper.cs` | `Win calculation logic` · `Win calculation helper` |
| `Helpers.cs` · `BoardHelper.cs` | `General helper functions` · `Board generation helper` |
| `LinesUtils.cs` · `WaysUtils.cs` | `Lines win calculation algorithm` · `Ways win calculation algorithm` |

For **game-specific feature files** there is no template — read them and compress to
one specific line (e.g. `CollectFeature.cs` → "Wild collect feature logic";
`HoldAndRespin.cs` → "Hold and respin feature logic").

Write the manifest to a temp path (e.g. `/tmp/<GameName>_manifest.json`), ordering
files **config variants → entry rounds → spins → feature logic → win-util**.

### 4. Copy + build + zip (deterministic scripts)

```bash
SKILL=.cursor/skills/netherlands-cert-files/scripts
python3 "$SKILL/copy_files.py"             --manifest /tmp/<GameName>_manifest.json
python3 "$SKILL/build_description_xlsx.py" --manifest /tmp/<GameName>_manifest.json
python3 "$SKILL/make_zip.py"               --manifest /tmp/<GameName>_manifest.json \
    --zip-out "/tmp/<GameName>-nl/NetherlandsFiles.zip"
```

Run scripts from the `bandit-agent-tools` repo root so the `SKILL` path resolves.
The manifest's `out` is the throwaway temp dir; the zip at `--zip-out` is the
deliverable.

`copy_files.py` **aborts if any `src` is missing or two sources collide on one
basename**, so a typo cannot silently drop a math file. `build_description_xlsx.py`
**refuses to write a row with an empty note**. Any `python3` works; no install needed.

### 5. Verify, then show the summary table

- Confirm the temp `out` folder holds the copied files and `description.xlsx`.
- Confirm the zip was written at `--zip-out`.
- **Show the user the `File | Note` summary table** (the Markdown table
  `build_description_xlsx.py` printed — relay it verbatim), then state the file count
  and zip path.
- Report any judgment calls made (e.g. "excluded `Install.xml` — deployment config
  only"; "kept `Helpers.cs` — contains spin-result helper used in win calculation").

## description.xlsx format (what the script produces)

Sheet `data`, gridlines off, font Arial 10. Row 1 = game display name in `A1`.
Row 2 = bold header `File` | `Note`. Row 3+ = one row per file (`filename` | `note`).
Column A ≈ 47 wide, column B ≈ 108. Use the real game name as the title.

## Files in this skill

- `scripts/copy_files.py` — deterministic flatten-copy of the manifest's files.
- `scripts/build_description_xlsx.py` — deterministic `description.xlsx` + Markdown summary table (stdlib-only).
- `scripts/make_zip.py` — deterministic clean zip (stdlib-only; `--zip-out`).
