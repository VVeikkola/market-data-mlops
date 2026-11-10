import pandas as pd
import pytest

from analyze import holding_period_returns

def make_prices(prices: list[float])-> pd.DataFrame:
    """Small fake price table: one price per day starting 2024-01-01."""
    dates = pd.date_range("2024-01-01", periods=len(prices), freq="D", unit="us")
    return pd.DataFrame({"date": dates, "price": prices})

def test_one_day_returns():
    prices = make_prices([100, 110, 90])
    windows = holding_period_returns(prices, days=1)

    assert len(windows) == 2  # the last day has no "next day", so no window
    assert windows["return"].iloc[0] == pytest.approx(0.10)
    