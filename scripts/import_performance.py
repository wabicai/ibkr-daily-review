#!/usr/bin/env python3
"""Import a sanitized strategy trade ledger and rebuild performance.json.

This deliberately accepts no IBKR credentials/account dump. The caller (for
example ChatGPT with the IBKR connector) exports only strategy-level fields.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "cache" / "performance.json"
FORBIDDEN_KEYS = {
    "account", "account_id", "account_number", "broker_order_id", "order_id",
    "execution_id", "conid", "cash", "nav", "buying_power", "positions",
}
REQUIRED = {"symbol", "entry_date", "exit_date", "realized_pnl"}


def validate_trade(trade: dict) -> dict:
    forbidden = FORBIDDEN_KEYS.intersection(trade)
    if forbidden:
        raise ValueError(f"private broker fields are not allowed: {sorted(forbidden)}")
    missing = REQUIRED.difference(trade)
    if missing:
        raise ValueError(f"missing trade fields: {sorted(missing)}")
    clean = {
        "symbol": str(trade["symbol"]),
        "entry_date": str(trade["entry_date"]),
        "exit_date": str(trade["exit_date"]),
        "realized_pnl": round(float(trade["realized_pnl"]), 2),
        "planned_rr": trade.get("planned_rr"),
        "realized_rr": trade.get("realized_rr"),
        "entry_reason": trade.get("entry_reason"),
        "exit_reason": trade.get("exit_reason"),
        "market_score": trade.get("market_score"),
        "theme_score": trade.get("theme_score"),
    }
    for key in ("planned_rr", "realized_rr", "market_score", "theme_score"):
        if clean[key] is not None:
            clean[key] = round(float(clean[key]), 4)
            if not math.isfinite(clean[key]):
                raise ValueError(f"{key} must be finite")
    return clean


def average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def summarize(trades: list[dict]) -> dict:
    pnl = [t["realized_pnl"] for t in trades]
    wins = [x for x in pnl if x > 0]
    losses = [x for x in pnl if x < 0]
    planned = [t["planned_rr"] for t in trades if t["planned_rr"] is not None]
    realized = [t["realized_rr"] for t in trades if t["realized_rr"] is not None]
    decided = len(wins) + len(losses)
    return {
        "trade_count": len(trades),
        "win_count": len(wins),
        "loss_count": len(losses),
        "breakeven_count": len(pnl) - decided,
        "win_rate": round(len(wins) / decided, 4) if decided else None,
        "gross_profit": round(sum(wins), 2),
        "gross_loss": round(sum(losses), 2),
        "net_pnl": round(sum(pnl), 2),
        "profit_factor": round(sum(wins) / abs(sum(losses)), 4) if losses else None,
        "avg_rr_planned": average(planned),
        "avg_rr_realized": average(realized),
        "max_drawdown_pct": None,
        "alpha_vs_qqq_pct": None,
        "alpha_vs_smh_pct": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--source", default="sanitized_ibkr_export")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text())
    raw = payload["trades"] if isinstance(payload, dict) else payload
    trades = [validate_trade(t) for t in raw]
    trades.sort(key=lambda t: (t["exit_date"], t["symbol"]), reverse=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    out = {
        "version": "4.1",
        "last_updated": now,
        "summary": summarize(trades),
        "trades": trades,
        "recent_decisions": payload.get("recent_decisions", []) if isinstance(payload, dict) else [],
        "import": {"source": args.source, "last_imported_at": now, "schema": "strategy_trade_v1"},
        "notes": "Strategy-level, sanitized statistics only. Never commit account IDs, balances, positions, broker order IDs, execution IDs, or other private broker data.",
    }
    OUTPUT.write_text(json.dumps(out, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(trades)} closed trades")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
