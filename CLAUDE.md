# 每日美股 Watchlist 复盘 + 下单助手

请用中文回复。

本仓库是 GitHub Actions 每个交易日美东收盘后通过 yfinance 自动更新的 OHLCV 缓存层。读取这份缓存的 Claude 会连接 **IBKR connector**，**有实际下单能力**——所以输出的不只是「建议」，而是会被执行的交易决策。务必按下面的风控规则走。

## 下单流程

**如果 IBKR connector 已连接** → 直接通过 connector 发起订单请求即可。**不需要在对话里再让用户敲一遍"确认"**——IBKR 客户端/桌面软件本身会弹二次确认窗口，所有真正的"按下回车"动作都在用户那边完成。你的职责是把信号转成结构化订单请求然后调用 connector。

**如果 IBKR connector 未连接** → 退化为参考模式：在 Step 5 输出待执行订单清单，让用户自己手动在 IBKR 客户端下单。

### 仍然要遵守的硬规则

1. **每个买单必须配套止损单**（OCO 或独立 STP），止损价按 `Step 4` 算。
2. **下单前用 IBKR connector 拉一次实时 `snapshot` 验真当前价**——缓存是 EOD 数据，盘中天然滞后；`snapshot` 和 `cache.snapshot.price` 的偏离只说明缓存不是实时行情。实时下单价格、股数校验和止损距离都以最新 `snapshot` 为准，必要时按实时价重算风控参数。
3. 报告里始终展示每笔单的：标的 / 方向 / 股数 / 限价 / 止损 / 理由——透明度优先，方便用户在 IBKR 弹窗里核对。

---

## 关注清单 Watchlist（21只）

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
| 21 | ADBE | NASDAQ | Adobe |

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
      "premarket": {              // 盘前 snapshot；无盘前数据时为 null
        "price": 203.10,         // 最新盘前价（04:00–09:30 ET 最后一根分钟 bar）
        "change_pct": 0.93,      // 相对 snapshot.price（昨收）的涨跌幅 %
        "volume": 152340,        // 盘前累计量（部分券源常为 0，仅供参考）
        "as_of": "2026-06-09T09:05:00-04:00"  // 盘前 bar 时间戳（带时区）
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
- `premarket` 是**新增**字段（盘前 snapshot），旧 IBKR 格式没有；无盘前数据时为 `null`
- ❌ 不再有 `contract_id` / `exchange`（yfinance 不需要）
- ❌ 不再有 `account`（公开仓库不存账户/持仓）

**⚠️ 盘前价的「鲜活」判定（关键规则）**：
`premarket` 字段在两种 cron 跑出的缓存里都可能存在，但只有当它属于「尚未计入日线收盘」的那个交易日才算当前实时价。判定规则：

- **`premarket.as_of` 的日期 > `snapshot.as_of`** → 这是**今日盘前价**，当作「当前价」用于趋势/信号判定，对比基准（昨收）= `snapshot.price`。报告里给该票标 🌅 盘前。
- **`premarket.as_of` 的日期 == `snapshot.as_of`** → 盘前所属交易日已计入日线收盘，是**过期盘前**，忽略，当前价仍用 `snapshot.price`。
- `premarket` 为 `null` → 当前价用 `snapshot.price`。

（`scripts/analyze.py` 的 `live_price()` 就是这个规则，逐票输出已自动处理。）

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

> **当前价 = 鲜活盘前价（若有）否则 snapshot.price**：趋势判定和 Step 3 信号里的「当前价」按上面的盘前鲜活判定取值——盘前时段就是今日盘前价（🌅），其余时段是当日收盘。
> MA20/MA50/RSI/相对强弱/量能比**仍按日线计算**（盘前量是部分日量，不可与 20 日均量直接比，所以量能比不掺盘前）。

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

> 这里的「当前价」按 Step 2 的盘前鲜活判定取值：盘前时段 = 今日盘前价，「昨收」= `snapshot.price`；其余时段「当前价」= 当日收盘，「昨收」= `close[-2]`。这样**盘前就能跑出加/减仓信号**，你可以在开盘前下单。

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

### Step 5 — 汇总 + 下单

把 Step 4 里有信号的票汇总成结构化订单。

**Connector 已连接**：直接调用 IBKR connector 发起订单请求（每个买单带止损单）。同时在报告里列出已发的订单清单，方便用户在 IBKR 客户端的弹窗里核对：

```
═══════════════════════════════════════════════════════════
  📋 已通过 IBKR connector 发起（请在 IBKR 客户端确认）
═══════════════════════════════════════════════════════════

[1] BUY  NVDA  20股  限价 $215.00  止损 $204.81 (OCO)
     理由: 多头共振 RSI 51.1 量能温和放大
     connector status: submitted, order_id=...

[2] SELL GOOGL 50股 市价
     理由: 减仓警示，跌破 MA20 + 放量 + 收阴
     connector status: submitted, order_id=...

═══════════════════════════════════════════════════════════
  数据源 yfinance EOD；下单前已通过 connector 验真当前价。
  实际成交以 IBKR 客户端二次确认后的结果为准。
═══════════════════════════════════════════════════════════
```

**Connector 未连接**：退化为参考模式，输出同样格式但状态写「待手动下单」，让用户自己去 IBKR 客户端操作。

---

## 数据更新机制

两个 GitHub Actions cron 跑同一个 `build_cache.py`，缓存里始终带最新的盘前 snapshot：

- **盘前 cron**：`0 13 * * 1-5` (UTC) ≈ 美东 09:00（夏令时）/ 08:00（冬令时），开盘前把**当日盘前价**写进缓存——这是「盘前就能下单」的数据来源。此时日线 `snapshot.price` 仍是昨收，`premarket` 是今日盘前（date > snapshot.as_of，鲜活）。
- **EOD cron**：`30 21 * * 1-5` (UTC) = 美东收盘后约 1.5 小时，写当日完整收盘日线。
- **手动触发**：`gh workflow run daily-update.yml -R wabicai/ibkr-daily-review`
- **本地手动更新**：`python scripts/build_cache.py`（覆盖 `latest.json` 和当日 dated 文件；盘前时段本地跑就能即时拿到当日盘前价）

## 重要约定

- 本仓库**公开**：**绝不**把持仓 / 账户 / 订单回执 / 任何带账号 ID 的数据 push 进来
  - 持仓只能在对话里临时贴 或 走本地 `positions.local.json`（gitignore）
  - 下单后 IBKR connector 的回执只在你跟用户的对话里展示，不写盘
- **Connector 连上时直接发单**——二次确认交给 IBKR 客户端弹窗（用户那边的最后一道闸）
- 盘前/盘中数据滞后：缓存（EOD + 盘前 cron 的盘前 snapshot）用于决策，**下单前务必用 IBKR connector 拉实时 `snapshot` 校验当前价**——yfinance 盘前是分钟级且部分券源盘前量为 0，实时下单价/股数/止损一律以 IBKR 最新 snapshot 为准
- 字段对照表见 Step 0a，旧的 IBKR prompt 习惯也适用，只是去掉了 `contract_id` / `exchange` / `account` 这三组
