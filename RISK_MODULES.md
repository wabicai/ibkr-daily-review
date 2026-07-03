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
- total portfolio stop-risk context

`positions.local.json` remains local and must never be committed.

Per-trade risk is dynamic. `risk_per_trade_pct: null` with `risk_per_trade_mode: ai_dynamic` means there is no fixed 1% per-trade risk cap. The model should judge each proposed order from overall portfolio context, cash level, position size, stop distance, risk/reward, market regime, theme concentration, earnings/event risk, signal quality, and current exposure. Do not reject an otherwise valid order only because its stop distance exceeds 1% of account net liquidation value.

Total stop risk is also dynamic when `max_total_stop_risk_pct: null`. Still report total defined stop risk, but do not mechanically block orders from a fixed total-stop percentage.

## 2. Watchlist pools

`config/watchlist.json` uses schema version 2 and four pools:

1. `core` — daily priority review. AI infrastructure leaders and highest-conviction names.
2. `satellite` — memory, storage, optical, connectivity, power/cooling, and other theme extensions. These can trade when strong signals appear.
3. `etf` — QQQ/SPY/IWM/SMH/TLT/GLD. These are both market inputs and actionable ETFs.
4. `context` — non-actionable context symbols unless explicitly promoted by the user.

Current memory/storage coverage:

- MU in core.
- SNDK and SK Hynix (`000660.KS`) in satellite.
- Samsung Electronics (`005930.KS`) and Kioxia (`285A.T`) as context until trading availability/liquidity is verified and user approves promotion.

The optional `auto_opportunity_pool` is a research instruction only. The daily review may surface 5-10 extra US-listed AI infrastructure opportunities from current market/news context, but must not commit new symbols to the repo without user approval.

## 3. Market regime and ETF handling

`python scripts/market_regime.py`

QQQ, SPY, IWM, SMH, TLT, and GLD may be used both as market context and as actionable ETF candidates. Their benchmark or context role must not automatically exclude them from the daily decision table or order-instruction generation.

ENTG remains context-only and must not receive trade instructions.

ETF grouping rules:

- QQQ, SPY, and IWM are broad-market ETFs. At most one of these may receive a new-entry instruction in the same review cycle.
- SMH is a sector ETF and is counted separately from broad-market ETFs.
- TLT and GLD are defensive assets and are counted separately from broad-market and sector ETFs.

The market-regime module classifies the environment as `RISK-ON`, `NEUTRAL`, or `RISK-OFF` from price/MA20/MA50/20-day-return conditions.

## 4. Event risk

`python scripts/event_risk.py`

Reads `config/events.json` and flags:

- earnings blackout windows
- high-risk events within two days
- position-size review requirements

Event dates must be populated from reliable primary sources. Empty or stale event data must never be treated as evidence that no event exists.

## Daily decision order

1. Validate cache freshness.
2. Read live IBKR balances, positions, orders, and snapshots when available.
3. Review core pool first, satellite pool second, ETFs third, and context symbols only for market/theme information.
4. Run portfolio-risk checks.
5. Run market-regime classification.
6. Run event-risk checks.
7. Run technical analysis for candidates and actionable ETFs.
8. Add current fundamentals and reliable news.
9. If IBKR connector is connected and all risk gates pass, create IBKR order instructions for user-side confirmation. Do not assume an instruction is live until IBKR confirms it and the user approves the client-side prompt.

## Hard rules

- Context-only symbols never create trade instructions.
- QQQ, SPY, IWM, SMH, TLT, and GLD are not excluded merely because they are benchmark or context inputs.
- Do not add exposure when cash is below the configured floor unless the action reduces another risk first.
- Do not add a position above the single-position or theme limit.
- Do not open a new position inside the configured earnings blackout window.
- Do not use a fixed 1% per-trade risk cap; use dynamic AI risk assessment instead.
- Do not require fixed signal-confirmation days or cooldown days when the config sets them to 0; let AI judge signal quality directly.
- Every buy instruction needs a defined stop. If a bracket/OCO instruction is unavailable, show the stop explicitly and do not imply it is live.
- Never commit account balances, positions, orders, account IDs, or broker responses.
