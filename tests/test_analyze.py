import pandas as pd
import pytest

from analyze import holding_period_returns, summarize

def make_prices(prices: list[float])-> pd.DataFrame:
    """Small fake price table: one price per day starting 2024-01-01."""
    dates = pd.date_range("2024-01-01", periods=len(prices), freq="D", unit="us")
    return pd.DataFrame({"date": dates, "price": prices})

def test_one_day_returns():
    prices = make_prices([100, 110, 90])
    windows = holding_period_returns(prices, days=1)

    assert len(windows) == 2  # the last day has no "next day", so no window
    assert windows["return"].iloc[0] == pytest.approx(0.10)
    assert windows["return"].iloc[1] == pytest.approx(-0.18181818)

def test_too_long_holding_period_raises():
    prices = make_prices([100, 110, 90]) #covers 2 days
    with pytest.raises(ValueError, match="Cannot hold 3 days"):
        holding_period_returns(prices, days=3)

def test_summarize_two_day_windows():
    prices = make_prices([100, 110, 90, 120, 100]) #Covers 4 days
    windows = holding_period_returns(prices, days=2)

    summary = summarize(windows, days=2)

    assert summary["windows"] == 3
    assert summary["independent_periods"] == 2
    assert summary["share_positive"] == pytest.approx(2 / 3)
    assert summary["best"] == pytest.approx(100 / 90 - 1)
    assert summary["worst"] == pytest.approx(90 / 100 - 1)