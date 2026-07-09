---
name: jira-nailedit
description: Interact with the NaileditGames Jira instance — read issues, post comments, upload and download attachments. Use when the user mentions Jira, NKIT tickets, posting comments, uploading files to Jira, or downloading Jira attachments.
---

# Jira — NaileditGames

## Table of Contents

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

## Auth — two modes

**Instance:** `https://naileditgames.atlassian.net`  
**Cloud ID:** `09f9a965-7757-4b4d-978e-cb466e2a257c`

Credentials should be available as environment variables:

| Variable | Description |
|---|---|
| `JIRA_TOKEN` | API token (personal or service account) |
| `JIRA_EMAIL` | Email for the account that owns the token |

If the variables are not set, look them up in `.env` at the project root — that file is for local development only and should not be used in production or cloud agents.

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
# Base URL structure:
# https://api.atlassian.com/ex/jira/<cloudId>/rest/api/3
# cloudId is fetched once: curl -s https://naileditgames.atlassian.net/_edge/tenant_info | python3 -c "import json,sys; print(json.load(sys.stdin)['cloudId'])"
# naileditgames cloudId: 09f9a965-7757-4b4d-978e-cb466e2a257c

CLOUD_ID=$(curl -s https://naileditgames.atlassian.net/_edge/tenant_info | python3 -c "import json,sys; print(json.load(sys.stdin)['cloudId'])")
BASE="https://api.atlassian.com/ex/jira/$CLOUD_ID/rest/api/3"

curl -H "Authorization: Bearer $JIRA_TOKEN" \
  -H "Accept: application/json" \
  "$BASE/issue/NKIT-123"
```

Token format: `ATSTT3x...`

Always detect the token type from `.env` and pick the right auth mode:

```bash
JIRA_TOKEN=$(grep '^JIRA_TOKEN=' .env | cut -d= -f2-)
if [[ "$JIRA_TOKEN" == ATSTT* ]]; then
  # service account — Bearer on api.atlassian.com
  CLOUD_ID=$(curl -s https://naileditgames.atlassian.net/_edge/tenant_info | python3 -c "import json,sys; print(json.load(sys.stdin)['cloudId'])")
  BASE="https://api.atlassian.com/ex/jira/$CLOUD_ID/rest/api/3"
  AUTH_HEADER="Authorization: Bearer $JIRA_TOKEN"
else
  # personal — Basic Auth on instance URL
  JIRA_EMAIL=$(grep '^JIRA_EMAIL=' .env | cut -d= -f2-)
  BASE="https://naileditgames.atlassian.net/rest/api/3"
  AUTH_HEADER="Authorization: Basic $(echo -n "$JIRA_EMAIL:$JIRA_TOKEN" | base64)"
fi
```

---

## Common operations

### Get issue + list attachments

```bash
curl -s -H "$AUTH_HEADER" "$BASE/issue/NKIT-123?fields=summary,attachment" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('Summary:', d['fields']['summary'])
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
- **`cut -d= -f2-`** correctly handles `=` signs inside the token value
- **`X-Atlassian-Token: no-check`** is required for attachment uploads (CSRF protection bypass)
- Service account must be added to the Jira project with appropriate role (`write:jira-work` scope) — otherwise 403/404 on issue access
