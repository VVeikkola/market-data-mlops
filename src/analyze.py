import argparse
import logging

import pandas as pd

from logging_setup import setup_logging
from transform import CLEAN_FILE

logger = logging.getLogger(__name__)

MIN_INDEPENDENT_PERIODS = 10 # Require at least 10 independent periods to reduce misleading results caused by random luck. This is a heuristic, not a statistical guarantee.

def load_prices(symbol: str) -> pd.DataFrame:
    """Read one symbol's prices from the clean dataset. OLDEST FIRST"""
    df = pd.read_parquet(CLEAN_FILE, columns=["symbol", "date", "price"])
    df = df[df["symbol"] == symbol]
    if df.empty:
        raise ValueError(f"No prices found for symbol {symbol!r} in {CLEAN_FILE}")
    # Date math needs a datetime column. A fixed precision lets two date columns be matched later.
    df["date"] = pd.to_datetime(df["date"].astype("datetime64[us]"))
    return df[["date", "price"]].sort_values("date", ignore_index=True)

def holding_period_returns(prices: pd.DataFrame, days: int) -> pd.DataFrame:
    """One row per possible buy day: the return after holding for 'days' calendar days"""
    windows = prices.rename(columns={"date": "start_date", "price": "start_price"})
    windows["end_date"] = windows["start_date"] + pd.Timedelta(days=days)
    windows = windows[windows["end_date"] <= prices["date"].max()] # drop windows that go past the last price

    # As-of: if the end date has no price (weekend, holiday), use the last price before it
    windows = pd.merge_asof(
        windows,
        prices.rename(columns={"price": "end_price"}),
        left_on="end_date",
        right_on="date",
        direction="backward",
    )
    windows["return"] = windows["end_price"] / windows["start_price"] - 1
    return windows[["start_date", "end_date", "start_price", "end_price", "return"]]

def summarize(windows: pd.DataFrame, days: int) -> dict[str, float]:
    """Describe the distribution of returns over all windows."""
    returns = windows["return"]
    data_days = (windows["end_date"].max() - windows["start_date"].min()).days
    return {
        "windows": len(returns),
        "independent_periods": data_days // days,
        "mean": returns.mean(),
        "median": returns.median(),
        "best": returns.max(),
        "worst": returns.min(),
        "share_positive": (returns > 0).mean(),
    }

def parse_args() -> argparse.Namespace:
    """Read symbol and holding days from the command line"""
    parser = argparse.ArgumentParser(description="Analyze holding period returns for a symbol.")
    parser.add_argument("symbol", help="symbol in the clean dataset (e.g., BTC-USD)")
    parser.add_argument("days", type=int, help="number of calendar days to hold (e.g. 30)")
    args = parser.parse_args()

    if args.days < 1:
        parser.error(f"Days must be a positive integer, got {args.days}")
    return args


if __name__ == "__main__":
    setup_logging()
    args = parse_args()

    windows = holding_period_returns(load_prices(args.symbol), args.days)
    summary = summarize(windows, args.days)

    print(f"{args.symbol}, held {args.days} days:")
    for name, value in summary.items():
        text = f"{value:.1%}" if isinstance(value, float) else value
        print(f"  {name:<20}: {text}")

    if summary["independent_periods"] < MIN_INDEPENDENT_PERIODS:
        logger.warning(
            "Only %d independent periods: treat these numbers with caution",
            summary["independent_periods"],
        )
