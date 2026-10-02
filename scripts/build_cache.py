#!/usr/bin/env python3
"""
Fetch daily OHLCV for the watchlist via yfinance and write a single
JSON cache file under cache/<YYYY-MM-DD>_market.json.

Run order: this is the only network step. analyze.py works fully offline
against whatever this writes.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "watchlist.json"
CACHE_DIR = ROOT / "cache"
HISTORY_DAYS = 120  # enough for MA50 + 20d relative strength + headroom
REQUIRED_OHLCV = ["Open", "High", "Low", "Close", "Volume"]
US_TZ = ZoneInfo("America/New_York")


def flatten_watchlist(data: dict) -> list[dict]:
    """Support both legacy {symbols:[...]} and v2 {groups:{...}} watchlists."""
    if data.get("groups"):
        out: list[dict] = []
        seen: set[str] = set()
        group_order = data.get("strategy", {}).get(
            "priority_order", ["core", "satellite", "etf", "context"]
        )
        for group in group_order:
            for item in data["groups"].get(group, []):
                symbol = item["symbol"]
                if symbol in seen:
                    continue
                merged = {**item, "group": group}
                out.append(merged)
                seen.add(symbol)
        for group, items in data["groups"].items():
            if group in group_order:
                continue
            for item in items:
                symbol = item["symbol"]
                if symbol in seen:
                    continue
                out.append({**item, "group": group})
                seen.add(symbol)
        return out
    return data.get("symbols", [])


def load_watchlist() -> tuple[list[dict], str]:
    data = json.loads(CONFIG.read_text())
    return flatten_watchlist(data), data["benchmark"]


def fetch_premarket(symbol: str, ref_close: float) -> dict | None:
    """Latest pre-market (04:00–09:30 ET) price/volume for the most recent
    session, vs ``ref_close`` (the last regular close). None when there are no
    pre-market trades — e.g. weekends, holidays, or an EOD run with an empty
    intraday window.

    Note: ``as_of`` carries the bar timestamp so the reader can tell whether
    this pre-market belongs to a session *not yet* in the daily history. Only
    treat it as the live price when ``as_of`` date > ``snapshot.as_of``.
    """
    df = yf.Ticker(symbol).history(
        period="1d", interval="1m", prepost=True, auto_adjust=False
    )
    if df.empty:
        return None

    idx = df.index.tz_convert("America/New_York")
    minutes = idx.hour * 60 + idx.minute
    latest_day = idx[-1].date()
    mask = (idx.date == latest_day) & (minutes >= 4 * 60) & (minutes < 9 * 60 + 30)
    pre = df[mask]
    if pre.empty:
        return None

    price = round(float(pre["Close"].iloc[-1]), 4)
    volume = int(pre["Volume"].sum())
    change_pct = (price - ref_close) / ref_close * 100 if ref_close else 0.0
    return {
        "price": price,
        "change_pct": round(change_pct, 3),
        "volume": volume,
        "as_of": idx[mask][-1].isoformat(),
    }


def _finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _complete_history(hist):
    """Remove partial/non-finite daily bars before they enter the cache."""
    if any(col not in hist.columns for col in REQUIRED_OHLCV):
        return hist.iloc[0:0]
    clean = hist.dropna(subset=REQUIRED_OHLCV).copy()
    finite_mask = clean[REQUIRED_OHLCV].apply(
        lambda col: col.map(_finite)
    ).all(axis=1)
    return clean.loc[finite_mask]


def fetch_symbol(symbol: str) -> dict | None:
    """Return {snapshot, history, premarket} for one ticker, or None if the
    daily data is unusable. ``premarket`` may be None when no pre-market bar
    is available — that never invalidates the symbol."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=f"{HISTORY_DAYS}d", auto_adjust=False)
    hist = _complete_history(hist)
    if hist.empty:
        return None

    closes = [round(float(v), 4) for v in hist["Close"].tolist()]
    opens = [round(float(v), 4) for v in hist["Open"].tolist()]
    highs = [round(float(v), 4) for v in hist["High"].tolist()]
    lows = [round(float(v), 4) for v in hist["Low"].tolist()]
    volumes = [int(v) for v in hist["Volume"].tolist()]
    dates = [d.strftime("%Y-%m-%d") for d in hist.index.tolist()]

    last_close = closes[-1]
    prev_close = closes[-2] if len(closes) >= 2 else last_close
    change_pct = (last_close - prev_close) / prev_close * 100 if prev_close else 0.0

    try:
        premarket = fetch_premarket(symbol, last_close)
    except Exception as exc:  # intraday endpoint can be flaky; never fatal
        print(f"[WARN] {symbol}: premarket fetch failed ({exc})", file=sys.stderr)
        premarket = None

    return {
        "snapshot": {
            "price": last_close,
            "prev_close": prev_close,
            "change_pct": round(change_pct, 3),
            "as_of": dates[-1],
        },
        "premarket": premarket,
        "history": {
            "dates": dates,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("premarket", "eod", "manual"), default="manual")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=int, default=90)
    return parser.parse_args()


