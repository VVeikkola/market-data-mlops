import logging
import sys 

import pandas as pd

from config import load_config
from load_raw import load_all_raw
from logging_setup import setup_logging
from validate import validate_prices

logger = logging.getLogger(__name__)

CLEAN_COLUMNS = ["symbol", "date", "price", "suspicious_return"]

def transform_prices(valid: pd.DataFrame) -> pd.DataFrame:
    """Turn validated rows into clean dataset: one price per symbol and day"""
    clean = valid.rename(columns={"adj_close": "price"})
    clean["date"] = clean["date"].dt.date  # a date has no time and no timezone
    clean = clean.sort_values(["symbol", "date"], ignore_index=True)
    return clean[CLEAN_COLUMNS]


if __name__ == "__main__":
    setup_logging()
    config = load_config()
    result = validate_prices(load_all_raw(config), config)

    if result.errors:
        for error in result.errors:
            logger.error("%s", error)
        sys.exit(1)

    clean = transform_prices(result.valid)
    print(clean[clean["symbol"] == "NVDA"].head(10).to_string())
    print()
    print(clean.groupby("symbol").size())
