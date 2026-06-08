#!/usr/bin/env python3
"""
Fetch daily OHLCV for the watchlist via yfinance and write a single
JSON cache file under cache/<YYYY-MM-DD>_market.json.

Run order: this is the only network step. analyze.py works fully offline
against whatever this writes.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "watchlist.json"
CACHE_DIR = ROOT / "cache"
HISTORY_DAYS = 120  # enough for MA50 + 20d relative strength + headroom


def load_watchlist() -> tuple[list[dict], str]:
    data = json.loads(CONFIG.read_text())
    return data["symbols"], data["benchmark"]


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


def fetch_symbol(symbol: str) -> dict | None:
    """Return {snapshot, history, premarket} for one ticker, or None if the
    daily data is unusable. ``premarket`` may be None when no pre-market bar
    is available — that never invalidates the symbol."""
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=f"{HISTORY_DAYS}d", auto_adjust=False)
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


def main() -> int:
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
            data = fetch_symbol(sym)
        except Exception as exc:  # network/yfinance hiccups
            print(f"[WARN] {sym}: fetch failed ({exc})", file=sys.stderr)
            failures.append(sym)
            continue
        if data is None:
            print(f"[WARN] {sym}: empty history", file=sys.stderr)
            failures.append(sym)
            continue
        data["name"] = entry["name"]
        out["market_data"][sym] = data
        line = f"  {sym:<6} {data['snapshot']['price']:>9.2f}  ({data['snapshot']['change_pct']:+.2f}%)"
        pre = data.get("premarket")
        if pre:
            line += f"   盘前 {pre['price']:>9.2f} ({pre['change_pct']:+.2f}%)"
        print(line)

    if benchmark not in out["market_data"]:
        print(f"[ERROR] benchmark {benchmark} missing — relative strength unavailable", file=sys.stderr)
        return 2

    today = date.today().strftime("%Y-%m-%d")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{today}_market.json"
    cache_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    latest = CACHE_DIR / "latest.json"
    latest.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"\nWrote {cache_path.relative_to(ROOT)}  ({len(out['market_data'])} symbols)")
    if failures:
        print(f"Failures: {', '.join(failures)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
