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
4. **不要使用固定 1% 单笔风险上限。** `risk_per_trade_pct: null` 且 `risk_per_trade_mode: ai_dynamic` 时，由 AI 结合整体组合、仓位、现金、止损距离、风险收益比、市场状态、主题集中度、财报事件和信号质量动态判断。不要仅因为止损风险超过账户净值 1% 就否决订单。
5. `signal_confirmation_days = 0` 和 `trade_cooldown_days = 0` 时，不要求机械等待确认天数或冷却期；由 AI 直接判断信号质量。

## Watchlist 分层

`config/watchlist.json` 使用四层结构：

1. **core**：每天优先分析，AI 基础设施核心池。
2. **satellite**：卫星池，memory/storage/optical/connectivity/power cooling 等扩展主题，有强信号时可交易。
3. **etf**：ETF 池，既用于市场状态，也可交易。
4. **context**：仅作为主题和市场背景，不生成订单，除非用户明确提升为 candidate。

当前 Memory / Storage 规则：

- MU 是核心池标的。
- SNDK 和 SK 海力士（`000660.KS`）是卫星池，可在信号足够强、IBKR 可交易且风险收益比合理时生成订单指令。
- 三星电子（`005930.KS`）和 Kioxia（`285A.T`）暂时只作为 context，用于判断 memory/NAND 行业状态，不直接交易。

`auto_opportunity_pool` 只作为研究指令：每天可额外扫描 5–10 只美股 AI 基础设施机会，但不要自动写入仓库；连续强势且主题匹配时，在报告里建议提升到 satellite/core。

## ETF 与 context 规则

QQQ、SPY、IWM、SMH、TLT、GLD 虽然承担 benchmark 或 context 作用，但同时允许作为可交易 ETF 生成买入、卖出、持有和观察建议；不要因为其角色而禁止交易。

ENTG 继续仅作为 context，不生成交易建议或订单指令。

为避免重复暴露，QQQ、SPY、IWM 这三只宽基 ETF 同时最多新建一只；SMH 作为行业 ETF 单独计算，TLT 和 GLD 作为防御资产单独计算。

不要把“QQQ 和 SMH 开盘后至少稳定 1 小时”或“候选股高开不得超过 3%”作为必要条件；应结合实时价格、趋势、风险收益比和整体市场状态直接判断。

---

## 分析参数

- **趋势基准**：MA20 / MA50（日线收盘价）
- **辅助指标**：RSI 14 日（Wilder 平滑法）
- **相对强弱**：标的近 20 日涨幅 − QQQ 同期涨幅
- **量能**：近 5 日均量 ÷ 近 20 日均量
- **风格**：趋势交易，中长周期；无明确信号则「观察/持有」

## 每日执行流程

### Step 0 — 数据获取

1. **优先 `git -C <repo路径> pull --ff-only`** 拉一次远端最新缓存。
2. 读 `cache/latest.json`。
3. 看 `market_data["QQQ"].snapshot.as_of`：
   - 等于今天 → ✅ 用，报告首行注明 `📦 数据日期 YYYY-MM-DD`。
   - 是上一个交易日（今天美股没开盘 / Actions 还没跑）→ ⚠️ 报告首行说明「最新可用数据为 YYYY-MM-DD」再继续。
   - 超过 3 个交易日 → 提示用户检查 Actions 是否失败，先不出报告。
4. 连接 IBKR 获取账户净值、现金、持仓、成交记录、未成交订单和最新行情。

### Step 1 — 持仓核算

仓库本身不存持仓。优先使用 IBKR connector 的实时账户数据；无 connector 时才使用用户提供的持仓或本地 `positions.local.json`。

拿到持仓后，对每只票算：

- 当前市值
- 仓位占比
- 未实现盈亏
- 止损风险
- 所属主题集中度

### Step 2 — 技术指标

逐票计算：

```text
MA20         = mean(close[-20:])
MA50         = mean(close[-50:])
RSI(14)      = Wilder 平滑法
量能比       = mean(volume[-5:]) / mean(volume[-20:])
相对强弱     = (close[-1]/close[-21] - 1)*100 − (QQQ_close[-1]/QQQ_close[-21] - 1)*100
趋势         = price>MA20>MA50 → 上升↑
               price<MA20<MA50 → 下降↓
               否则             → 盘整→
```

实时价用于触发条件、限价、止损和风险收益比；日线指标仍按缓存历史数据计算。

### Step 3 — 信号判定

**减仓警示**（满足任一即触发）：

- `当前价 < MA20` 且 `量能比 > 1.2` 且 `当前价 < 昨收`
- `当前价 < min(近 5 日收盘) × 0.99`（跌破近期低点）

**加仓 / 建仓候选**（无减仓信号，且下列至少 3 项成立）：

- `当前价 > MA20`
- `MA20 > MA50`
- `量能比 > 1.5` 且 `当前价 > 昨收`
- `50 ≤ RSI(14) ≤ 70`
- `相对强弱 ≥ 0`（跑赢 QQQ）

同时必须通过 `config/risk_rules.json` 中的仓位、主题集中度、现金比例和财报黑窗规则。单笔风险和总止损风险使用 AI 动态评估，不使用固定 1% 或固定总风险上限。

否则 → 观察/持有。

### Step 4 — 操作建议

对每个持仓和候选标的输出：

- 持有、减仓、止损、平仓、建仓或观察结论
- 当前价、MA20、MA50、RSI
- 支撑、阻力、参考入场区间
- 止损 = 近 2 周最低 × 0.97，或按实时风险收益比重算
- 触发条件、股数、限价、止损和理由

任何买入建议必须包含触发条件、股数、限价和止损。

### Step 5 — 汇总 + 下单

把 Step 4 里有高质量信号且通过全部风控的票汇总成结构化订单。

**Connector 已连接**：可以直接调用 IBKR connector 发起订单请求（每个买单带止损单）。报告里列出已发起的订单清单，方便用户在 IBKR 客户端弹窗里核对。实际成交以 IBKR 客户端二次确认后的结果为准。

**Connector 未连接**：退化为参考模式，输出同样格式但状态写「待手动下单」。

没有高质量信号时明确写“不操作”。

## 输出结构

1. 数据日期和账户摘要
2. 市场状态
3. 当日表现归因
4. 持仓逐票复盘
5. core / satellite / ETF 候选逐票复盘
6. Memory / Storage 主题专项观察
7. 风险检查
8. 财报与事件风险
9. 盘前计划有效性复盘
10. 下一交易日条件单预案或已发起订单指令
11. 最终结论：操作或不操作

## 数据更新机制

两个 GitHub Actions cron 跑同一个 `build_cache.py`，缓存里始终带最新的盘前 snapshot：

- **盘前 cron**：`0 13 * * 1-5` (UTC)
- **EOD cron**：`30 21 * * 1-5` (UTC)
- **手动触发**：`gh workflow run daily-update.yml -R wabicai/ibkr-daily-review`
- **本地手动更新**：`python scripts/build_cache.py`

## 重要约定

- 本仓库公开：绝不把持仓 / 账户 / 订单回执 / 任何带账号 ID 的数据 push 进来。
- 持仓、账户和订单回执只在对话或 IBKR connector 中使用，不写入仓库。
- Connector 连上时可以发起订单请求，最终确认交给 IBKR 客户端弹窗。
- 盘前/盘中数据滞后：缓存用于决策前置分析，下单前务必用 IBKR connector 拉实时行情校验当前价。
