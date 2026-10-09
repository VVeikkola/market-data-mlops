import pandas as pd

PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close"]

def hard_rule_violations(df: pd.DataFrame) -> dict[str, pd.Series]:
    """# Return one boolean mask per hard rule. True = row breaks the rule, False = row is valid."""
    now_utc = pd.Timestamp.now(tz="UTC").tz_localize(None)
    return{
        "high_below_open_or_close": df["high"] < df[["open", "close"]].max(axis=1),
        "low_above_open_or_close": df["low"] > df[["open", "close"]].min(axis=1),
        "high_below_low": df["high"] < df["low"],
        "non_positive_price": df[PRICE_COLUMNS].le(0).any(axis=1),
        "negative_volume": df["volume"] < 0,
        "missing_date": df["date"].isna(),
        "future_date": df["date"] > now_utc,
        "duplicate_date_symbol": df.duplicated(subset=["date", "symbol"], keep=False),
    }

def count_violations(violations: dict[str, pd.Series]) -> pd.Series:
    """Count how many rows break each rule."""
    return pd.Series({rule: int(mask.sum()) for rule, mask in violations.items()})

def missing_calendar_days(dates: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    """Return a DatetimeIndex of missing days in the data."""
    all_days = pd.date_range(start=start, end=end)
    return all_days[~all_days.isin(dates)]