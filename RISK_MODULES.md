# Risk, market-regime, and event modules

These modules extend the technical watchlist review without storing brokerage data in the public repository.

## 1. Portfolio risk

`python scripts/portfolio_risk.py`

Reads local-only `positions.local.json`, `cache/latest.json`, `config/watchlist.json`, and `config/risk_rules.json`.

Checks:

- single-position concentration
- theme concentration
- cash floor
- stop-risk reasonableness
- total portfolio stop-risk ceiling

`positions.local.json` remains local and must never be committed.

Per-trade risk is dynamic. `risk_per_trade_pct: null` with `risk_per_trade_mode: ai_dynamic` means there is no fixed 1% per-trade risk cap. The model should judge each proposed order from overall portfolio context, cash level, position size, stop distance, risk/reward, market regime, theme concentration, earnings/event risk, signal quality, and cooldown status. Do not reject an otherwise valid order only because its stop distance exceeds 1% of account net liquidation value.

## 2. Market regime and ETF handling

`python scripts/market_regime.py`

QQQ, SPY, IWM, SMH, TLT, and GLD may be used both as market context and as actionable ETF candidates. Their benchmark or context role must not automatically exclude them from the daily decision table or order-instruction generation.

ENTG remains context-only and must not receive trade instructions.

ETF grouping rules:

- QQQ, SPY, and IWM are broad-market ETFs. At most one of these may receive a new-entry instruction in the same review cycle.
- SMH is a sector ETF and is counted separately from broad-market ETFs.
- TLT and GLD are defensive assets and are counted separately from broad-market and sector ETFs.

The market-regime module still classifies the environment as `RISK-ON`, `NEUTRAL`, or `RISK-OFF` from price/MA20/MA50/20-day-return conditions.

## 3. Event risk

`python scripts/event_risk.py`

Reads `config/events.json` and flags:

- earnings blackout windows
- high-risk events within two days
- position-size review requirements

Event dates must be populated from reliable primary sources. Empty or stale event data must never be treated as evidence that no event exists.

## Daily decision order

1. Validate cache freshness.
2. Read live IBKR balances, positions, orders, and snapshots when available.
3. Run portfolio-risk checks.
4. Run market-regime classification.
5. Run event-risk checks.
6. Run technical analysis for candidates and actionable ETFs.
7. Add current fundamentals and reliable news.
8. If IBKR connector is connected and all risk gates pass, create IBKR order instructions for user-side confirmation. Do not assume an instruction is live until IBKR confirms it and the user approves the client-side prompt.

## Hard rules

- Context-only symbols never create trade instructions.
- QQQ, SPY, IWM, SMH, TLT, and GLD are not excluded merely because they are benchmark or context inputs.
- Do not add exposure when cash is below the configured floor unless the action reduces another risk first.
- Do not add a position above the single-position or theme limit.
- Do not open a new position inside the configured earnings blackout window.
- Do not use a fixed 1% per-trade risk cap; use dynamic AI risk assessment instead.
- Every buy instruction needs a defined stop. If a bracket/OCO instruction is unavailable, show the stop explicitly and do not imply it is live.
- Never commit account balances, positions, orders, account IDs, or broker responses.