def _fetch_with_retry(symbol: str, retries: int, delay: int) -> dict | None:
    last_exc: Exception | None = None
    for attempt in range(1, max(retries, 1) + 1):
        try:
            data = fetch_symbol(symbol)
            if data is not None:
                return data
        except Exception as exc:
            last_exc = exc
        if attempt < retries:
            print(f"[WARN] {symbol}: incomplete fetch, retry {attempt}/{retries}", file=sys.stderr)
            time.sleep(max(delay, 0))
    if last_exc:
        raise last_exc
    return None


def main() -> int:
    args = parse_args()
    symbols, benchmark = load_watchlist()
    out: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "yfinance",
        "benchmark": benchmark,
        "history_days": HISTORY_DAYS,
        "market_data": {},
    }

    failures: list[str] = []
    for entry in symbols:
        sym = entry["symbol"]
        try:
            data = _fetch_with_retry(sym, args.retries, args.retry_delay)
        except Exception as exc:  # network/yfinance hiccups
            print(f"[WARN] {sym}: fetch failed ({exc})", file=sys.stderr)
            failures.append(sym)
            continue
        if data is None:
            print(f"[WARN] {sym}: empty history", file=sys.stderr)
            failures.append(sym)
            continue
        data["name"] = entry["name"]
        data["role"] = entry.get("role", "candidate")
        data["theme"] = entry.get("theme", "unclassified")
        data["group"] = entry.get("group", "legacy")
        data["priority"] = entry.get("priority")
        data["tradable"] = entry.get("tradable", entry.get("role") != "context")
        out["market_data"][sym] = data
        line = f"  {sym:<10} {data['snapshot']['price']:>9.2f}  ({data['snapshot']['change_pct']:+.2f}%)"
        pre = data.get("premarket")
        if pre:
            line += f"   盘前 {pre['price']:>9.2f} ({pre['change_pct']:+.2f}%)"
        print(line)

    if benchmark not in out["market_data"]:
        print(f"[ERROR] benchmark {benchmark} missing — relative strength unavailable", file=sys.stderr)
        return 2

    benchmark_date = out["market_data"][benchmark]["snapshot"]["as_of"]
    latest_dates = {sym: data["snapshot"]["as_of"] for sym, data in out["market_data"].items()}
    stale_symbols = sorted(sym for sym, d in latest_dates.items() if d < benchmark_date)
    incomplete_symbols = sorted(set(failures))
    status = "ok" if not incomplete_symbols and not stale_symbols else "degraded"

    expected_us_date = datetime.now(US_TZ).date().isoformat()
    if args.phase == "eod" and benchmark_date != expected_us_date:
        print(
            f"[ERROR] EOD benchmark stale: {benchmark} latest={benchmark_date}, "
            f"expected={expected_us_date}; refusing to publish cache",
            file=sys.stderr,
        )
        return 3

    out["data_quality"] = {
        "status": status,
        "phase": args.phase,
        "benchmark_latest_complete_bar": benchmark_date,
        "expected_us_market_date": expected_us_date if args.phase == "eod" else None,
        "incomplete_symbols": incomplete_symbols,
        "stale_symbols": stale_symbols,
        "strict_json": True,
    }

    today = date.today().strftime("%Y-%m-%d")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{today}_market.json"
    serialized = json.dumps(out, indent=2, ensure_ascii=False, allow_nan=False)
    cache_path.write_text(serialized)

    latest = CACHE_DIR / "latest.json"
    latest.write_text(serialized)

    print(f"\nWrote {cache_path.relative_to(ROOT)}  ({len(out['market_data'])} symbols)")
    if failures:
        print(f"Failures: {', '.join(failures)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
