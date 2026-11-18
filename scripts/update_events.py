#!/usr/bin/env python3
"""Refresh the event calendar from deterministic public schedules.

Macro dates are maintained as a small reviewed schedule in this script.
Earnings dates are pulled from yfinance for watchlist symbols and marked as
secondary-source data so the review can still verify primary sources.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST = ROOT / "config" / "watchlist.json"
EVENTS = ROOT / "config" / "events.json"
HORIZON_DAYS = 45

# High-impact US macro releases used by the strategy. Keep reviewed dates here;
# do not guess dates. New dates can be added independently of earnings fetching.
MACRO_EVENTS = [
    {"date": "2026-10-02", "title": "US Employment Situation", "source": "BLS", "risk_level": "high"},
    {"date": "2026-10-14", "title": "US CPI", "source": "BLS", "risk_level": "high"},
    {"date": "2026-10-28", "title": "FOMC rate decision", "source": "Federal Reserve", "risk_level": "high"},
    {"date": "2026-10-29", "title": "US Personal Income and Outlays / PCE", "source": "BEA", "risk_level": "high"},
]


def flatten(config: dict) -> list[str]:
    groups = config.get("groups", {})
    seen: set[str] = set()
    out: list[str] = []
    for items in groups.values():
        for item in items:
            symbol = item["symbol"]
            if symbol not in seen:
                seen.add(symbol)
                out.append(symbol)
    return out


def earnings_event(symbol: str, start: date, end: date) -> dict | None:
    try:
        dates = yf.Ticker(symbol).get_earnings_dates(limit=8)
    except Exception:
        return None
    if dates is None or dates.empty:
        return None
    for idx in dates.index:
        day = idx.date()
        if start <= day <= end:
            return {
                "symbol": symbol,
                "event_type": "earnings",
                "date": day.isoformat(),
                "title": f"{symbol} earnings",
                "source": "yfinance (verify primary IR source before trading)",
                "risk_level": "high",
            }
    return None


def main() -> int:
    today = date.today()
    end = today + timedelta(days=HORIZON_DAYS)
    config = json.loads(WATCHLIST.read_text())
    events = []
    for item in MACRO_EVENTS:
        day = date.fromisoformat(item["date"])
        if today <= day <= end:
            events.append({"symbol": "MARKET", "event_type": "macro", **item})
    earnings_failures = []
    for symbol in flatten(config):
        event = earnings_event(symbol, today, end)
        if event:
            events.append(event)
        else:
            earnings_failures.append(symbol)
    events.sort(key=lambda e: (e["date"], e["symbol"], e["event_type"]))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = {
        "events": events,
        "metadata": {
            "last_updated": now,
            "source_mode": "generated",
            "horizon_days": HORIZON_DAYS,
            "status": "ok" if not earnings_failures else "degraded",
            "earnings_lookup_no_event_or_failed": earnings_failures,
            "note": "Earnings use yfinance discovery and must be verified against primary IR sources before trading. Macro dates are reviewed constants.",
        },
        "schema": json.loads(EVENTS.read_text()).get("schema", {}),
    }
    EVENTS.write_text(json.dumps(out, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(f"Wrote {len(events)} events; status={out['metadata']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
