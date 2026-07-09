---
name: gamesglobal-gitlab
description: Access and navigate the Games Global GitLab instance at gametechgit.gamesglobal.com. Use when listing game repositories, searching for projects, cloning games, or exploring the naileditgames group structure.
---

# Games Global GitLab

## Authentication

**Instance:** `https://gametechgit.gamesglobal.com`

Credentials should be available as environment variables:

| Variable | Description |
|---|---|
| `GG_GITLAB_USERNAME` | GitLab username |
| `GG_GITLAB_TOKEN` | Personal access token |

If the variables are not set, look them up in `.env` at the project root — that file is for local development only and should not be used in production or cloud agents.

API calls use the `PRIVATE-TOKEN` header with `$GG_GITLAB_TOKEN`:

```bash
curl -s "https://gametechgit.gamesglobal.com/api/v4/..." \
  -H "PRIVATE-TOKEN: $GG_GITLAB_TOKEN"
```

Clone with credentials embedded in URL:

```bash
git clone "https://${GG_GITLAB_USERNAME}:${GG_GITLAB_TOKEN}@gametechgit.gamesglobal.com/naileditgames/<repo>.git"
```

Verify auth before proceeding:

```bash
curl -s "https://gametechgit.gamesglobal.com/api/v4/user" \
  -H "PRIVATE-TOKEN: $GG_GITLAB_TOKEN" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('name'), d.get('username'))"
```

## Group Structure: `naileditgames`

All game projects live under the `naileditgames` group.

### Root-level projects (~36 repos)

Slot games follow the naming convention `Slot-<GameName>` or `slot-<gamename>` (mixed casing). Other root-level projects include tools like `DataExtractionTool` and prototypes.

### Subgroups

| Subgroup | Purpose | Status |
|---|---|---|
| `naileditgames/playchecks` | Legacy HTML game-history viewer per game | Legacy |
| `naileditgames/playreviews` | New JS/TS replacement for playcheck + portugal-reporting | Active |
| `naileditgames/portugal-reporting` | Legacy Portugal regulator string generator | Legacy |
| `naileditgames/proto` | Prototypes | Internal |

**`playreviews`** is the current standard — it replaces both `playchecks` and `portugal-reporting` using a unified JS/TS approach.

## Common API Queries

### List all projects in a group

```bash
curl -s "https://gametechgit.gamesglobal.com/api/v4/groups/naileditgames/projects?per_page=100" \
  -H "PRIVATE-TOKEN: $GG_GITLAB_TOKEN" | \
  python3 -c "import json,sys; [print(p['path_with_namespace']) for p in json.load(sys.stdin)]"
```

### List subgroups

```bash
curl -s "https://gametechgit.gamesglobal.com/api/v4/groups/naileditgames/subgroups?per_page=100" \
  -H "PRIVATE-TOKEN: $GG_GITLAB_TOKEN" | \
  python3 -c "import json,sys; [print(g['full_path']) for g in json.load(sys.stdin)]"
```

### List projects in a subgroup (URL-encode the `/`)

```bash
curl -s "https://gametechgit.gamesglobal.com/api/v4/groups/naileditgames%2Fplayreviews/projects?per_page=100" \
  -H "PRIVATE-TOKEN: $GG_GITLAB_TOKEN" | \
  python3 -c "import json,sys; [print(p['path_with_namespace']) for p in json.load(sys.stdin)]"
```

### Search for a specific project

```bash
curl -s "https://gametechgit.gamesglobal.com/api/v4/groups/naileditgames/projects?search=starsbonanza&per_page=20" \
  -H "PRIVATE-TOKEN: $GG_GITLAB_TOKEN" | \
  python3 -c "import json,sys; [print(p['path_with_namespace'], p['http_url_to_repo']) for p in json.load(sys.stdin)]"
```

## Slot Game Repository Structure

Each slot game is a .NET/C# solution with the following layout:

```
src/
├── <GameName>.sln
├── <GameName>/                    # Main game math service
│   ├── Config/
│   │   ├── V90/                   # RTP variant 90%
│   │   ├── V92/                   # RTP variant 92%
│   │   ├── V94/                   # RTP variant 94%
│   │   └── V96/                   # RTP variant 96%
│   ├── Game/                      # Core game logic
│   ├── Features/                  # Game features (e.g. Collect)
│   ├── Behaviours/TestScenarios/  # NCheat & other test scenarios
│   └── SDK/                       # Shared SDK (RNG, model interfaces)
├── <GameName>.Tests/
│   └── Tests/Rtp/                 # RTP simulation tests
│       ├── RtpTest.cs
│       ├── RtpTestSimulation.cs
│       └── RtpTestResult.cs
└── <GameName>.Tools/              # Code-generation tools (e.g. ReelSets)
```

Each `Config/V<XX>/GameProperties.json` defines the math configuration for that RTP variant.
