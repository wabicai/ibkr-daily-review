#!/usr/bin/env python3
"""Report upcoming earnings, macro, and company-event risk from config/events.json."""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "config" / "events.json"
RULES = ROOT / "config" / "risk_rules.json"


def parse_day(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    events_doc = json.loads(EVENTS.read_text())
    rules = json.loads(RULES.read_text())
    today = date.today()
    blackout = int(rules["earnings_blackout_days"])

    upcoming = []
    for event in events_doc.get("events", []):
        event_day = parse_day(event["date"])
        days = (event_day - today).days
        if days >= 0:
            upcoming.append((days, event))

    upcoming.sort(key=lambda item: item[0])
    print("\nEVENT RISK")
    print("=" * 72)
    if not upcoming:
        print("No upcoming events configured.")
        print("Populate config/events.json from reliable primary sources before trading.")
        return

    for days, event in upcoming:
        symbol = event.get("symbol", "MARKET")
        level = event.get("risk_level", "medium").upper()
        title = event.get("title", event.get("event_type", "event"))
        flags: list[str] = []
        if event.get("event_type") == "earnings" and days <= blackout:
            flags.append("NO_NEW_POSITION")
        if level == "HIGH" and days <= 2:
            flags.append("REVIEW_POSITION_SIZE")
        print(
            f"{event['date']}  {symbol:<7} D-{days:<3} {level:<6} "
            f"{title} {' '.join(flags)}"
        )


if __name__ == "__main__":
    main()
