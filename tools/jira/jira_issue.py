#!/usr/bin/env python3
"""Fetch a Jira issue from the NaileditGames instance.

Resolves credentials from environment variables (cloud agents) or .env (local dev),
detects personal vs service-account token type, and prints issue fields.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CLOUD_ID = "09f9a965-7757-4b4d-978e-cb466e2a257c"
INSTANCE_URL = "https://naileditgames.atlassian.net"


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def resolve_credentials() -> tuple[str, str | None]:
    token = os.environ.get("JIRA_TOKEN", "").strip()
    email = os.environ.get("JIRA_EMAIL", "").strip() or None

    if not token:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        dotenv = load_dotenv(env_file)
        token = dotenv.get("JIRA_TOKEN", "").strip()
        if not email:
            email = dotenv.get("JIRA_EMAIL", "").strip() or None

    if not token:
        raise SystemExit(
            "JIRA_TOKEN is not set. Export JIRA_TOKEN (and JIRA_EMAIL for personal tokens) "
            "or add them to .env at the repo root."
        )

    if not token.startswith("ATSTT") and not email:
        raise SystemExit(
            "JIRA_EMAIL is required for personal API tokens (ATATT...). "
            "Service account tokens (ATSTT...) use Bearer auth and do not need JIRA_EMAIL."
        )

    return token, email


def jira_request(token: str, email: str | None, path: str) -> dict:
    if token.startswith("ATSTT"):
        base = f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/3"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
    else:
        base = f"{INSTANCE_URL}/rest/api/3"
        auth = base64.b64encode(f"{email}:{token}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
        }

    url = f"{base}{path}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Jira API error {exc.code} for {url}: {body}") from exc


def adf_to_text(node: object) -> str:
    parts: list[str] = []

    def walk(item: object) -> None:
        if isinstance(item, dict):
            node_type = item.get("type")
            if node_type == "text":
                parts.append(str(item.get("text", "")))
            elif node_type == "inlineCard":
                url = item.get("attrs", {}).get("url")
                if url:
                    parts.append(url)
            elif node_type == "hardBreak":
                parts.append("\n")
            for child in item.get("content", []):
                walk(child)
            if node_type in {"paragraph", "heading", "listItem"}:
                parts.append("\n")
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(node)
    text = "".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch a NaileditGames Jira issue")
    parser.add_argument("issue_key", help="Issue key, e.g. NKIT-123 or RGO2-164")
    parser.add_argument(
        "--fields",
        default="summary,description,status,attachment",
        help="Comma-separated Jira fields to fetch",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON response instead of a human-readable summary",
    )
    args = parser.parse_args()

    token, email = resolve_credentials()
    issue = jira_request(token, email, f"/issue/{args.issue_key}?fields={args.fields}")

    if args.json:
        print(json.dumps(issue, indent=2))
        return

    fields = issue.get("fields", {})
    print(f"Key: {issue.get('key')}")
    print(f"Summary: {fields.get('summary', '')}")
    status = fields.get("status") or {}
    print(f"Status: {status.get('name', '')}")

    description = fields.get("description")
    if description:
        print("Description:")
        print(adf_to_text(description))
    else:
        print("Description: (empty)")

    attachments = fields.get("attachment") or []
    if attachments:
        print("Attachments:")
        for attachment in attachments:
            print(
                f"  [{attachment.get('id')}] {attachment.get('filename')} "
                f"({attachment.get('size')} bytes)"
            )


if __name__ == "__main__":
    main()
