---
name: task-netherlands-files
description: >-
  Clone a Bandit game repo, generate the Netherlands certification Files package
  (C# math source + description.xlsx), zip the result, and attach to Jira. Use when
  asked to do the Netherlands cert files task, prepare a NL certification package for a
  game, process a Jira ticket requesting Netherlands certification files, or generate
  and deliver the NetherlandsFiles.zip.
---

# Netherlands Files Task

End-to-end workflow: clone a Bandit game repo → generate the Netherlands certification
Files package → attach to Jira.

**Reference skills:**
- `gamesglobal-gitlab` — repo discovery and cloning
- `netherlands-cert-files` — file selection, description.xlsx, and zip generation
- `jira-nailedit` — reading tickets, uploading attachments, posting comments

## Task Progress

```
- [ ] Game identified (repo name resolved)
- [ ] Jira ticket read and game confirmed (Jira-triggered tasks)
- [ ] Repo cloned into tmp/
- [ ] Netherlands Files package generated (netherlands-cert-files skill)
- [ ] Zip attached to Jira + summary comment posted (Jira-triggered tasks)
```

---

## Strategy: Jira-triggered vs standalone

### Jira-triggered tasks

If the task includes a Jira ticket key (e.g. `NKIT-123`) or the user references a Jira
issue, use the `jira-nailedit` skill to:

1. Read the issue summary and description — extract the game name from the summary

Then proceed with the full process and post results back to Jira (see [Post to Jira](#post-to-jira)).

### Standalone tasks

The user provides the game name directly. Skip the Jira steps unless explicitly asked.

---

## Process

### 1. Identify the repo

Resolve the GitLab repo name from the game name. Use the `gamesglobal-gitlab` skill:

```bash
source .env
curl -s "https://gametechgit.gamesglobal.com/api/v4/groups/naileditgames/projects?search=<GameName>&per_page=20" \
  -H "PRIVATE-TOKEN: $GG_GITLAB_TOKEN" | \
  python3 -c "import json,sys; [print(p['path_with_namespace'], p['http_url_to_repo']) for p in json.load(sys.stdin)]"
```

Repo names follow the pattern `Slot-<GameName>` or `slot-<gamename>`.

**If multiple repos match**, stop and ask the user — do not guess.

### 2. Clone the repo

```bash
source .env
git clone "https://${GG_GITLAB_USERNAME}:${GG_GITLAB_TOKEN}@gametechgit.gamesglobal.com/naileditgames/<repo>.git" tmp/<repo>
```

Confirm `tmp/<repo>/src/<GameName>/` exists before proceeding.

### 3. Generate the Netherlands Files package

Apply the **`netherlands-cert-files`** skill with `tmp/<repo>` as the repo root.

The skill will:
- Analyse the game source under `tmp/<repo>/src/<GameName>/`
- Select the result-affecting math files (C# logic only — no GameProperties.json)
- Produce a flat folder + `description.xlsx` in `tmp/<GameName>-nl/NetherlandsFiles/`
- Write the zip to `tmp/<GameName>-nl/NetherlandsFiles.zip`

### 4. Post to Jira

**Only for Jira-triggered tasks.**

Use the `jira-nailedit` skill to:

**4a. Attach the zip:**

```bash
source .env
# (set up JIRA auth — see jira-nailedit skill)

curl -s -X POST \
  -H "$AUTH_HEADER" \
  -H "X-Atlassian-Token: no-check" \
  -F "file=@$(pwd)/tmp/<GameName>-nl/NetherlandsFiles.zip;type=application/zip" \
  "$BASE/issue/<TICKET>/attachments" \
  | python3 -c "import json,sys; a=json.load(sys.stdin); print('Attached ID:', a[0]['id'])"
```

**4b. Post a summary comment:**

The comment must contain three sections:

1. A brief introduction line.
2. **Included files** — relay the `File | Note` table printed by `build_description_xlsx.py`.
3. **Excluded files** — list every `.cs` file found in the game's `Game/` folder that
   was **not** included in the zip, with a short reason for each exclusion. Produce this
   list by diffing the files you analysed against the manifest. Typical reasons: "pure
   state container / no logic", "launcher / entry-point boilerplate", "test helper",
   "serializer only".

Example comment structure (use Atlassian Document Format):

```
Netherlands certification Files package generated for <GameName>.

*Included files (<N>):*

| File | Note |
|------|------|
| BaseRound.cs | Base round entry point |
| BaseSpin.cs  | Base spin logic        |
...

*Excluded from Game/ (<M> files):*

| File | Reason |
|------|--------|
| GameRound.cs   | Pure state container — no result-affecting logic |
| SpinResult.cs  | DTO, persists state only |
| Program.cs     | Launcher / entry-point boilerplate |
...

NetherlandsFiles.zip is attached to this ticket.
```

---

## Tips

- Always use `tmp/` for cloned repos. The cloned repo is only needed during generation —
  it can be removed afterwards.
- `tmp/<GameName>-nl/` and its contents (loose files + zip) are regenerable and are
  not committed (`tmp/` is gitignored).
- If the game name in the Jira ticket is ambiguous or missing, comment on the ticket
  asking for clarification before proceeding.

## Expected output per run

```
tmp/<GameName>-nl/
├── manifest.json             build manifest
├── NetherlandsFiles/
│   ├── BaseRound.cs
│   ├── BaseSpin.cs
│   ├── ...
│   └── description.xlsx
└── NetherlandsFiles.zip      ← deliverable attached to Jira
```
