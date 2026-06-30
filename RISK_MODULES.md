# Risk, market-regime, and event modules

These modules extend the technical watchlist review without storing brokerage data in the public repository.

## 1. Portfolio risk

`python scripts/portfolio_risk.py`

Reads local-only `positions.local.json`, `cache/latest.json`, `config/watchlist.json`, and `config/risk_rules.json`.

Checks:

- single-position concentration
- theme concentration
- cash floor
- defined stop-loss risk
- total portfolio stop-risk ceiling

`positions.local.json` remains local and must never be committed.

## 2. Market regime

`python scripts/market_regime.py`

Uses SPY, IWM, TLT, and GLD as context-only instruments. They are fetched into the same cache but must not generate trade orders. The script classifies the environment as `RISK-ON`, `NEUTRAL`, or `RISK-OFF` from price/MA20/MA50/20-day-return conditions.

Context instruments are marked with `role: context` in `config/watchlist.json`. Trading candidates use `role: candidate`; QQQ uses `role: benchmark`.

## 3. Event risk

`python scripts/event_risk.py`

Reads `config/events.json` and flags:

- earnings blackout windows
- high-risk events within two days
- position-size review requirements

Event dates must be populated from reliable primary sources. Empty or stale event data must never be treated as evidence that no event exists.

## Daily decision order

1. Validate cache freshness.
2. Read live IBKR balances, positions, orders, and snapshots.
3. Run portfolio-risk checks.
4. Run market-regime classification.
5. Run event-risk checks.
6. Run technical analysis for candidates.
7. Add current fundamentals and reliable news.
8. Create an IBKR instruction only when all risk gates pass.

## Hard rules

- Context-only symbols never create trade instructions.
- Do not add exposure when cash is below the configured floor unless the action reduces another risk first.
- Do not add a position above the single-position or theme limit.
- Do not open a new position inside the configured earnings blackout window.
- Every buy needs a defined stop. If a bracket/OCO instruction is unavailable, show the stop explicitly and do not imply it is live.
- Never commit account balances, positions, orders, account IDs, or broker responses.
