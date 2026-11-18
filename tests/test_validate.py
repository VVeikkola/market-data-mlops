from datetime import date

import pandas as pd

from config import Config
from validate import (
    flag_suspicious_returns,
    hard_rule_violations,
    missing_calendar_days,
    split_by_hard_rules,
    validate_prices,
)

def make_row(**overrides) -> pd.DataFrame:
    """One valid price row as a table. Pass a column name to change its value"""
    row = {
        "symbol": "test",
        "date": pd.Timestamp("2024-01-02"),
        "open": 100.0,
        "high": 110.0,
        "low": 90.0,
        "close": 100.0,
        "adj_close": 100.0,
        "volume": 1000,
    }
    row.update(overrides)
    return pd.DataFrame([row])

def make_config(**overrides) -> Config:
    """A small valid Config for tests. Pass a field name to change its value."""
    values = {
        "start_date": date(2024, 1, 2),
        "end_date": date(2024, 1, 4),
        "tiingo_symbols": ["NVDA"],
        "coinbase_products": ["BTC-USD"],
        "max_abs_daily_return": 0.5,
        "max_invalid_share": 0.05,
    }
    values.update(overrides)
    return Config(**values)

def test_valid_row_breaks_no_rule():
    df = make_row()
    violations = hard_rule_violations(df)

    for rule, mask in violations.items():
        assert not mask.any(), f"Rule {rule} should not be violated"

def test_negative_volume_is_flagged():
    df = make_row(volume=-1)
    violations = hard_rule_violations(df)

    assert violations["negative_volume"].all()

def test_high_below_low_is_flagged():
    df = make_row(high=90, low=100)
    violations = hard_rule_violations(df)

    assert violations["high_below_low"].all()

def test_high_below_open_is_flagged():
    df = make_row(high=95)
    violations = hard_rule_violations(df)

    assert violations["high_below_open_or_close"].all()
    assert not violations["high_below_low"].any()

def test_low_above_open_is_flagged():
    df = make_row(low=105)
    violations = hard_rule_violations(df)

    assert violations["low_above_open_or_close"].all()
    assert not violations["high_below_low"].any()

def test_non_positive_price_is_flagged():
    df = make_row(adj_close=0)
    violations = hard_rule_violations(df)

    assert violations["non_positive_price"].all()
    assert not violations["low_above_open_or_close"].any()

def test_missing_date_is_flagged():
    df = make_row(date=pd.NaT)
    violations = hard_rule_violations(df)

    assert violations["missing_date"].all()
    assert not violations["future_date"].any()

def test_future_date_is_flagged():
    df = make_row(date=pd.Timestamp.now() + pd.Timedelta(days=1))
    violations = hard_rule_violations(df)

    assert violations["future_date"].all()
    assert not violations["missing_date"].any()

def test_duplicate_date_symbol_is_flagged():
    df = pd.concat([make_row(), make_row()], ignore_index=True)
    violations = hard_rule_violations(df)

    assert violations["duplicate_date_symbol"].all()

def test_row_breaking_two_rules_gets_both_names():

    good = make_row()
    bad = make_row(open=0, date=pd.Timestamp("2024-01-03"))
    df = pd.concat([good, bad], ignore_index=True)

    valid, quarantined = split_by_hard_rules(df)
    failed = quarantined["failed_rules"].iloc[0]

    assert len(valid) == 1
    assert len(quarantined) == 1
    assert "non_positive_price" in failed
    assert "low_above_open_or_close" in failed

def test_suspicious_return_flags_only_big_jump():
    df = pd.concat(
        [
            make_row(date=pd.Timestamp("2024-01-02"), adj_close=100.0),
            make_row(date=pd.Timestamp("2024-01-03"), adj_close=110.0),
            make_row(date=pd.Timestamp("2024-01-04"), adj_close=176.0),
        ],
        ignore_index=True,
    )

    result = flag_suspicious_returns(df, 0.5)

    assert result["suspicious_return"].tolist() == [False, False, True]
    
def test_missing_calendar_days_finds_the_gap():
    dates = pd.Series([pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-04")])

    missing = missing_calendar_days(dates, pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-04"))

    assert missing.tolist() == [pd.Timestamp("2024-01-03")]

def test_empty_dataset_is_an_error():
    df = make_row().iloc[0:0]

    result = validate_prices(df, make_config())

    assert result.errors == ["Dataset is empty"]

def test_too_many_invalid_rows_is_an_error():
    good = make_row(source="tiingo")
    bad = make_row(source="tiingo", volume=-1, date=pd.Timestamp("2024-01-03"))
    df = pd.concat([good, bad], ignore_index=True)

    result = validate_prices(df, make_config(max_invalid_share=0.05))

    assert len(result.quarantined) == 1
    assert len(result.errors) == 1
    assert "broke hard rules" in result.errors[0]

def test_missing_crypto_day_is_an_error():
    df = pd.concat(
        [
            make_row(source="coinbase", symbol="BTC-USD", date=pd.Timestamp("2024-01-02")),
            make_row(source="coinbase", symbol="BTC-USD", date=pd.Timestamp("2024-01-04")),
        ],
        ignore_index=True,
    )

    result = validate_prices(df, make_config())

    assert result.errors == ["BTC-USD: 1 missing calendar day(s), first: 2024-01-03"]
