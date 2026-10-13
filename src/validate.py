from dataclasses import dataclass

import pandas as pd

from config import Config

PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close"]


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of validating one dataset."""

    valid: pd.DataFrame
    quarantined: pd.DataFrame
    errors: list[str]

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

def split_by_hard_rules(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split rows into (valid, quarantined). Quarantined rows get a failed_rules column."""
    failed_rules = pd.Series("", index=df.index)
    for rule, mask in hard_rule_violations(df).items():
        failed_rules[mask] = failed_rules[mask] + rule + ","
    failed_rules = failed_rules.str.rstrip(",")

    is_invalid = failed_rules != ""
    quarantined = df[is_invalid].copy()
    quarantined["failed_rules"] = failed_rules[is_invalid]
    return df[~is_invalid].copy(), quarantined


def flag_suspicious_returns(df: pd.DataFrame, max_abs_daily_return: float) -> pd.DataFrame:
    """Add a suspicious_return column: True where the daily return exceeds the soft limit."""
    df = df.sort_values(["symbol", "date"], ignore_index=True)
    daily_return = df.groupby("symbol")["adj_close"].pct_change()
    df["suspicious_return"] = daily_return.abs() > max_abs_daily_return
    return df


def validate_prices(df: pd.DataFrame, config: Config) -> ValidationResult:
    """Run every validation level: hard rules, soft rule and dataset-level checks."""
    if df.empty:
        return ValidationResult(
            valid=df.assign(suspicious_return=False),
            quarantined=df.assign(failed_rules=""),
            errors=["Dataset is empty"],
        )

    errors: list[str] = []

    valid, quarantined = split_by_hard_rules(df)
    valid = flag_suspicious_returns(valid, config.max_abs_daily_return)

    invalid_share = len(quarantined) / len(df)
    if invalid_share > config.max_invalid_share:
        errors.append(
            f"{invalid_share:.1%} of rows broke hard rules (limit {config.max_invalid_share:.1%})"
        )

    # Crypto trades every day, so every calendar day in the requested range must be present
    crypto = valid[valid["source"] == "coinbase"]
    for symbol, rows in crypto.groupby("symbol"):
        missing = missing_calendar_days(
            rows["date"], pd.Timestamp(config.start_date), pd.Timestamp(config.end_date)
        )
        if len(missing) > 0:
            first_days = ", ".join(str(day.date()) for day in missing[:5])
            errors.append(f"{symbol}: {len(missing)} missing calendar day(s), first: {first_days}")

    return ValidationResult(valid=valid, quarantined=quarantined, errors=errors)