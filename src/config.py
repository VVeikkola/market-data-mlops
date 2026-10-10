import tomllib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

# Project root = the parent of the src/ directory this file lives in
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.toml"


@dataclass(frozen=True)
class Config:
    """Pipeline settings loaded from config.toml."""

    start_date: date
    end_date: date
    tiingo_symbols: list[str]
    coinbase_products: list[str]
    max_abs_daily_return: float

def _validate_symbols(values: object, field: str) -> None:
    """Raise ValueError unless values is a non-empty list of non-empty strings."""
    if not isinstance(values, list) or not values:
        raise ValueError(f'{field} must be a non-empty list like ["NVDA"]')
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} contains an invalid entry: {value!r}")


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Read config.toml, validate it and return it as a Config object."""
    with path.open("rb") as f:
        raw = tomllib.load(f)

    config = Config(
        start_date=raw["date_range"]["start_date"],
        end_date=raw["date_range"]["end_date"],
        tiingo_symbols=raw["tiingo"]["symbols"],
        coinbase_products=raw["coinbase"]["products"],
        max_abs_daily_return=raw["validation"]["max_abs_daily_return"],
    )

    if not isinstance(config.start_date, date) or not isinstance(config.end_date, date):
        raise ValueError("start_date and end_date must be dates like 2024-01-01 (no quotes)")
    if config.start_date > config.end_date:
        raise ValueError(f"start_date {config.start_date} is after end_date {config.end_date}")

    today_utc = datetime.now(timezone.utc).date()
    if config.end_date >= today_utc:
        raise ValueError(
            f"end_date {config.end_date} must be before today ({today_utc} UTC): "
            "only completed days are fetched"
        )

    _validate_symbols(config.tiingo_symbols, "tiingo.symbols")
    _validate_symbols(config.coinbase_products, "coinbase.products")

    if not isinstance(config.max_abs_daily_return, (int, float)) or config.max_abs_daily_return <= 0:
        raise ValueError("max_abs_daily_return must be a positive number like 0.5")

    return config


if __name__ == "__main__":
    print(load_config())