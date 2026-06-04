# 每日美股 Watchlist 复盘助手

请用中文回复。所有建议仅供参考，不构成投资建议，**绝不自动下单**。

本仓库是 GitHub Actions 每个交易日美东收盘后通过 yfinance 自动更新的 OHLCV 缓存。Claude Code 本地 clone 后直接读 `cache/latest.json` 算指标即可，**不需要联网**、**不需要 API key**、**不连券商**。

---

## 关注清单 Watchlist（20只）

来源：`config/watchlist.json`。新增/删减改这个文件并跑 `scripts/build_cache.py`，下次 Actions 也会用新列表。

| # | 代码 | 交易所 | 描述 |
|---|------|--------|------|
| 1 | AAPL | NASDAQ | 苹果 |
| 2 | META | NASDAQ | Meta |
| 3 | NVDA | NASDAQ | 英伟达 |
| 4 | QQQ | NASDAQ | 纳指100 ETF（**基准**）|
| 5 | TSLA | NASDAQ | 特斯拉 |
| 6 | VOO | ARCA | 标普500 ETF |
| 7 | MU | NASDAQ | 美光科技 |
| 8 | MSFT | NASDAQ | 微软 |
| 9 | AMD | NASDAQ | AMD |
| 10 | AVGO | NASDAQ | 博通 |
| 11 | PLTR | NASDAQ | Palantir |
| 12 | GOOGL | NASDAQ | 谷歌 |
| 13 | AMZN | NASDAQ | 亚马逊 |
| 14 | ORCL | NYSE | 甲骨文 |
| 15 | SMH | NASDAQ | 半导体ETF（VanEck）|
| 16 | MRVL | NASDAQ | 迈威尔科技 |
| 17 | NOK | NYSE | 诺基亚 |
| 18 | LITE | NASDAQ | Lumentum（光学器件）|
| 19 | COHR | NYSE | Coherent（激光/光学）|
| 20 | GLW | NYSE | 康宁（光纤/特种玻璃）|

---

## 分析参数

- **趋势基准**：MA20 / MA50（日线收盘价）
- **辅助指标**：RSI 14 日（Wilder 平滑法）
- **相对强弱**：标的近 20 日涨幅 − QQQ 同期涨幅
- **量能**：近 5 日均量 ÷ 近 20 日均量
- **风格**：趋势交易，中长周期；无明确信号则「观察/持有」

---

## 每日执行流程

### Step 0 — 数据获取

#### 0-pre：缓存检查（必须最先执行）

1. **优先 `git -C <repo路径> pull --ff-only`** 拉一次远端最新缓存
2. 读 `cache/latest.json`
3. 看 `market_data["QQQ"].snapshot.as_of`：
   - 等于今天 → ✅ 用，报告首行注明 `📦 数据日期 YYYY-MM-DD`
   - 是上一个交易日（今天美股没开盘 / Actions 还没跑）→ ⚠️ 报告首行说明「最新可用数据为 YYYY-MM-DD」再继续
   - 超过 3 个交易日 → 提示用户检查 Actions 是否失败，先不出报告

#### 0a：缓存结构

`cache/latest.json` 和 `cache/<YYYY-MM-DD>_market.json` 内容一致：

```json
{
  "generated_at": "2026-06-04T21:35:12+00:00",
  "source": "yfinance",
  "benchmark": "QQQ",
  "history_days": 120,
  "market_data": {
    "AAPL": {
      "name": "苹果",
      "snapshot": {
        "price": 201.23,          // 当日收盘
        "prev_close": 199.10,     // 前一日收盘
        "change_pct": 1.07,       // 涨跌幅 %
        "as_of": "2026-06-04"     // 数据日期
      },
      "history": {
        "dates":  ["2026-01-06", ...],  // 升序，120 个交易日
        "open":   [...],
        "high":   [...],
        "low":    [...],
        "close":  [...],                 // close[-1] === snapshot.price
        "volume": [...]
      }
    }
  }
}
```

**字段说明**（跟旧 IBKR 格式的对应）：
- `snapshot.price` ⟵ 旧 `snapshot.price`（当日收盘价）
- `snapshot.prev_close` ⟵ 旧 `snapshot.prior_close`
- `snapshot.change_pct` ⟵ 旧 `snapshot.change_pct`
- `history.dates` ⟵ 旧 `history.time`
- `history.{open,high,low,close,volume}` ⟵ 同名
- ❌ 不再有 `contract_id` / `exchange`（yfinance 不需要）
- ❌ 不再有 `account`（公开仓库不存账户/持仓）

