# 每日美股 Watchlist 复盘 + v4.2 专业交易仪表盘

请用中文回复。

本仓库由 GitHub Actions 每个交易日更新 OHLCV 缓存。复盘时连接 IBKR connector 获取账户、持仓、订单和实时行情；AI 综合判断限价、止损、仓位、现金、集中度和事件风险后，可创建等待用户在 IBKR 客户端确认的 order instruction。

## 核心原则

1. 每天优先筛选 1–2 笔最合适的限价交易，不为交易而交易。
2. 输出必须是可执行的交易作战计划。
3. 当前价、触发价、限价、止损、股数、RR 和仓位计算必须使用 IBKR broker snapshot。
4. `cache/latest.json` 仅用于历史 K 线、MA20、MA50、RSI、量能比、相对强弱、支撑阻力和缓存日期。
5. `cached_premarket_usage=fallback_only`、`current_price_source=broker_snapshot`、`require_current_quote=true`。
6. 单笔风险与总止损风险由 AI 动态评估，不使用固定 1% 上限。
7. `signal_confirmation_days=0`、`trade_cooldown_days=0` 时，不机械等待。
8. Market Score、Candidate Score、Committee Score 和 RR 均保留，但只作为分析、排序和风险参考，不作为固定硬门槛。
9. 不再要求 RR >= 2.2，也不再要求 Committee >= 85。
10. 只要 AI 判断挂单价格、止损、仓位和整体风险合适，即可生成非 live order instruction。
11. 美股七姐妹全部是可交易候选，并必须进行每日横向对比。
12. 没有合适挂单时，必须明确写：**今日不操作**。

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

## 下单规则

- instruction 不是 live order，必须等待用户在 IBKR 客户端确认。
- 每个买入建议仍必须有明确止损。
- connector 不支持 bracket/OCO/STP 时，必须明确止损不是 live stop。
- 每笔订单必须展示：标的、方向、股数、限价、止损、RR、理由。
- 默认 `limit_only`，不允许市价追高。
- RR 可以低于 2.2，只要 AI 能解释为何当前挂单仍合理。
- Committee 可以低于 85，只要 AI 能解释风险、优势和失效条件。
- 不得把账户 ID、余额、持仓、订单或成交回执写入公开仓库。

## Watchlist 分层

`config/watchlist.json` 使用四层结构：

1. `core`：每日优先分析。
2. `satellite`：强信号时可交易。
3. `etf`：既做市场状态，也可交易。
4. `context`：只做背景，不生成订单，除非用户明确提升为 candidate。

Memory / Storage：

- MU 是 core。
- SNDK 和 `000660.KS` 是 satellite。
- `005930.KS` 和 `285A.T` 是 context。
- ENTG 是 context。

ETF：

- QQQ、SPY、IWM、SMH、DRAM、TLT、GLD 均可交易。
- QQQ、SPY、IWM 同一复盘周期最多新建一只。
- SMH、DRAM 按行业 ETF 单独计算。
- TLT、GLD 按防御资产计算。

## 美股七姐妹

每日必须对比以下可交易标的：AAPL、MSFT、NVDA、AMZN、META、GOOGL、TSLA。

七姐妹需要展示：

- IBKR 当前价与涨跌幅
- 趋势
- 相对 QQQ 强弱
- 组内排名
- 成交量确认
- Candidate Score
- 操作结论

同时计算上涨/下跌家数、MA20/MA50 上方家数、跑赢 QQQ 家数和 Leadership Ranking。

七姐妹参与统一 Candidate Ranking，可在 AI 判断限价、止损、仓位、现金、集中度和事件风险合适时生成 order instruction。

## 每日执行流程

### Step 0 — 数据获取

1. 读取全部配置与缓存。
2. 验证缓存日期；超过 3 个交易日则提示检查 Actions，不出完整交易计划。
3. 从 IBKR 获取账户净值、现金、持仓、未成交订单、已保存 instructions 和 broker snapshots。
4. 当前价必须来自 IBKR snapshot。

### Step 1 — Dashboard

输出数据日期、价格源、账户净值、现金比例、持仓数、未成交订单数、Market Score、AI Confidence 和最终动作。

### Step 2 — Market Score

计算 QQQ 趋势、SMH 趋势、市场广度与风险偏好、宏观与利率、新闻与事件风险。Market Score 只用于环境和仓位参考，不是订单准入条件。

### Step 3 — 美股七姐妹 Monitor

输出七姐妹完整对比、Breadth 和 Leadership Ranking。七姐妹是可交易候选。

### Step 4 — Theme Ranking

至少覆盖 AI Infrastructure、Semiconductor、Memory / Storage、Networking / ASIC、Semiconductor Equipment、AI Software、Mega-cap Platforms、AI Autonomy / Robotics、Defensive Assets。

### Step 5 — Candidate Ranking

最多输出前 8 个候选。每个候选包含 IBKR 当前价、主题、Candidate Score、星级、操作结论和核心理由。

### Step 6 — Risk Center

检查单票仓位、主题集中度、现金、财报黑窗、重大事件、止损距离和总体止损风险。

### Step 7 — AI Investment Committee

五项评分：Trend、Relative Strength、News、Macro、Risk。

委员会输出用于解释和比较，不设固定批准分数。RR 也不设固定最低值。AI 应综合判断：

- 限价是否有吸引力
- 止损是否合理
- 仓位是否与风险匹配
- 现金和集中度是否允许
- 财报和事件风险是否可接受
- 当前成交和市场结构是否支持挂单

### Step 8 — Trading Plan

AI 判断合适的候选即可进入交易计划。任何买入建议必须包含触发条件、股数、限价、止损、计划风险金额、RR 和失效条件。默认只给 1 笔，最多 2 笔。

### Step 9 — Execution

| Action | Symbol | Shares | Limit | Stop | RR | Status |
|---|---|---:|---:|---:|---:|---|

没有合适机会时输出：

> 今日不操作。

并附 No Trade Report。

### Step 10 — Strategy Statistics

如 `cache/performance.json` 有数据，展示交易次数、胜率、Profit Factor、平均计划 RR / 实现 RR、最大回撤和 Alpha vs QQQ / SMH。

## 标准输出结构

1. Dashboard
2. Market Score
3. Magnificent Seven Monitor
4. Theme Ranking
5. Candidate Ranking
6. Trading Plan
7. Risk Center
8. AI Investment Committee
9. Execution
10. No Trade Report（如适用）
11. Strategy Statistics
12. 最终结论

## 重要约定

- 仓库公开，绝不提交任何账户私密数据。
- 缓存用于历史分析，下单前必须用 IBKR broker snapshot 校验当前价。
- 最终目标：AI 每天判断是否存在 1–2 笔价格合适、风险可控的限价交易。