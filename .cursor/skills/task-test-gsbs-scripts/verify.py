#!/usr/bin/env python3
"""
GSBS Verification Script — opens each operator/currency game link, extracts
DefaultBet and MaxBet from the bet panel, verifies against expected limits,
and captures a screenshot per combination.

Usage:
    python3 verify.py --links links.json --max-win 5486.5 --output-dir /path/to/output

Dependencies (system Python, no venv needed):
    pip3 install playwright
    python3 -m playwright install chromium
"""

import argparse
import asyncio
import json
import math
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

# ---------------------------------------------------------------------------
# Currency configuration
# ---------------------------------------------------------------------------

CURRENCY_MULTIPLIERS: dict[str, int] = {
    "GBP": 1,
    "MYR": 5,
    "ZAR": 10,
    "ZMW": 20,
    "PHP": 50,
    "JPY": 100,
    "CLP": 200,
    "EUR": 1,
    "USD": 1,
}

# ---------------------------------------------------------------------------
# Operator expected-value tables
# All monetary amounts are in the base-currency smallest unit (GBP pence).
# ---------------------------------------------------------------------------

# Exposure-based operators: operatorId → GBP exposure amount (£)
EXPOSURE_OPERATORS: dict[int, int] = {
    8050000: 50_000,
    8100000: 100_000,
    8125000: 125_000,
    8250000: 250_000,
    8500000: 500_000,
    8750000: 750_000,
    8000037: 140_000,   # Greece140K — capped at £20.00 (2000p)
    8111000: 1_000_000,
    8112000: 2_000_000,
    8113000: 3_000_000,
    8115000: 5_000_000,
    8110000: 10_000_000,
    8000006: 250_000,
    8000007: 500_000,
    8000008: 750_000,
}

# Fixed MaxBet operators: operatorId → MaxBet ceiling in GBP pence
FIXED_MAXBET_PENCE: dict[int, int] = {
    8001099: 200,    # £2.00
    8000005: 500,    # £5.00
    8000010: 1000,   # £10.00
    8000020: 2000,   # £20.00
    8000050: 5000,   # £50.00
    8000100: 10000,  # £100.00
    8000150: 15000,  # £150.00
    8000031: 100,    # €1.00 Germany Quickfire
}

