# ibkr-daily-review

美股 watchlist 每日技术分析数据缓存。GitHub Actions 在每个交易日盘前和美东收盘后用 yfinance 抓取 OHLCV，写入 `cache/`；本地或连接器读取后计算 MA20 / MA50 / RSI / 相对强弱 / 量能比，并结合组合风险、市场状态和事件风险生成复盘。

## 结构

```text
.
├── .github/workflows/daily-update.yml   # 每日定时 + 手动触发
├── cache/
│   ├── YYYY-MM-DD_market.json           # 历史快照（按日期）
│   └── latest.json                      # 最新一份（覆盖式）
├── config/
│   ├── watchlist.json                   # 交易候选、基准、市场状态标的
│   ├── risk_rules.json                  # 仓位/现金/止损风险规则
│   └── events.json                      # 财报、宏观和公司事件
├── scripts/
│   ├── build_cache.py                   # yfinance → cache JSON
│   ├── analyze.py                       # 离线技术分析
│   ├── portfolio_risk.py                # 本地持仓集中度与止损风险
│   ├── market_regime.py                 # Risk-on / Neutral / Risk-off
│   ├── event_risk.py                    # 财报与重大事件窗口
│   ├── update_events.py                 # 自动刷新事件日历
│   └── import_performance.py            # 导入脱敏后的真实策略交易
├── CLAUDE.md                            # 每日复盘与下单约定
├── RISK_MODULES.md                      # 新增风险模块说明
└── requirements.txt
```

## 本地使用

```bash
pip install -r requirements.txt
python scripts/build_cache.py
python scripts/analyze.py
python scripts/market_regime.py
python scripts/event_risk.py
python scripts/portfolio_risk.py  # 需要本地 positions.local.json
```

分析指定日期：

```bash
python scripts/analyze.py 2026-06-04
```

## Watchlist 角色

`config/watchlist.json` 中：

- `candidate`：允许进入交易信号评估
- `benchmark`：相对强弱基准，目前为 QQQ
- `context`：只用于市场状态判断，禁止生成交易订单

当前 context 标的是 SPY、IWM、TLT、GLD。

## 修改 watchlist

编辑 `config/watchlist.json` 后重新运行 `build_cache.py`。GitHub Actions 下一次运行也会使用新列表。

## 组合数据安全

仓库公开，严禁提交账户和持仓信息。组合风险脚本只读取已 gitignore 的本地文件 `positions.local.json`。格式示例见 `scripts/portfolio_risk.py`。

## 数据源

- yfinance EOD 与盘前分钟数据
- 历史窗口：120 个交易日
- 相对强弱基准：QQQ
- 基本面、财报日期和新闻在决策时必须用可靠最新来源复核

## 风控

完整规则见 `RISK_MODULES.md` 和 `config/risk_rules.json`。任何买入都必须有明确止损；context 标的永远不能生成订单。

## 免责

仓库提供数据与辅助分析，不保证收益。真实交易必须由用户在 IBKR 界面审核确认。


## 策略统计同步

`cache/performance.json` 只保存脱敏后的策略级数据。IBKR/其他券商数据应先由受信任的连接器整理成如下输入，再运行：

```bash
python scripts/import_performance.py trades.sanitized.json --source ibkr_connector
```

允许字段包括 symbol、entry/exit date、realized P/L、planned/realized RR、entry/exit reason、market/theme score。
导入器会拒绝 account id、NAV、cash、positions、broker order/execution id 等私有字段。不要把原始券商导出提交到仓库。

## 事件日历

工作日自动运行 `scripts/update_events.py`。财报日期使用 yfinance 做发现，交易前仍必须用公司 IR 等一手来源复核；宏观日期采用仓库内人工审阅的高影响事件表。
`events.json.metadata.status != ok` 或日历为空时，必须视为“事件数据不可靠”，不能视为“没有事件风险”。
