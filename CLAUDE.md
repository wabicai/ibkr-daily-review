# IBKR Daily Review — Claude 读取指南

这个仓库是给 Claude Code 做美股每日复盘用的**数据缓存层**。GitHub Actions 每个交易日美东收盘后通过 yfinance 抓 watchlist 的 OHLCV，写到 `cache/`。Claude 本地 clone 后直接读 JSON 算指标、出报告。

## 用户常见请求 → 你应该做的事

**「今天美股复盘 / 帮我看看 watchlist」**
1. `git -C <repo路径> pull --ff-only`（确保数据最新）
2. 读 `cache/latest.json`（或 `cache/<YYYY-MM-DD>_market.json`）
3. 在内存里对每只票算 MA20 / MA50 / RSI(14) / 相对强弱(vs QQQ, 20d) / 量能比(5日/20日)
4. 按 `scripts/analyze.py` 的信号规则给出"加仓候选 / 减仓警示 / 观察"
5. 用户问到具体票，给当前价、3 个月支撑/阻力、近期 2 周低点、止损位

**「分析 XXXX」单只票**
- 同上但只跑那一只，可以更细：看最近 5/10/20 天 close、量能拐点、RSI 背离

**「持仓分析」**
- 仓库**不存任何持仓数据**（公开 repo）。用户会贴持仓 / 或本地放 `positions.local.json`（gitignore 了）
- 拿到持仓后，结合缓存里的 snapshot price 算市值、仓位占比、盈亏

## 缓存文件结构

`cache/<YYYY-MM-DD>_market.json` 和 `cache/latest.json` 是同一份内容：

```json
{
  "generated_at": "2026-06-04T21:35:12+00:00",
  "source": "yfinance",
  "benchmark": "QQQ",
  "history_days": 120,
  "market_data": {
    "AAPL": {
      "name": "苹果",
      "snapshot": { "price": 201.23, "prev_close": 199.10, "change_pct": 1.07, "as_of": "2026-06-04" },
      "history": {
        "dates":  ["2026-01-06", ...],
        "open":   [...],
        "high":   [...],
        "low":    [...],
        "close":  [...],
        "volume": [...]
      }
    },
    ...
  }
}
```

`history.close` 已经按日期升序排好，`close[-1]` 是当日收盘。

## 信号规则（跟 analyze.py 一致）

**减仓警示**（满足任一）：
- `当前价 < MA20` 且 `量能比 > 1.2` 且 `当前价 < 昨收`
- `当前价 < min(近5日收盘) * 0.99`（跌破近期低点）

**加仓候选**（无减仓信号，且下列至少 3 项成立）：
- `当前价 > MA20`
- `MA20 > MA50`
- `量能比 > 1.5` 且 `当前价 > 昨收`
- `50 ≤ RSI(14) ≤ 70`
- `相对强弱 ≥ 0`（跑赢 QQQ）

**强弱标记**：RSI>70 超买 / 50-70 健康 / 30-50 偏弱 / <30 超卖；相对强弱 >3% 强 / <-3% 弱。

## 数据更新机制

- GitHub Actions cron: `30 21 * * 1-5` (UTC) = 美东收盘 1.5h 后
- 手动触发：`gh workflow run daily-update.yml`
- 数据延迟：yfinance 通常收盘后 30 分钟内更新当日 EOD

如果 `cache/latest.json` 的 `as_of` 跟今天对不上（节假日 / Actions 没跑 / 网络问题），告诉用户最新数据是哪天的，不要拿过期数据当当日数据用。

## 重要约定

- **本仓库公开**，不放任何持仓 / 账户 / 交易数据
- **不下单、不连券商**，只算指标给参考
- 报告里始终注明"非投资建议"
- 数据源是 yfinance EOD，盘中数据不准，复盘用没问题
