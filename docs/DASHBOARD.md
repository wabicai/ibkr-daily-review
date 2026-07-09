# IBKR Daily Review v4 Professional Dashboard

本文件定义每日盘前/盘后输出格式。目标不是写长篇观点，而是输出可执行的交易作战计划。

## 1. Dashboard

必须包含：

- 数据日期与当前价格源
- 账户净值、现金、持仓数量、未成交订单数量
- Market Score / AI Confidence
- 今日最终动作：BUY / LIMIT BUY / SELL / WATCH / NO TRADE

## 2. Market Score

总分 100 分：

| 模块 | 权重 |
|---|---:|
| QQQ 趋势 | 20 |
| SMH 趋势 | 20 |
| 市场广度与风险偏好 | 20 |
| 宏观与利率 | 20 |
| 新闻与事件风险 | 20 |

解释：

- >= 85：Strong Risk-On，允许正常建仓
- 75–84：Risk-On，只允许高质量机会
- 60–74：Neutral，只允许小仓或 ETF
- < 60：Risk-Off，原则上不新建风险仓位

## 3. Theme Ranking

每天输出 AI / Semiconductor / Memory / Networking / Equipment / Software / Defensive 等主题排名。

使用 1–5 星：

- 五星：主线，可交易
- 四星：强观察
- 三星：观察
- 二星及以下：背景

## 4. Candidate Ranking

最多输出前 8 个候选，不要平均分析所有股票。

每个候选必须包含：

- 当前价，且来自 IBKR broker snapshot
- 所属主题
- Candidate Score
- 星级
- 操作结论
- 核心理由

## 5. Trading Plan

只有高质量机会才进入交易计划。

任何买入建议必须包含：

- 触发条件
- 股数
- 限价
- 止损
- 计划风险金额
- 风险收益比 RR
- 失效条件

不允许市价追高。默认 `limit_only`。

## 6. Risk Center

必须检查：

- 单票仓位是否超过 `max_position_pct`
- 主题集中度是否超过 `max_theme_pct`
- 现金是否低于最低要求
- 财报黑窗和重大事件
- 止损距离是否过宽
- 总体止损风险是否合理

`risk_per_trade_pct = null` 且 `risk_per_trade_mode = ai_dynamic` 时，不使用固定 1% 风险上限。

## 7. AI Investment Committee

每笔交易必须经过五项评分：

| 委员 | 职责 |
|---|---|
| Trend | 趋势是否健康 |
| Relative Strength | 是否跑赢 QQQ / SMH / 主题 |
| News | 新闻和事件是否支持 |
| Macro | 宏观环境是否允许加风险 |
| Risk | 仓位、止损、RR、现金、集中度是否通过 |

批准规则：

- 总分 >= 85
- Risk 委员不能否决
- RR >= `minimum_rr`
- 当前价、限价、止损和仓位计算全部使用 IBKR snapshot

## 8. Execution

最后必须给出简洁执行表：

| Action | Symbol | Shares | Limit | Stop | RR | Status |
|---|---|---:|---:|---:|---:|---|

如果没有高质量机会，必须明确写：

> 今日不操作。

并输出 No Trade Report。

## 9. No Trade Report

没有下单时，必须列出最关键的 1–5 个原因，例如：

- Market Score 不足
- RR 不足
- 止损距离过宽
- 跳空过大，追价风险高
- 财报或宏观事件风险过高
- 现金或集中度限制

## 10. Strategy Statistics

如果 `cache/performance.json` 有可用数据，展示：

- 交易次数
- 胜率
- Profit Factor
- 平均计划 RR / 实现 RR
- 最大回撤
- Alpha vs QQQ / SMH

不得把账户 ID、订单 ID、成交回执或任何私人账户数据写入公开仓库。
