#!/usr/bin/env python3
"""
Verify GSBS bet settings for all operator/currency links.

Reads links.json, authenticates each session, calls play/refreshes API,
and reports actual maxBet / defaultBet / availableBets for each combination.

Usage:
    python verify_gsbs.py \
        --links-file path/to/links.json \
        --axiom-name gtp727 \
        --module-id 105001 \
        --client-id 50300 \
        --out-file path/to/results.json
"""

import argparse
import json
import sys
import uuid
from pathlib import Path

import requests


CURRENCY_MULTIPLIERS = {
    "GBP": 1,
    "EUR": 1,
    "USD": 1,
    "MYR": 5,
    "ZAR": 10,
    "ZMW": 20,
    "PHP": 50,
    "JPY": 100,
    "CLP": 200,
    "MXN": 20,
}


def login(axiom_name: str, server_id: int, external_token: str) -> str:
    """Exchange external token for a JWT session token. Returns Bearer token."""
    url = (
        f"https://api5-rhel1-{axiom_name}.installprogram.eu"
        f"/casino/user/public/v1/accounts/login/token"
        f"?fields=core%2Cbalance%2Csession"
    )
    payload = {
        "sessionProductId": server_id,
        "numLaunchTokens": 1,
        "environment": {"clientTypeId": 40, "languageCode": "en"},
        "deviceAttributes": [
            {"shortCode": "bn", "value": "Apple"},
            {"shortCode": "dos", "value": "OS X"},
            {"shortCode": "dosv", "value": "26.1.0"},
            {"shortCode": "it", "value": "false"},
            {"shortCode": "mktn", "value": ""},
            {"shortCode": "mbb", "value": "Chrome"},
            {"shortCode": "mbbv", "value": "142.0.7444.176"},
            {"shortCode": "mdln", "value": ""},
            {"shortCode": "ua", "value": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"},
            {"shortCode": "ff", "value": "desktop"},
        ],
        "token": external_token,
    }
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "Origin": f"https://mobile-app1-{axiom_name}.installprogram.eu",
        "Referer": f"https://mobile-app1-{axiom_name}.installprogram.eu/",
        "X-ClientTypeId": "40",
        "X-CorrelationId": str(uuid.uuid4()),
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # Response structure: tokens.launchTokens[0] contains the JWT
    return data["tokens"]["launchTokens"][0]


def get_bet_limits(axiom_name: str, jwt: str, module_id: int, client_id: int, product_id: int) -> dict:
    """Call play/refreshes and return availableBetLimits."""
    url = (
        f"https://api5-rhel1-{axiom_name}.installprogram.eu"
        f"/casino/play/public/v1/games2/module/{module_id}/client/{client_id}/play/refreshes"
    )
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Accept": "*/*",
        "Accept-Language": "en",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
        "Origin": f"https://mobile-app1-{axiom_name}.installprogram.eu",
        "Referer": f"https://mobile-app1-{axiom_name}.installprogram.eu/",
        "X-ClientTypeId": "40",
        "X-CorrelationId": str(uuid.uuid4()),
        "X-Route-ProductId": str(product_id),
        "X-Route-ModuleId": str(module_id),
    }
    resp = requests.post(url, json={"context": {}, "gameRequest": {}}, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return _find_key(data, "availableBetLimits")


def _find_key(obj, key):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            r = _find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_key(v, key)
            if r is not None:
                return r
    return None


def extract_token_from_url(url: str) -> str:
    from urllib.parse import urlparse, parse_qs
    qs = parse_qs(urlparse(url).query)
    return qs.get("externaltoken", [None])[0]


def status_label(actual: float, expected: float | None, warn_ratio: float = 0.5) -> str:
    if expected is None:
        return "?"
    if actual > expected * 1.001:
        return "ERROR (too high)"
    if actual < expected * warn_ratio:
        return f"WARN (low, expected ~{expected})"
    return "OK"


def main():
    parser = argparse.ArgumentParser(description="Verify GSBS bet settings via API")
    parser.add_argument("--links-file", required=True, help="Path to links.json")
    parser.add_argument("--axiom-name", required=True, help="Axiom name, e.g. gtp727")
    parser.add_argument("--module-id", type=int, required=True, help="Game module ID, e.g. 105001")
    parser.add_argument("--client-id", type=int, default=50300, help="Client ID (default 50300 desktop)")
    parser.add_argument("--out-file", default=None, help="Output JSON results file")
    parser.add_argument("--max-win", type=float, default=None,
                        help="Game max-win multiplier (e.g. 5486.5) for calculating expected MaxBet from exposure presets")
    args = parser.parse_args()

    links_data: dict = json.loads(Path(args.links_file).read_text())
    results = {}
    rows = []

    for op_id_str, op_info in links_data.items():
        operator_id = op_info["operatorId"]
        operator_name = op_info["operatorName"]
        server_id = op_info["serverId"]
        currency_links: dict = op_info["currencyLinks"]

        op_results = {
            "operatorId": operator_id,
            "operatorName": operator_name,
            "serverId": server_id,
            "currencies": {},
        }

        for currency, launch_url in currency_links.items():
            external_token = extract_token_from_url(launch_url)
            if not external_token:
                print(f"  [{operator_id}/{currency}] SKIP - no externaltoken in URL")
                op_results["currencies"][currency] = {"error": "no externaltoken"}
                continue

            print(f"  [{operator_id}/{currency}] Logging in with token={external_token}...", end=" ", flush=True)
            try:
                jwt = login(args.axiom_name, server_id, external_token)
                limits = get_bet_limits(args.axiom_name, jwt, args.module_id, args.client_id, server_id)
                if limits is None:
                    raise ValueError("availableBetLimits not found in response")

                max_bet = limits.get("maxBet")
                min_bet = limits.get("minBet")
                default_bet = limits.get("defaultBet") or _find_key(limits, "defaultBet")
                available_bets = limits.get("availableBets", [])
                highest_available = max(available_bets) if available_bets else None

                print(f"maxBet={max_bet} defaultBet={default_bet} bets[{len(available_bets)}]")
                op_results["currencies"][currency] = {
                    "maxBet": max_bet,
                    "minBet": min_bet,
                    "defaultBet": default_bet,
                    "highestAvailableBet": highest_available,
                    "availableBets": available_bets,
                }
                rows.append({
                    "operatorId": operator_id,
                    "operatorName": operator_name,
                    "currency": currency,
                    "maxBet": max_bet,
                    "defaultBet": default_bet,
                    "highestAvailableBet": highest_available,
                })
            except Exception as e:
                print(f"ERROR: {e}")
                op_results["currencies"][currency] = {"error": str(e)}

        results[op_id_str] = op_results

    # Print summary table
    print("\n" + "=" * 100)
    print(f"{'OperatorID':<12} {'OperatorName':<35} {'CCY':<6} {'MaxBet':>10} {'DefaultBet':>12} {'HighestAvail':>14}")
    print("-" * 100)
    for r in rows:
        print(
            f"{r['operatorId']:<12} {r['operatorName']:<35} {r['currency']:<6} "
            f"{str(r['maxBet']):>10} {str(r['defaultBet']):>12} {str(r['highestAvailableBet']):>14}"
        )
    print("=" * 100)

    if args.out_file:
        Path(args.out_file).write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to {args.out_file}")


if __name__ == "__main__":
    main()
