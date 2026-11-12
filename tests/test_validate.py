import pandas as pd

from validate import hard_rule_violations

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