---
name: jira-nailedit
description: Interact with the NaileditGames Jira instance — read issues, post comments, upload and download attachments. Use when the user mentions Jira, NKIT/RGO2 tickets, posting comments, uploading files to Jira, or downloading Jira attachments.
---

# Jira — NaileditGames

## Table of Contents

- [Quick start](#quick-start)
- [MCP vs REST API](#mcp-vs-rest-api)
- [Auth — two modes](#auth--two-modes)
  - [Personal account](#personal-account)
  - [Service account](#service-account)
- [Common operations](#common-operations)
  - [Get issue + list attachments](#get-issue--list-attachments)
  - [Download attachment](#download-attachment)
  - [Upload attachment](#upload-attachment)
  - [Post comment (Atlassian Document Format)](#post-comment-atlassian-document-format)
- [Gotchas](#gotchas)

---

## Quick start

**Instance:** `https://naileditgames.atlassian.net`  
**Cloud ID:** `09f9a965-7757-4b4d-978e-cb466e2a257c`

### Verify credentials

Cloud agents should have `JIRA_TOKEN` (and `JIRA_EMAIL` for personal tokens) pre-configured. Local dev can use `.env` at the repo root.

```bash
# Quick check — both should print "yes" in cloud agents
[ -n "$JIRA_TOKEN" ] && echo "JIRA_TOKEN: yes" || echo "JIRA_TOKEN: no"
[ -n "$JIRA_EMAIL" ] && echo "JIRA_EMAIL: yes" || echo "JIRA_EMAIL: no"
```

### Fetch an issue

Prefer the helper script — it handles auth mode detection and ADF description parsing:

```bash
python3 tools/jira/jira_issue.py RGO2-164
python3 tools/jira/jira_issue.py NKIT-123 --json
```

---

## MCP vs REST API

`.cursor/mcp.json` configures the Atlassian MCP server (`https://mcp.atlassian.com/v1/mcp/authv2`). That MCP requires interactive OAuth in Cursor Desktop and is **not available in cloud agents**.

| Environment | Jira access |
|---|---|
| Cursor Desktop (OAuth connected) | Atlassian MCP tools, or REST API |
| Cloud agents | REST API only — use `tools/jira/jira_issue.py` or curl |

When MCP is unavailable, always fall back to the REST API. Do not block on MCP auth errors.

---

## Auth — two modes

Credentials are resolved in this order:

1. Environment variables `JIRA_TOKEN` / `JIRA_EMAIL` (cloud agents, CI)
2. `.env` at the repo root (local development only)

| Variable | Description |
|---|---|
| `JIRA_TOKEN` | API token (personal or service account) |
| `JIRA_EMAIL` | Email for the account that owns the token (required for personal tokens only) |

Detect token type from the prefix and pick the auth mode:

```bash
# Prefer env vars; fall back to .env for local dev
JIRA_TOKEN="${JIRA_TOKEN:-$(grep '^JIRA_TOKEN=' .env 2>/dev/null | cut -d= -f2-)}"
JIRA_EMAIL="${JIRA_EMAIL:-$(grep '^JIRA_EMAIL=' .env 2>/dev/null | cut -d= -f2-)}"

if [[ "$JIRA_TOKEN" == ATSTT* ]]; then
  # service account — Bearer on api.atlassian.com
  BASE="https://api.atlassian.com/ex/jira/09f9a965-7757-4b4d-978e-cb466e2a257c/rest/api/3"
  AUTH_HEADER="Authorization: Bearer $JIRA_TOKEN"
else
  # personal — Basic Auth on instance URL
  BASE="https://naileditgames.atlassian.net/rest/api/3"
  AUTH_HEADER="Authorization: Basic $(echo -n "$JIRA_EMAIL:$JIRA_TOKEN" | base64)"
fi
```

### Personal account

Uses **Basic Auth** directly on the instance URL:

```bash
curl -u "$JIRA_EMAIL:$JIRA_TOKEN" \
  "https://naileditgames.atlassian.net/rest/api/3/issue/NKIT-123"
```

Token format: `ATATT3x...`

### Service account

Service account tokens from Atlassian Administration **do not work** with Basic Auth on `naileditgames.atlassian.net`. They require **Bearer auth** on the API gateway:

```bash
BASE="https://api.atlassian.com/ex/jira/09f9a965-7757-4b4d-978e-cb466e2a257c/rest/api/3"

curl -H "Authorization: Bearer $JIRA_TOKEN" \
  -H "Accept: application/json" \
  "$BASE/issue/NKIT-123"
```

Token format: `ATSTT3x...`

---

## Common operations

### Get issue + list attachments

```bash
python3 tools/jira/jira_issue.py NKIT-123

# Or with curl after setting BASE and AUTH_HEADER (see Auth section):
curl -s -H "$AUTH_HEADER" "$BASE/issue/NKIT-123?fields=summary,description,attachment,status" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('Summary:', d['fields']['summary'])
print('Status:', d['fields']['status']['name'])
for a in d['fields'].get('attachment', []):
    print(f'  [{a[\"id\"]}] {a[\"filename\"]}  ({a[\"size\"]} bytes)')
"
```

### Download attachment

```bash
curl -s -L -H "$AUTH_HEADER" \
  "$BASE/attachment/content/<id>" \
  -o output_file
```

### Upload attachment

```bash
curl -s -X POST \
  -H "$AUTH_HEADER" \
  -H "X-Atlassian-Token: no-check" \
  -F "file=@/path/to/file.xlsx;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  "$BASE/issue/NKIT-123/attachments" \
  | python3 -c "import json,sys; a=json.load(sys.stdin); print('ID:', a[0]['id'])"
```

### Post comment (Atlassian Document Format)

```bash
python3 -c "
import json
body = {
  'type': 'doc', 'version': 1,
  'content': [{
    'type': 'paragraph',
    'content': [{'type': 'text', 'text': 'Your comment here'}]
  }]
}
print(json.dumps({'body': body}))
" | curl -s -X POST \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d @- \
  "$BASE/issue/NKIT-123/comment" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('Comment ID:', d.get('id'))"
```

---

## Gotchas

- **`ATSTT3x` tokens always fail** with Basic Auth and `naileditgames.atlassian.net` — use Bearer + `api.atlassian.com`
- **`JIRA_EMAIL` is only required** for personal tokens (`ATATT3x...`); service account tokens use Bearer auth alone
- **`cut -d= -f2-`** correctly handles `=` signs inside the token value when reading `.env`
- **`X-Atlassian-Token: no-check`** is required for attachment uploads (CSRF protection bypass)
- Service account must be added to the Jira project with appropriate role (`write:jira-work` scope) — otherwise 403/404 on issue access
- **Issue descriptions are ADF JSON**, not plain text — use `tools/jira/jira_issue.py` or parse `type: doc` content nodes
- **Atlassian MCP is desktop-only** — cloud agents must use the REST API
