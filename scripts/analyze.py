#!/usr/bin/env python3
"""Offline watchlist technical review with role-aware signal filtering."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "cache"
WATCHLIST = ROOT / "config" / "watchlist.json"


def ma(values: list[float], n: int) -> float | None:
    return sum(values[-n:]) / n if len(values) >= n else None


def rsi(closes: list[float], n: int = 14) -> float | None:
    if len(closes) < n + 1:
        return None
    deltas = [closes[i + 1] - closes[i] for i in range(len(closes) - 1)]
    gains = [max(delta, 0) for delta in deltas]
    losses = [max(-delta, 0) for delta in deltas]
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
    avg5 = sum(volumes[-5:]) / 5
    avg20 = sum(volumes[-20:]) / 20
    return avg5 / avg20 if avg20 else 1.0


def rel_strength(closes: list[float], benchmark: list[float], n: int = 20) -> float:
    if len(closes) < n + 1 or len(benchmark) < n + 1:
        return 0.0
    stock_return = (closes[-1] / closes[-n - 1] - 1) * 100
    benchmark_return = (benchmark[-1] / benchmark[-n - 1] - 1) * 100
    return stock_return - benchmark_return


def live_price(data: dict) -> tuple[float, float, bool]:
    snapshot = data["snapshot"]
    closes = data["history"]["close"]
    premarket = data.get("premarket")
    if (
        premarket
        and premarket.get("price")
        and premarket.get("as_of", "")[:10] > snapshot["as_of"]
    ):
        return float(premarket["price"]), float(snapshot["price"]), True
    previous = closes[-2] if len(closes) >= 2 else snapshot["price"]
    return float(snapshot["price"]), float(previous), False


def trend_label(price: float, m20: float | None, m50: float | None) -> str:
    if m20 is None or m50 is None:
        return "—"
    if price > m20 > m50:
        return "上升↑"
    if price < m20 < m50:
        return "下降↓"
    return "盘整→"


def rsi_label(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value > 70:
        return f"{value:.1f} 超买"
    if value >= 50:
        return f"{value:.1f} 健康"
    if value >= 30:
        return f"{value:.1f} 偏弱"
    return f"{value:.1f} 超卖"


def load_cache(target: str | None) -> tuple[dict, Path]:
    path = CACHE_DIR / (f"{target}_market.json" if target else "latest.json")
    if not path.exists() and not target:
        path = CACHE_DIR / f"{date.today():%Y-%m-%d}_market.json"
    if not path.exists():
        print(f"[ERROR] cache not found: {path}", file=sys.stderr)
        raise SystemExit(1)
    return json.loads(path.read_text()), path


def load_roles() -> dict[str, str]:
    config = json.loads(WATCHLIST.read_text())
    return {item["symbol"]: item.get("role", "candidate") for item in config["symbols"]}


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else None
    cache, cache_path = load_cache(target)
    roles = load_roles()
    market = cache["market_data"]
    benchmark_symbol = cache["benchmark"]
    benchmark_closes = market[benchmark_symbol]["history"]["close"]
    as_of = market[benchmark_symbol]["snapshot"]["as_of"]

    print(f"\n{'=' * 112}")
    print(f"每日美股 watchlist 技术分析 {as_of}（基准 {benchmark_symbol}）")
    print(f"cache: {cache_path.relative_to(ROOT)}")
    print(f"{'=' * 112}")
    print(
        f"{'标的':<6} {'角色':<9} {'当前价':>10} {'MA20':>10} {'MA50':>10} "
        f"{'RSI14':>11} {'强弱QQQ':>10} {'趋势':>7} {'量能':>7}  信号"
    )

    signals: list[tuple[str, str, dict]] = []
    any_premarket = False

    for symbol, data in market.items():
        role = roles.get(symbol, "candidate")
        closes = data["history"]["close"]
        volumes = data["history"]["volume"]
        current, previous, is_premarket = live_price(data)
        any_premarket = any_premarket or is_premarket
        m20 = ma(closes, 20)
        m50 = ma(closes, 50)
        rsi14 = rsi(closes)
        volume_ratio = vol_ratio(volumes)
        relative = rel_strength(closes, benchmark_closes)
        trend = trend_label(current, m20, m50)

        if role == "context":
            action = "仅市场状态"
        elif role == "benchmark":
            action = "基准"
        else:
            sell = (
                (m20 is not None and current < m20 and volume_ratio > 1.2 and current < previous)
                or (len(closes) >= 5 and current < min(closes[-5:]) * 0.99)
            )
            if sell:
                action = "减仓警示"
                signals.append((symbol, action, data))
            else:
                conditions = [
                    m20 is not None and current > m20,
                    m20 is not None and m50 is not None and m20 > m50,
                    volume_ratio > 1.5 and current > previous,
                    rsi14 is not None and 50 <= rsi14 <= 70,
                    relative >= 0,
                ]
                if sum(conditions) >= 3:
                    action = "多头共振"
                    signals.append((symbol, "加仓候选", data))
                else:
                    action = "观察/持有"

        premarket_tag = "*" if is_premarket else " "
        print(
            f"{symbol:<6} {role:<9} {premarket_tag}${current:>8.2f} "
            f"${m20 or 0:>8.2f} ${m50 or 0:>8.2f} "
            f"{rsi_label(rsi14):>11} {relative:>+9.1f}% {trend:>7} "
            f"{volume_ratio:>6.2f}x  {action}"
        )

    if any_premarket:
        print("* 当前价为鲜活盘前价；技术指标仍使用日线数据。")

    print(f"\n{'=' * 112}\n操作建议\n{'=' * 112}")
    if not signals:
        print("今日没有候选标的触发明确信号。")
        return

    for symbol, signal, data in signals:
        closes = data["history"]["close"]
        current, previous, is_premarket = live_price(data)
        support_3m = min(closes)
        resistance_3m = max(closes)
        support_2w = min(closes[-10:]) if len(closes) >= 10 else support_3m
        stop = support_2w * 0.97
        print(f"\n{symbol} [{signal}]")
        print(f"当前价 ${current:.2f}" + (f"，盘前，昨收 ${previous:.2f}" if is_premarket else ""))
        print(f"3个月支撑 ${support_3m:.2f}，阻力 ${resistance_3m:.2f}")
        print(f"参考入场区间 ${support_2w:.2f} - ${current:.2f}")
        print(f"止损参考 ${stop:.2f}")


if __name__ == "__main__":
    main()
