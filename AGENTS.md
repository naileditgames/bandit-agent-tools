# AGENTS.md

Guidance for AI agents working in this repository.

---

## Skills first

Before starting any task, check `.cursor/skills/` for a relevant skill and **read it** before doing anything else. Skills contain the authoritative workflow, edge cases, and exact CLI patterns for each task type. Do not improvise a workflow that a skill already covers.

| Task | Skill to read first |
|---|---|
| Netherlands cert files for a game | `task-netherlands-files` |
| RTP simulation or RNG cert CSV | `task-bandit-simulations` |
| Clone or search a game repo | `gamesglobal-gitlab` |
| Build a Bandit game server | `bandit-server` |
| Read/comment/attach on a Jira ticket | `jira-nailedit` |

---

## Credentials

Environment variables (`GG_GITLAB_TOKEN`, `JIRA_TOKEN`, etc.) are available directly in the agent environment — no `.env` file exists on disk. Never attempt to read, create, or source a `.env` file when running as an agent.

---

## Working directory conventions

- Clone all game repos into `tmp/<repo-name>/` — never elsewhere in the workspace.
- Write all simulation results and cert build artefacts to `/tmp/<GameName>-*/` (system temp) or `tmp/results/` — never to `src/` or the repo root.
- `tmp/` is gitignored. Do not commit anything under it.
- Artefacts in `/tmp/` (loose files, zips) are regenerable — the zip attached to Jira is the only deliverable that matters.

---

## Game name resolution

Bandit repo names follow the pattern `slot-<gamename>` (lowercase, no spaces). When a user provides a game name, search GitLab before assuming the exact repo name — use the `gamesglobal-gitlab` skill.

If a search returns multiple matching repos, **stop and ask** the user which one to use. Never guess.

---

## File selection for cert packages

When building a Netherlands cert package, the test is: **does this file carry result-affecting math?**

- Include: `GameProperties.json` per variant, all `Game/Logic/**/*.cs`, all `RechargeData*/*.cs`, referenced SDK win-utils.
- Exclude: `Install.xml`, `EmptyReels.xml`, `SkinMapping.xml`, `rng.config.json`, `TestScenarios/`, `*.Tests/`, `*.Tools/`, `Program.cs`, pure model/DTO classes, serializers.
- When uncertain about a file, read it — then decide. Over-including is safer than silently dropping math.

The `netherlands-cert-files` skill has the full decision table.

---

## `GameProperties.json` filename collisions

Multiple variants each produce a `GameProperties.json`. These collide in the flat `NetherlandsFiles/` output folder. Always copy them to disambiguated temp paths (`GameProperties-V90.json`, etc.) before building the manifest — `copy_files.py` aborts on basename collisions.

---

## Do not commit generated artefacts

Never `git add` or commit:
- Cloned game repos under `tmp/`
- Simulation CSVs, JSONs, or Excel files
- `/tmp/` cert build folders or zips
- `.env` files
