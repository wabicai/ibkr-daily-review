#!/usr/bin/env python3
"""Classify broad market conditions from ETF/context instruments in cache/latest.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache" / "latest.json"
WATCHLIST = ROOT / "config" / "watchlist.json"

REGIME_SYMBOLS = {"QQQ", "SPY", "IWM", "SMH", "TLT", "GLD"}


def ma(values: list[float], n: int) -> float | None:
    return sum(values[-n:]) / n if len(values) >= n else None


def pct_change(values: list[float], n: int) -> float:
    if len(values) < n + 1 or not values[-n - 1]:
        return 0.0
    return (values[-1] / values[-n - 1] - 1) * 100


def flatten_watchlist(config: dict) -> list[dict]:
    if config.get("groups"):
        out: list[dict] = []
        seen: set[str] = set()
        order = config.get("strategy", {}).get(
            "priority_order", ["core", "satellite", "etf", "context"]
        )
        for group in order:
            for item in config["groups"].get(group, []):
                if item["symbol"] in seen:
                    continue
                out.append({**item, "group": group})
                seen.add(item["symbol"])
        return out
    return config.get("symbols", [])


def main() -> None:
    cache = json.loads(CACHE.read_text())
    config = json.loads(WATCHLIST.read_text())
    market = cache["market_data"]
    items = flatten_watchlist(config)
    context = [x for x in items if x["symbol"] in REGIME_SYMBOLS or x.get("role") == "context"]

    scores: dict[str, int] = {}
    print("\nMARKET REGIME")
    print("=" * 72)
    for item in context:
        symbol = item["symbol"]
        data = market.get(symbol)
        if not data:
            print(f"{symbol:<10} missing")
            continue
        closes = data["history"]["close"]
        price = closes[-1]
        m20 = ma(closes, 20)
        m50 = ma(closes, 50)
        ret20 = pct_change(closes, 20)
        score = 0
        if m20 is not None and price > m20:
            score += 1
        if m20 is not None and m50 is not None and m20 > m50:
            score += 1
        if ret20 > 0:
            score += 1
        scores[symbol] = score
        trend = "strong" if score == 3 else "mixed" if score in (1, 2) else "weak"
        print(
            f"{symbol:<10} price=${price:>8.2f}  MA20=${m20 or 0:>8.2f}  "
            f"MA50=${m50 or 0:>8.2f}  20d={ret20:+6.2f}%  {trend}"
        )

    risk_assets = [scores.get("QQQ", 0), scores.get("SPY", 0), scores.get("IWM", 0), scores.get("SMH", 0)]
    defensive = [scores.get("TLT", 0), scores.get("GLD", 0)]
    risk_score = sum(risk_assets)
    defensive_score = sum(defensive)

    if risk_score >= 9 and risk_score >= defensive_score:
        regime = "RISK-ON"
    elif risk_score <= 4 and defensive_score >= 4:
        regime = "RISK-OFF"
    else:
        regime = "NEUTRAL"

    print(f"\nRegime: {regime}")
    print("QQQ/SPY/IWM/SMH/TLT/GLD are regime inputs and may still be actionable ETFs; ENTG/Samsung/Kioxia remain context-only unless explicitly promoted.")


if __name__ == "__main__":
    main()
