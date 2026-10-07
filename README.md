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

Hard rules (per row):

- `high ≥ open`, `high ≥ close`, `high ≥ low`
- `low ≤ open`, `low ≤ close`
- all prices > 0, `volume ≥ 0`
- date is present, not in the future, and unique per asset (no duplicates)

Thresholds (e.g. the 50 % daily return limit and the maximum share of invalid rows) are configurable. A soft-rule threshold that suits Bitcoin may be too loose for a stable index fund.

## Time handling

- Dates in the clean dataset are stored as `YYYY-MM-DD`, not as timestamps. Daily data has no time of day, and converting a date to midnight UTC and back in another timezone can silently shift it to the previous day.
- The meaning of a "day" differs by asset:
  - **Bitcoin:** a UTC calendar day (00:00–24:00 UTC). Crypto trades 24/7, so the daily close is a convention chosen by the data provider.
  - **NVIDIA:** a New York Stock Exchange trading day.
- **Only completed days are stored.** The current day's row is still changing (its close is just the latest price so far), so it is skipped. Completeness is checked in UTC.
- Holding periods are measured in **calendar days**, so a 30-day period means the same amount of time for both assets. If the end date falls on a day without trading (e.g. a weekend for NVIDIA), the last available price before it is used (as-of).

## Out of scope for v1

| Not in v1 | Reason |
|---|---|
| Machine learning | A reliable data pipeline comes first |
| Buy/sell recommendations | The project analyses history; it does not give investment advice |
| Intraday or real-time data | Daily data is enough for the question being asked |
| Scheduling / orchestration (Airflow) | The pipeline is first built and run as a plain Python program |
| Database (PostgreSQL), Docker | Added when there is a concrete need for them |

## Roadmap

1. **Market data fundamentals:** API → raw data → validation → transformation → storage → analysis *(current)*
2. **Data Engineering:** incremental loading, Parquet / PostgreSQL, tests, logging
3. **Orchestration:** Docker, Airflow, scheduling, retries, backfills
4. **Analytics & feature engineering:** returns, volatility, drawdown, momentum
5. **Machine learning:** baseline, time-series validation, experiment comparison
6. **MLOps:** MLflow, model registry, CI/CD, monitoring

## Development environment

The project is developed **Linux-first** (WSL2 on Windows) and is intended to run natively on any Linux machine after cloning. Configuration and secrets are provided through environment variables.

## Disclaimer

This project is for learning purposes only and does not constitute investment advice.
