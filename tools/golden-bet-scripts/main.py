#!/usr/bin/env python3
"""
Golden Bet Scripts Link Generator

Generates Axiom launch links for Golden Bet Scripts testing across all operators
and their supported currencies.

Usage:
    python main.py --axiom-name <name> --api-key <key> --game-name <game> --username <user>
    python main.py --axiom-name <name> --api-key <key> --game-name <game> --username <user> --output links.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from operators import OPERATOR_DATA_SET, OperatorData
from web_config import fetch_web_config, upload_web_config, set_default_currency
from create_user import create_user


def build_launch_link(axiom_name: str, game_name: str, operator_name_link: str, token: str) -> str:
    return (
        f"https://mobile-app1-{axiom_name}.installprogram.eu"
        f"/mobilewebservices/casino/game/launch/{operator_name_link}/{game_name}"
        f"/en?logintype=VanguardSessionToken&externaltoken={token}"
    )


def prepare_test_cases_per_currency(operators: list[OperatorData]) -> Dict[str, list]:
    mapping: Dict[str, list] = {}
    for op in operators:
        for currency in op.currencies:
            mapping.setdefault(currency, []).append(op)
    return mapping


def generate_links(axiom_name: str, api_key: str, game_name: str, username: str) -> dict:
    test_cases = prepare_test_cases_per_currency(OPERATOR_DATA_SET)

    print(f"Fetching Web.config from Axiom '{axiom_name}'...")
    web_config = fetch_web_config(axiom_name, api_key)

    result: dict = {}
    index = 0

    for currency, operators in test_cases.items():
        print(f"\n[{currency}] Updating Web.config default currency...")
        updated_config = set_default_currency(web_config, currency)
        upload_web_config(axiom_name, api_key, updated_config)

        for op in operators:
            print(f"  [{currency}] Creating user & link for operator '{op.operator_name}' (id={op.operator_id})")
            index += 1
            token = f"{username}{index}"

            create_user(token, str(op.server_id), axiom_name)
            link = build_launch_link(axiom_name, game_name, op.operator_name_link, token)

            if op.operator_id not in result:
                result[op.operator_id] = {
                    "operatorId": op.operator_id,
                    "serverId": op.server_id,
                    "operatorName": op.operator_name,
                    "operatorNameLink": op.operator_name_link,
                    "currencyLinks": {},
                }

            result[op.operator_id]["currencyLinks"][currency] = link

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate Axiom launch links for Golden Bet Scripts testing.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--axiom-name", required=True, help="Axiom environment name (e.g. myenv01)")
    parser.add_argument("--api-key", required=True, help="Axiom API key")
    parser.add_argument("--game-name", required=True, help="Game name as registered in Axiom (e.g. SlotGame)")
    parser.add_argument("--username", required=True, help="Base username; tokens are suffixed with an index")
    parser.add_argument(
        "--output",
        default="golden-bet-links.json",
        help="Output JSON file path",
    )

    args = parser.parse_args()

    try:
        links = generate_links(
            axiom_name=args.axiom_name,
            api_key=args.api_key,
            game_name=args.game_name,
            username=args.username,
        )
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(links, indent=2))
    print(f"\nDone. {len(links)} operators written to {output_path}")


if __name__ == "__main__":
    main()
