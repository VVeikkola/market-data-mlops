# market-data-mlops

A learning-focused data pipeline that collects daily market data for a stock (NVIDIA) and a cryptocurrency (Bitcoin), validates it, and analyses what different holding periods would have returned historically.

> **Status:** v1 requirements defined, implementation in progress.

## Why this project exists

This is a portfolio and learning project. The goal is to learn Data Engineering and MLOps by building a reliable pipeline for financial data step by step, starting from the fundamentals:

> *How do I collect, process and understand market data reliably?*

Machine learning comes later, only once the data pipeline is trustworthy.

## What v1 does

```
Tiingo (stocks) ─┐
                 ├─→ raw (stored as-is) → validation → transformation → clean dataset → holding-period analysis
Coinbase (crypto)┘                            │
                                              └─→ quarantine (invalid rows)
```

The analysis answers one question:

> *If someone had bought this asset on any day in the past and held it for N days, what returns would they have experienced?*

This is a **historical** analysis, not a forecast. Instead of a single number, it reports the distribution of outcomes for a user-selected holding period (e.g. 30 days, 6 months, 1 year, 5 years):

- mean and median return
- best and worst return
- share of periods that ended positive
- number of observations, with a warning when the result is based on few independent periods (overlapping windows share most of their days, so 1,000 five-year windows from 10 years of data are not 1,000 independent observations)

## Data

| | NVIDIA (NVDA) | Bitcoin (BTC-USD) |
|---|---|---|
| Source | [Tiingo](https://www.tiingo.com) REST API | [Coinbase Exchange](https://docs.cdp.coinbase.com/exchange/) public REST API |
| Granularity | 1 row per day (OHLCV) | 1 row per day (OHLCV) |
| Price used for returns | Adjusted close | Close |
| Authentication | API key (environment variable) | None |

- **History:** 10 years, configurable. A 5-year holding period needs clearly more than 5 years of data: with exactly 5 years there would be zero possible start dates.
- **Assets are configuration**, not code. Adding another stock or crypto should only require a config change.
- **Why adjusted close:** stock splits change the share price without changing the value of an investment. NVIDIA's 10-for-1 split in June 2024 dropped the price from ~$1,200 to ~$120 overnight. Using the raw close, returns across the split would show a false crash. Bitcoin has no splits, so the plain close is used.
- **Market data is not committed to this repository.** Only code is versioned; data is fetched by running the pipeline.

## Data quality

Raw API responses are **stored unchanged** before any processing. This makes it possible to debug what the API actually returned and to re-run processing without new API requests.

Validation reacts according to how certain it is that the data is broken:

| Level | Meaning | Example | Pipeline reaction |
|---|---|---|---|
| Soft rule | Unlikely but possible | \|daily return\| > 50 % | Keep the row, flag it, log `WARNING` |
| Hard rule | Impossible in real data | `high < low`, price ≤ 0 | Move the row to quarantine, log `WARNING` |
| Dataset-level | The whole response is broken | missing `close` column, too many invalid rows | Stop the run, log `ERROR` |