#### 0b：价格一致性自检

对每只票确认 `history.close[-1] ≈ snapshot.price`，正常应完全相等（同一来源）。如果差异 > 0.5%，跳过这只票并在报告里标注。

---

### Step 1 — 持仓核算（可选，仅当用户提供持仓时）

仓库本身不存持仓。两种来源：

1. **用户在对话里贴**：
   ```
   AAPL 30股 @ 180.50
   NVDA 50股 @ 95.00
   ```
2. **本地文件**：检查 `<repo路径>/positions.local.json`（已 gitignore），格式：
   ```json
   {
     "net_liquidation": 120000,
     "cash": 12000,
     "positions": [
       { "symbol": "AAPL", "shares": 30, "avg_cost": 180.50 }
     ]
   }
   ```

拿到持仓后，对每只票算：
- 当前市值 = `snapshot.price × shares`
- 仓位占比 = 市值 / net_liquidation × 100%（>40% 标 ⚠️ 仓位过重）
- 未实现盈亏 % = (snapshot.price − avg_cost) / avg_cost × 100%

无持仓 → 跳过 Step 1，直接进 Step 2。

---

### Step 2 — 技术指标

逐票计算（公式跟 `scripts/analyze.py` 完全一致）：

```
MA20         = mean(close[-20:])
MA50         = mean(close[-50:])
RSI(14)      = Wilder 平滑法
量能比       = mean(volume[-5:]) / mean(volume[-20:])
相对强弱     = (close[-1]/close[-21] - 1)*100 − (QQQ_close[-1]/QQQ_close[-21] - 1)*100
趋势         = price>MA20>MA50 → 上升↑
               price<MA20<MA50 → 下降↓
               否则             → 盘整→
```

输出表格（每列对齐）：

```
标的     当前价    MA20     MA50     RSI(14)        强弱vsQQQ      趋势    量能比   信号
AAPL    $201.23  $198.50  $192.10   65.7 健康      +2.1%         上升↑   1.10x   📈 多头共振
...
```

**指标标签**：
- RSI：`>70` ⚠超买 / `50–70` 健康 / `30–50` 偏弱 / `<30` 超卖
- 相对强弱：`>+3%` 💪 / `<-3%` 👎 / 其他无标
- 量能比：`>1.5` 放量 / `<0.7` 缩量

---

### Step 3 — 信号判定

**减仓警示**（满足任一即触发）：
- `当前价 < MA20` 且 `量能比 > 1.2` 且 `当前价 < 昨收`
- `当前价 < min(近 5 日收盘) × 0.99`（跌破近期低点）

**加仓候选**（无减仓信号，且下列至少 3 项成立）：
- `当前价 > MA20`
- `MA20 > MA50`
- `量能比 > 1.5` 且 `当前价 > 昨收`
- `50 ≤ RSI(14) ≤ 70`
- `相对强弱 ≥ 0`（跑赢 QQQ）

否则 → 观察/持有。

---

### Step 4 — 操作建议

对每个有信号的票输出：
- 当前价、MA20、MA50、RSI
- 3 个月最低（支撑）、3 个月最高（阻力）
- 近 2 周最低 → 当前价（参考入场区间）
- 止损 = 近 2 周最低 × 0.97
- 如果用户给了 net_liquidation，再算「30% 上限对应最大股数」

---

### Step 5 — 汇总收尾

报告末尾必须包含：
```
═══════════════════════════════════════════════════════════
  ⚠️ 以上为技术分析参考，非投资建议，不会自动下单。
  数据源 yfinance EOD，盘中数据不实时，仅适合复盘。
═══════════════════════════════════════════════════════════
```

---

## 数据更新机制

- **GitHub Actions cron**：`30 21 * * 1-5` (UTC) = 美东收盘后约 1.5 小时
- **手动触发**：`gh workflow run daily-update.yml -R wabicai/ibkr-daily-review`
- **本地手动更新**：`python scripts/build_cache.py`（覆盖 `latest.json` 和当日 dated 文件）

## 重要约定

- 本仓库**公开**：不放任何持仓 / 账户 / 交易数据
- **不下单、不连券商**：所有"建议"都是技术信号，用户手动在 IBKR 客户端执行
- 报告里始终注明"非投资建议"
- 盘中数据不准确，复盘场景 OK
- 字段对照表见 Step 0a，旧的 IBKR prompt 习惯也适用，只是去掉了 `contract_id` / `exchange` / `account` 这三组
