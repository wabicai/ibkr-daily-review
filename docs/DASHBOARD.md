# IBKR Daily Review v4.2 Professional Dashboard

本文件定义每日盘前、盘中和盘后输出格式。目标是输出可执行的限价交易计划。

## 1. Dashboard

必须包含数据日期、价格源、账户净值、现金、持仓数量、未成交订单数量、Market Score、AI Confidence 和最终动作。

## 2. Market Score

Market Score 继续按 QQQ 趋势、SMH 趋势、市场广度与风险偏好、宏观与利率、新闻与事件风险计算，但只用于描述市场环境、调整选股标准和参考仓位，不是交易硬门槛。

## 3. 美股七姐妹 Monitor

每日必须对比 AAPL、MSFT、NVDA、AMZN、META、GOOGL、TSLA。七只全部是可交易候选。

每只展示：IBKR 当前价、涨跌幅、趋势、相对 QQQ 强弱、组内排名、成交量确认、Candidate Score 和操作结论。

同时展示上涨/下跌家数、MA20/MA50 上方家数、跑赢 QQQ 家数和 Leadership Ranking。

## 4. Theme Ranking

覆盖 AI Infrastructure、Semiconductor、Memory / Storage、Networking / ASIC、Semiconductor Equipment、AI Software、Mega-cap Platforms、AI Autonomy / Robotics 和 Defensive Assets。

## 5. Candidate Ranking

最多输出前 8 个候选。七姐妹参与统一排名。每个候选包含 IBKR 当前价、主题、Candidate Score、星级、操作结论和核心理由。

Candidate Score 和星级只用于排序，不构成固定准入门槛。

## 6. Trading Plan

AI 判断挂单价格、止损、仓位、现金、集中度和事件风险合适的候选即可进入交易计划。

任何买入建议必须包含：

- 触发条件
- 股数
- 限价
- 止损
- 计划风险金额
- RR
- 失效条件

RR 必须展示并解释，但不再要求固定达到 2.2。默认 `limit_only`，不允许市价追高。

## 7. Risk Center

必须检查：

- 单票仓位是否超过 `max_position_pct`
- 主题集中度是否超过 `max_theme_pct`
- 现金是否低于最低要求
- 财报黑窗和重大事件
- 止损距离是否合理
- 总体止损风险是否合理

单笔风险与总体止损风险由 AI 动态评估。

## 8. AI Investment Committee

每笔候选继续展示五项评分：Trend、Relative Strength、News、Macro、Risk。

委员会评分用于解释交易质量和比较候选，不再设固定 85 分批准线，也不再拥有机械一票否决权。AI 最终综合判断：

- 限价是否有足够吸引力
- 止损是否清晰且合理
- 计划仓位是否匹配风险
- 现金和集中度是否允许
- 财报与事件风险是否可接受
- 当前成交结构是否适合挂单

Committee Score 可以低于 85，只要 AI 明确说明为何仍值得挂单。

## 9. Execution

| Action | Symbol | Shares | Limit | Stop | RR | Status |
|---|---|---:|---:|---:|---:|---|

只要 AI 判断挂单组合合适，就可以创建非 live 的 IBKR order instruction，等待用户在 IBKR 客户端确认。

## 10. No Trade Report

没有挂单时，列出最关键原因，例如：

- 当前限价没有吸引力
- 止损结构不合理
- 财报或宏观事件风险过高
- 跳空过大或成交结构不稳定
- 现金或集中度限制
- 当前报价不可用
- AI 综合判断暂不值得进入

Market Score、RR 或 Committee Score 不得单独作为机械的不交易原因。

## 11. Strategy Statistics

如 `cache/performance.json` 有数据，展示交易次数、胜率、Profit Factor、平均计划 RR / 实现 RR、最大回撤和 Alpha vs QQQ / SMH。

不得把账户 ID、订单 ID、成交回执或任何私人账户数据写入公开仓库。