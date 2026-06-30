#!/usr/bin/env python3
"""Offline portfolio concentration and stop-risk checks.

Input is intentionally local-only and must never be committed:
  positions.local.json

Expected shape:
{
  "net_liquidation": 100000,
  "cash": 15000,
  "positions": [
    {"symbol": "AAPL", "shares": 20, "avg_cost": 180, "stop_price": 170}
  ]
}
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSITIONS = ROOT / "positions.local.json"
WATCHLIST = ROOT / "config" / "watchlist.json"
RULES = ROOT / "config" / "risk_rules.json"
CACHE = ROOT / "cache" / "latest.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


def main() -> int:
    try:
        portfolio = load_json(POSITIONS)
        watchlist = load_json(WATCHLIST)
        rules = load_json(RULES)
        cache = load_json(CACHE)
    except FileNotFoundError as exc:
        print(f"[ERROR] missing file: {exc.filename}", file=sys.stderr)
        return 1

    net_liq = float(portfolio.get("net_liquidation", 0))
    cash = float(portfolio.get("cash", 0))
    if net_liq <= 0:
        print("[ERROR] net_liquidation must be > 0", file=sys.stderr)
        return 2

    meta = {x["symbol"]: x for x in watchlist["symbols"]}
    market = cache["market_data"]
    theme_values: dict[str, float] = defaultdict(float)
    total_stop_risk = 0.0

    print("\nPORTFOLIO RISK")
    print("=" * 72)
    print(f"Net liquidation: ${net_liq:,.2f}")
    print(f"Cash:            ${cash:,.2f} ({cash / net_liq * 100:.1f}%)")

    if cash / net_liq * 100 < rules["min_cash_pct"]:
        print(f"WARN cash below minimum {rules['min_cash_pct']}%")

    print("\nPositions")
    for pos in portfolio.get("positions", []):
        symbol = pos["symbol"]
        if symbol not in market:
            print(f"WARN {symbol}: no cache data")
            continue
        price = float(market[symbol]["snapshot"]["price"])
        value = price * float(pos["shares"])
        weight = value / net_liq * 100
        theme = meta.get(symbol, {}).get("theme", "unclassified")
        theme_values[theme] += value

        flags: list[str] = []
        if weight > rules["max_position_pct"]:
            flags.append("OVER_LIMIT")
        elif weight > rules["warning_position_pct"]:
            flags.append("WARNING")

        stop = pos.get("stop_price")
        stop_text = "no stop"
        if stop is not None:
            risk = max(price - float(stop), 0) * float(pos["shares"])
            total_stop_risk += risk
            stop_text = f"stop ${float(stop):.2f}, risk ${risk:.2f}"

        print(
            f"{symbol:<6} ${value:>10,.2f}  {weight:>5.1f}%  "
            f"theme={theme:<22} {stop_text:<24} {' '.join(flags)}"
        )

    print("\nTheme concentration")
    for theme, value in sorted(theme_values.items(), key=lambda item: item[1], reverse=True):
        weight = value / net_liq * 100
        flag = " OVER_LIMIT" if weight > rules["max_theme_pct"] else ""
        print(f"{theme:<24} ${value:>10,.2f}  {weight:>5.1f}%{flag}")

    total_stop_pct = total_stop_risk / net_liq * 100
    print(f"\nTotal defined stop risk: ${total_stop_risk:,.2f} ({total_stop_pct:.2f}%)")
    if total_stop_pct > rules["max_total_stop_risk_pct"]:
        print(f"WARN total stop risk exceeds {rules['max_total_stop_risk_pct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
