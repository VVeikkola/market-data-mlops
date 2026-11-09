import logging
import sys 

import pandas as pd

from config import PROJECT_ROOT, load_config
from load_raw import load_all_raw
from logging_setup import setup_logging
from validate import validate_prices

logger = logging.getLogger(__name__)

CLEAN_COLUMNS = ["symbol", "date", "price", "suspicious_return"]
CLEAN_FILE = PROJECT_ROOT / "data" / "clean" / "prices.parquet"

def transform_prices(valid: pd.DataFrame) -> pd.DataFrame:
    """Turn validated rows into clean dataset: one price per symbol and day"""
    clean = valid.rename(columns={"adj_close": "price"})
    clean["date"] = clean["date"].dt.date  # a date has no time and no timezone
    clean = clean.sort_values(["symbol", "date"], ignore_index=True)
    return clean[CLEAN_COLUMNS]

def save_clean(clean: pd.DataFrame) -> None:
    """Write the clean dataset to Parquet, replacing the previous version"""
    CLEAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean.to_parquet(CLEAN_FILE, index=False)


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
    save_clean(clean)
    logger.info("Saved %d clean rows to %s", len(clean), CLEAN_FILE.relative_to(PROJECT_ROOT))