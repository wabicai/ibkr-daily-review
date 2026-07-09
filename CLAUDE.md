# 每日美股 Watchlist 复盘 + v4 专业交易仪表盘

请用中文回复。

本仓库是 GitHub Actions 每个交易日通过 yfinance 更新的 OHLCV 缓存层。读取缓存的 AI 会连接 **IBKR connector** 获取账户、持仓、订单与实时行情，并在高质量信号和风控全部通过时创建 **IBKR order instruction**。

## v4 核心原则

1. **每天只筛选 1–2 笔最高质量交易**。宁可错过，不为交易而交易。
2. 输出必须是可执行的交易作战计划，而不是长篇观点。
3. 当前价、触发价、限价、止损、股数、风险收益比和仓位计算必须使用 **IBKR broker snapshot**。
4. `cache/latest.json` 只用于历史 K 线、MA20、MA50、RSI、量能比、相对强弱、支撑阻力和缓存日期。
5. 不要用 `cache/latest.json` 的 `premarket.as_of` 判断是否需要拉 IBKR 实时价。规则固定为：`cached_premarket_usage=fallback_only`、`current_price_source=broker_snapshot`、`require_current_quote=true`。
6. 不使用固定 1% 单笔风险上限。`risk_per_trade_pct = null` 且 `risk_per_trade_mode = ai_dynamic` 时，由 AI 动态评估。
7. `signal_confirmation_days = 0` 和 `trade_cooldown_days = 0` 时，不机械等待确认天数或冷却期。
8. 没有高质量信号时，必须明确写：**今日不操作**。

## 配置文件读取顺序

每次复盘必须读取：

1. `CLAUDE.md`
2. `RISK_MODULES.md`
3. `config/watchlist.json`
4. `config/risk_rules.json`
5. `config/events.json`
6. `config/strategy.json`
7. `config/scoring.json`
8. `cache/latest.json`
9. 如存在：`cache/performance.json`
10. 如存在：`docs/DASHBOARD.md`

## 下单流程

如果 IBKR connector 已连接，可以创建 **IBKR order instruction**。该 instruction 不是 live order，必须等待用户在 IBKR 客户端确认后才会提交。

硬规则：

1. 每个买入建议必须有明确止损。
2. 如果 connector 不支持 bracket/OCO/STP，报告里必须明确止损不是 live stop，不能暗示已自动保护。
3. 每笔订单必须展示：标的、方向、股数、限价、止损、RR、理由。
4. 不允许市价追高；默认 `limit_only`。
5. 不得把账户 ID、订单 ID、成交回执、账户余额、持仓等私人数据写入公开仓库。

## Watchlist 分层

`config/watchlist.json` 使用四层结构：

1. **core**：每天优先分析，AI 基础设施核心池。
2. **satellite**：卫星池，memory/storage/optical/connectivity/power cooling 等扩展主题，有强信号时可交易。
3. **etf**：ETF 池，既用于市场状态，也可交易。
4. **context**：仅作为主题和市场背景，不生成订单，除非用户明确提升为 candidate。

当前 Memory / Storage 规则：

- MU 是 core 标的。
- SNDK 和 SK 海力士（`000660.KS`）是 satellite，可在信号足够强、IBKR 可交易且 RR 合理时生成订单指令。
- 三星电子（`005930.KS`）和 Kioxia（`285A.T`）暂时只作为 context，不直接交易。
- ENTG 继续仅作为 context，不生成交易建议或订单指令。

ETF 规则：

- QQQ、SPY、IWM、SMH、TLT、GLD 虽然承担 benchmark 或 context 作用，但同时允许作为可交易 ETF 生成买入、卖出、持有和观察建议。
- QQQ、SPY、IWM 三只宽基 ETF 同时最多新建一只。
- SMH 作为行业 ETF 单独计算。
- TLT 和 GLD 作为防御资产单独计算。

## v4 每日执行流程

### Step 0 — 数据获取

1. 优先 `git -C <repo路径> pull --ff-only` 拉取最新缓存。
2. 读取所有配置文件和 `cache/latest.json`。
3. 验证缓存日期。如果超过 3 个交易日，提示检查 Actions，不出完整交易计划。
4. 连接 IBKR 获取账户净值、现金、持仓、未成交订单、已保存 instructions 和 broker snapshot。
5. 当前价必须来自 IBKR snapshot。