# Fixed DefaultBet: operatorId → {currency → pence}
FIXED_DEFAULTBET_PENCE: dict[int, dict[str, int]] = {
    8000001: {"GBP": 100},   # £1.00
    8000002: {"GBP": 200},   # £2.00
    8001099: {"GBP": 200},   # £2.00
    8000031: {"EUR": 100},   # €1.00
    8000006: {"USD": 200},   # $2.00
    8000007: {"USD": 200},   # $2.00
    8000008: {"USD": 200},   # $2.00
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def calc_exposure_maxbet_pence(exposure_gbp: int, max_win: float) -> int:
    return math.floor(exposure_gbp * 100 / max_win)


def get_expected_maxbet_smallest(op_id: int, currency: str, max_win: float) -> int | None:
    """Return MaxBet ceiling in smallest currency units, or None for 'game default'."""
    if op_id in EXPOSURE_OPERATORS:
        base = calc_exposure_maxbet_pence(EXPOSURE_OPERATORS[op_id], max_win)
        if op_id == 8000037:          # Greece: capped at £20.00
            base = min(base, 2000)
        return base * CURRENCY_MULTIPLIERS.get(currency, 1)
    if op_id in FIXED_MAXBET_PENCE:
        return FIXED_MAXBET_PENCE[op_id] * CURRENCY_MULTIPLIERS.get(currency, 1)
    return None


def get_expected_defaultbet_smallest(op_id: int, currency: str) -> int | None:
    """Return expected DefaultBet in smallest currency units, or None for 'game default'."""
    return FIXED_DEFAULTBET_PENCE.get(op_id, {}).get(currency)


def parse_bet_value(raw: str) -> float | None:
    """
    Parse a formatted bet string to a float, handling all supported currencies:

    - GBP/MYR/ZAR/ZMW/PHP: comma = thousands, period = decimal  e.g. "1,234.56"
    - JPY: comma = thousands, no decimal                          e.g. "1,000"
    - CLP: space = thousands, comma = decimal                     e.g. "1 000,00"
    - EUR: comma = decimal (no space thousands at low values)     e.g. "1,00" / "15,00"

    EUR vs JPY disambiguation: if a single comma is followed by exactly 2 digits
    at the end of the string (and no period is present), the comma is a decimal
    separator. If it is followed by 3 digits, it is a thousands separator.
    """
    if not raw:
        return None
    s = raw.strip()
    for sym in ("£", "RM", "R", "K", "₱", "¥", "$", "€"):
        s = s.replace(sym, "")
    s = s.strip()

    # CLP: space thousands + comma decimal (e.g. "1 000,00")
    if " " in s and "," in s:
        s = s.replace(" ", "").replace(",", ".")
    # EUR-style: single comma followed by exactly 2 digits at the end, no period
    # Matches "1,00", "15,00", "100,00" but NOT "1,000" (3 digits) or "1,000.00"
    elif re.search(r",\d{2}$", s) and "." not in s and s.count(",") == 1:
        s = s.replace(",", ".")
    else:
        # GBP/JPY/USD/etc — comma is thousands separator
        s = s.replace(",", "")

    try:
        return float(s)
    except ValueError:
        return None


def evaluate_result(
    op_id: int, currency: str, default_raw: str | None, max_raw: str | None, max_win: float
) -> tuple[str, str, str]:
    """Return (status, notes, allowed_max_str)."""
    notes: list[str] = []
    status = "✅ OK"

    default_val = parse_bet_value(default_raw)
    max_val = parse_bet_value(max_raw)

    expected_max = get_expected_maxbet_smallest(op_id, currency, max_win)
    expected_default = get_expected_defaultbet_smallest(op_id, currency)

    allowed_max_str = "—"
    if expected_max is not None:
        allowed_max_val = expected_max / 100
        allowed_max_str = f"{allowed_max_val:.2f}"
        if max_val is not None:
            if max_val > allowed_max_val + 0.01:
                notes.append(f"MaxBet {max_val:.2f} > allowed {allowed_max_val:.2f}")
                status = "❌ FAIL"
            elif max_val < allowed_max_val / 2:
                notes.append(f"MaxBet {max_val:.2f} far below allowed {allowed_max_val:.2f}")
                if status != "❌ FAIL":
                    status = "⚠️ WARNING"

    if expected_default is not None and default_val is not None:
        expected_default_val = expected_default / 100
        if abs(default_val - expected_default_val) > 0.01:
            notes.append(
                f"DefaultBet {default_val:.2f} ≠ expected {expected_default_val:.2f}"
            )
            status = "❌ FAIL"

    return status, "; ".join(notes), allowed_max_str


# ---------------------------------------------------------------------------
# Browser automation
# ---------------------------------------------------------------------------

async def open_and_verify(page, url: str, op_id: int, op_name: str, currency: str,
                          screenshot_path: Path, max_win: float) -> dict:
    result: dict = {
        "op_id": op_id,
        "op_name": op_name,
        "currency": currency,
        "defaultBet": None,
        "maxBet": None,
        "allowedMaxBet": "—",
        "ladder": [],
        "status": "❌ FAIL",
        "note": "",
    }

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # Phase 1 — wait for #_pixi_root_ (splash screen mounted)
        pixi_found = False
        for _ in range(30):
            if await page.evaluate("() => !!document.getElementById('_pixi_root_')"):
                pixi_found = True
                break
            await asyncio.sleep(1)

        if not pixi_found:
            await page.screenshot(path=str(screenshot_path))
            result["note"] = "_pixi_root_ never appeared — preloader timed out"
            return result

        # Phase 2 — dismiss splash, wait for bet button to become active
        await page.keyboard.press("Space")

        bet_active = False
        for _ in range(30):
            is_active = await page.evaluate("""
                (() => {
                    const btn = document.getElementById('bet_button');
                    if (!btn) return false;
                    return !btn.className.split(' ').some(c => c.startsWith('disabled'));
                })()
            """)
            if is_active:
                bet_active = True
                break
            await asyncio.sleep(1)

        if not bet_active:
            await page.screenshot(path=str(screenshot_path))
            result["note"] = "bet_button never became active after splash"
            return result

        # Phase 3 — open bet panel via pointerup (click events are not trusted by the HUD)
        await page.evaluate("""
            document.getElementById('bet_button').dispatchEvent(
                new MouseEvent('pointerup', { bubbles: true })
            )
        """)
        await asyncio.sleep(1.5)

        # Extract bet ladder (retry up to 3× to allow panel animation to complete)
        bet_data: dict | None = None
        for _ in range(3):
            raw = await page.evaluate("""
                (() => {
                    const itemList = document.querySelector('#bet_panel [class*="itemList"]');
                    if (!itemList) return JSON.stringify({ error: 'itemList not found' });
                    const items = Array.from(itemList.children);
                    const bets = items.map(item => ({
                        value: item.textContent.trim(),
                        selected: item.className.split(' ').some(c => c.startsWith('selectedItem'))
                    }));
                    return JSON.stringify({ bets, count: bets.length });
                })()
            """)
            bet_data = json.loads(raw)
            if "error" not in bet_data:
                break
            await asyncio.sleep(1)

        if bet_data is None or "error" in bet_data:
            await page.screenshot(path=str(screenshot_path))
            result["note"] = f"Bet panel extraction failed: {bet_data}"
            return result

        bets = bet_data["bets"]
        default_raw = next((b["value"] for b in bets if b["selected"]), None)
        max_raw = bets[-1]["value"] if bets else None

        result["defaultBet"] = default_raw
        result["maxBet"] = max_raw
        result["ladder"] = [b["value"] for b in bets]

        await page.screenshot(path=str(screenshot_path))

        status, note, allowed_max_str = evaluate_result(
            op_id, currency, default_raw, max_raw, max_win
        )
        result["status"] = status
        result["note"] = note
        result["allowedMaxBet"] = allowed_max_str

    except Exception as exc:
        result["note"] = f"Exception: {exc}"
        try:
            await page.screenshot(path=str(screenshot_path))
        except Exception:
            pass

    return result


async def run(links_path: Path, max_win: float, output_dir: Path) -> list[dict]:
    links = json.loads(links_path.read_text())
    screenshots_dir = output_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
        )

        for op_id_str, op_data in links.items():
            op_id = int(op_id_str)
            op_name = op_data["operatorName"]

            op_dir = screenshots_dir / str(op_id)
            op_dir.mkdir(parents=True, exist_ok=True)

            for currency, url in op_data["currencyLinks"].items():
                screenshot_path = op_dir / f"{currency}.png"
                print(f"[{op_id}] {op_name} / {currency} ...", flush=True)

                context = await browser.new_context(viewport={"width": 1280, "height": 720})
                page = await context.new_page()

                res = await open_and_verify(
                    page, url, op_id, op_name, currency, screenshot_path, max_win
                )
                results.append(res)

                print(
                    f"  DefaultBet={str(res['defaultBet']):>12}  "
                    f"MaxBet={str(res['maxBet']):>14}  "
                    f"Allowed≤{res['allowedMaxBet']:>10}  {res['status']}"
                    + (f"  [{res['note']}]" if res["note"] else ""),
                    flush=True,
                )

                await context.close()

        await browser.close()

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify GSBS bet settings in-game via Playwright.")
    parser.add_argument("--links", required=True, help="Path to links.json generated by golden-bet-scripts")
    parser.add_argument("--max-win", type=float, required=True, help="Game max_win multiplier")
    parser.add_argument("--output-dir", required=True, help="Directory for screenshots and results.json")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = asyncio.run(run(Path(args.links), args.max_win, output_dir))

    results_file = output_dir / "results.json"
    results_file.write_text(json.dumps(results, indent=2))

    ok   = sum(1 for r in results if r["status"] == "✅ OK")
    warn = sum(1 for r in results if r["status"] == "⚠️ WARNING")
    fail = sum(1 for r in results if r["status"] == "❌ FAIL")
    total = len(results)

    print(f"\nResults → {results_file}")
    print(f"Summary: {ok} OK / {warn} WARNING / {fail} FAIL  (total={total})")

    if warn:
        print("\nWarnings:")
        for r in results:
            if r["status"] == "⚠️ WARNING":
                print(f"  [{r['op_id']}] {r['op_name']} / {r['currency']}: {r['note']}")

    if fail:
        print("\nFailures:")
        for r in results:
            if r["status"] == "❌ FAIL":
                print(f"  [{r['op_id']}] {r['op_name']} / {r['currency']}: {r['note']}")

    sys.exit(1 if fail > 0 else 0)


if __name__ == "__main__":
    main()
