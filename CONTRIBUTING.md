# Contribution workflow

## Review gate

Strategy, risk-rule, watchlist, pricing-source, and connector-behavior changes should be proposed through a pull request before they are merged into `main`.

The user reviews and merges manually.

Direct pushes to `main` should be reserved for urgent fixes or explicit user-approved hotfixes.

## Daily review safety

- Keep account data, positions, balances, broker responses, and order receipts out of the public repository.
- GitHub cache is for historical market data and indicators.
- Broker snapshots are the preferred source for current prices when available.
- Cached premarket data is fallback/context only.