### Step 1 — Dashboard

输出：

- 数据日期
- 当前价格源
- 账户净值、现金比例、持仓数量、未成交订单数量
- Market Score
- AI Confidence
- 今日最终动作：BUY / LIMIT BUY / SELL / WATCH / NO TRADE

### Step 2 — Market Score

按 `config/scoring.json` 打 100 分：

- QQQ 趋势
- SMH 趋势
- 市场广度与风险偏好
- 宏观与利率
- 新闻与事件风险

解释：

- >= 85：Strong Risk-On，允许正常建仓
- 75–84：Risk-On，只允许高质量机会
- 60–74：Neutral，只允许小仓或 ETF
- < 60：Risk-Off，原则上不新建风险仓位

### Step 3 — Theme Ranking

每天给出主题排名，至少覆盖：

- AI Infrastructure
- Semiconductor
- Memory / Storage
- Networking / ASIC
- Semiconductor Equipment
- AI Software
- Defensive assets

使用 1–5 星。

### Step 4 — Candidate Ranking

不要平均分析所有股票。最多输出前 8 个候选。

每个候选必须包含：

- 当前价（IBKR snapshot）
- 所属主题
- Candidate Score
- 星级
- 操作结论
- 核心理由

候选评分按 `config/scoring.json`：

- Trend
- Relative Strength
- Theme Strength
- News Quality
- Risk Reward and Execution

### Step 5 — Risk Center

检查：

- 单票仓位是否超过 `max_position_pct`
- 主题集中度是否超过 `max_theme_pct`
- 现金是否低于最低要求
- 财报黑窗和重大事件
- 止损距离是否过宽
- 总体止损风险是否合理

单笔风险和总止损风险使用 AI 动态评估。

### Step 6 — AI Investment Committee

每笔交易必须经过五项评分：

| 委员 | 职责 |
|---|---|
| Trend | 趋势是否健康 |
| Relative Strength | 是否跑赢 QQQ / SMH / 主题 |
| News | 新闻和事件是否支持 |
| Macro | 宏观环境是否允许加风险 |
| Risk | 仓位、止损、RR、现金、集中度是否通过 |

批准条件：

- 总分 >= `minimum_confidence`
- Risk 委员不能否决
- RR >= `minimum_rr`
- 符合现金、仓位、主题集中度和财报黑窗规则

### Step 7 — Trading Plan

只有通过 AI Investment Committee 的候选才能进入交易计划。

任何买入建议必须包含：

- 触发条件
- 股数
- 限价
- 止损
- 计划风险金额
- RR
- 失效条件

默认只给 1 笔最佳交易；最多 2 笔。

### Step 8 — Execution

若 connector 支持并且风控通过，可以创建 IBKR order instruction。

最后必须给出执行表：

| Action | Symbol | Shares | Limit | Stop | RR | Status |
|---|---|---:|---:|---:|---:|---|

没有高质量机会时输出：

> 今日不操作。

并附 No Trade Report。

### Step 9 — Strategy Statistics

如 `cache/performance.json` 有数据，展示：

- 交易次数
- 胜率
- Profit Factor
- 平均计划 RR / 实现 RR
- 最大回撤
- Alpha vs QQQ / SMH

## 标准输出结构

1. Dashboard
2. Market Score
3. Theme Ranking
4. Candidate Ranking
5. Trading Plan
6. Risk Center
7. AI Investment Committee
8. Execution
9. No Trade Report（无交易时必须有）
10. Strategy Statistics
11. 最终结论：操作或不操作

## 数据更新机制

两个 GitHub Actions cron 跑同一个 `build_cache.py`：

- 盘前 cron：`0 13 * * 1-5` (UTC)
- EOD cron：`30 21 * * 1-5` (UTC)
- 手动触发：`gh workflow run daily-update.yml -R wabicai/ibkr-daily-review`
- 本地手动更新：`python scripts/build_cache.py`

## 重要约定

- 本仓库公开：绝不 push 持仓、账户、订单回执、账号 ID 或 broker 私密数据。
- 持仓、账户和订单回执只在对话或 IBKR connector 中使用，不写入仓库。
- 缓存用于历史分析，下单前必须用 IBKR broker snapshot 校验当前价。
- 最终目标：每天只回答一个问题——**今天是否有 1–2 笔值得执行的高质量交易？**
