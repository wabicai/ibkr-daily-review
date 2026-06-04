#!/usr/bin/env python3
"""
Read today's market cache and print the watchlist technical review:
MA20, MA50, RSI(14), relative strength vs benchmark (20d), volume ratio,
trend, and a signal hint.

Usage:
    python scripts/analyze.py                # latest cache
    python scripts/analyze.py 2026-06-04     # specific date
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "cache"
REPORTS_DIR = ROOT / "reports"


def ma(closes: list[float], n: int) -> float | None:
    return sum(closes[-n:]) / n if len(closes) >= n else None


def rsi(closes: list[float], n: int = 14) -> float | None:
    if len(closes) < n + 1:
        return None
    deltas = [closes[i + 1] - closes[i] for i in range(len(closes) - 1)]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    avg_gain = sum(gains[:n]) / n
    avg_loss = sum(losses[:n]) / n
    for i in range(n, len(deltas)):
        avg_gain = (avg_gain * (n - 1) + gains[i]) / n
        avg_loss = (avg_loss * (n - 1) + losses[i]) / n
    if avg_loss == 0:
        return 100.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def vol_ratio(volumes: list[int]) -> float:
    if len(volumes) < 20:
        return 1.0
    return (sum(volumes[-5:]) / 5) / (sum(volumes[-20:]) / 20)


def rel_strength(closes: list[float], bench_closes: list[float], n: int = 20) -> float:
    if len(closes) < n + 1 or len(bench_closes) < n + 1:
        return 0.0
    s = (closes[-1] - closes[-n - 1]) / closes[-n - 1] * 100
    b = (bench_closes[-1] - bench_closes[-n - 1]) / bench_closes[-n - 1] * 100
    return s - b


def rsi_label(r: float | None) -> str:
    if r is None:
        return "N/A"
    if r > 70:
        return f"{r:5.1f} ⚠超买"
    if r >= 50:
        return f"{r:5.1f} 健康"
    if r >= 30:
        return f"{r:5.1f} 偏弱"
    return f"{r:5.1f} 超卖"


def rs_label(v: float) -> str:
    s = f"{v:+.1f}%"
    if v > 3:
        return s + " 💪"
    if v < -3:
        return s + " 👎"
    return s + "  "


def trend_label(price: float, m20: float | None, m50: float | None) -> str:
    if m20 is None or m50 is None:
        return "—"
    if price > m20 > m50:
        return "上升↑"
    if price < m20 < m50:
        return "下降↓"
    return "盘整→"


def load_cache(target: str | None) -> tuple[dict, Path]:
    if target:
        path = CACHE_DIR / f"{target}_market.json"
    else:
        path = CACHE_DIR / "latest.json"
        if not path.exists():
            today = date.today().strftime("%Y-%m-%d")
            path = CACHE_DIR / f"{today}_market.json"
    if not path.exists():
        print(f"[ERROR] cache not found: {path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text()), path


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else None
    cache, cache_path = load_cache(target)

    market = cache["market_data"]
    benchmark = cache["benchmark"]
    bench_closes = market[benchmark]["history"]["close"]
    as_of = market[benchmark]["snapshot"]["as_of"]

    line = "─" * 100
    print(f"\n{'═' * 100}")
    print(f"  📊  每日美股 watchlist 技术分析  {as_of}  (基准: {benchmark})")
    print(f"  cache: {cache_path.relative_to(ROOT)}")
    print(f"{'═' * 100}")

    header = (
        f"  {'标的':<6} {'当前价':>9} {'MA20':>9} {'MA50':>9} "
        f"{'RSI(14)':>13} {'强弱vs'+benchmark:>13} {'趋势':>6} {'量能比':>7}  信号"
    )
    print(header)
    print(line)

    signals: list[tuple[str, str, dict]] = []

    for sym, mdata in market.items():
        snap = mdata["snapshot"]["price"]
        closes = mdata["history"]["close"]
        vols = mdata["history"]["volume"]

        m20 = ma(closes, 20)
        m50 = ma(closes, 50)
        r = rsi(closes, 14)
        vr = vol_ratio(vols)
        rs = rel_strength(closes, bench_closes, 20)
        trend = trend_label(snap, m20, m50)

        action = "观察/持有"
        sell = False
        if m20 is not None and snap < m20 and vr > 1.2 and len(closes) >= 2 and snap < closes[-2]:
            sell = True
            action = "⚠️ 趋势走弱"
        if len(closes) >= 5 and snap < min(closes[-5:]) * 0.99:
            sell = True
            action = "⚠️ 跌破近期低点"

        if not sell:
            conds = [
                m20 is not None and snap > m20,
                m20 is not None and m50 is not None and m20 > m50,
                vr > 1.5 and len(closes) >= 2 and snap > closes[-2],
                r is not None and 50 <= r <= 70,
                rs >= 0,
            ]
            if sum(conds) >= 3:
                action = "📈 多头共振"
                signals.append((sym, "加仓候选", mdata))
        elif sym in market:
            signals.append((sym, "减仓警示", mdata))

        m20_s = f"${m20:>7.2f}" if m20 else "    —  "
        m50_s = f"${m50:>7.2f}" if m50 else "    —  "
        print(
            f"  {sym:<6} ${snap:>8.2f} {m20_s:>9} {m50_s:>9} "
            f"{rsi_label(r):>13} {rs_label(rs):>13} {trend:>6} {vr:>6.2f}x  {action}"
        )

    print(f"\n{'═' * 100}")
    print("  操作建议（仅供参考，非投资建议）")
    print(f"{'═' * 100}")
    if not signals:
        print("  ✅ 今日无明确信号触发，watchlist 维持观察。")
    else:
        for sym, kind, mdata in signals:
            snap = mdata["snapshot"]["price"]
            closes = mdata["history"]["close"]
            r = rsi(closes, 14)
            support3m = min(closes)
            resist3m = max(closes)
            support2w = min(closes[-10:]) if len(closes) >= 10 else min(closes)
            r_str = f"{r:.1f}" if r else "N/A"
            print(f"\n  ▶ {sym}  [{kind}]")
            print(f"    当前价 ${snap:.2f}  RSI {r_str}")
            print(f"    3个月支撑 ${support3m:.2f}  阻力 ${resist3m:.2f}")
            print(f"    参考入场区间  ${support2w:.2f} – ${snap:.2f}")
            print(f"    止损参考  ${support2w * 0.97:.2f}（近期支撑下方 3%）")

    print()


if __name__ == "__main__":
    main()
