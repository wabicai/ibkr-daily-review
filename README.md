# ibkr-daily-review

美股 watchlist 每日技术分析数据缓存。GitHub Actions 在每个交易日美东收盘后用 yfinance 抓 20 只票的 OHLCV，写入 `cache/`，本地 Claude Code 拉到后直接计算 MA20 / MA50 / RSI / 相对强弱 / 量能比，生成复盘报告。

## 结构

```
.
├── .github/workflows/daily-update.yml   # 每日定时 + 手动触发
├── cache/
│   ├── 2026-06-04_market.json            # 历史快照（按日期）
│   └── latest.json                       # 最新一份（覆盖式）
├── scripts/
│   ├── build_cache.py                    # yfinance → cache JSON
│   └── analyze.py                        # 离线技术分析
├── config/watchlist.json                 # 标的 + 基准
├── CLAUDE.md                             # 给 Claude 的读取约定
└── requirements.txt
```

## 本地使用

```bash
pip install -r requirements.txt
python scripts/build_cache.py            # 拉数据
python scripts/analyze.py                # 看最新
python scripts/analyze.py 2026-06-04     # 看指定日
```

## 让 Claude 跑分析

```bash
# 在 Claude Code 工作目录里
cd ~/Documents/GitHub/ibkr-daily-review
git pull
# 然后告诉 Claude："帮我看下今天的美股 watchlist"
```

Claude 会按 `CLAUDE.md` 的约定读 `cache/latest.json` 并算指标。

## 修改 watchlist

编辑 `config/watchlist.json`，重新跑 `build_cache.py`，下次 Actions 也会用新的列表。

## 数据源

- yfinance EOD（盘后 30 分钟左右更新）
- 历史窗口：120 个交易日（足够覆盖 MA50 + 20 天相对强弱）
- 基准：QQQ

## 免责

仓库只做技术指标计算，**不连券商、不下单、非投资建议**。
