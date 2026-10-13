import logging
import os
import sys
from datetime import date, datetime, timezone

import requests
from dotenv import load_dotenv

from config import PROJECT_ROOT, load_config
from logging_setup import setup_logging

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "tiingo"
BASE_URL = "https://api.tiingo.com/tiingo/daily"
TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)

def fetch_symbol(symbol: str, start_date: date, end_date: date, api_key: str) -> int:
    """Fetch daily prices for one symbol, save the raw response and return the row count."""
    url = f"{BASE_URL}/{symbol}/prices"
    headers = {"Authorization": "Token " + api_key}
    params = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
    }

    response = requests.get(url, headers=headers, params=params, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()

    # Save the raw response exactly as received, one file per fetch
    fetched_at = datetime.now(timezone.utc)
    output_dir = RAW_DIR / symbol
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{fetched_at:%Y%m%dT%H%M%SZ}.json"
    with output_path.open("x", encoding="utf-8") as f:
        f.write(response.text)

    rows = response.json()
    logger.info( "%s: saved %d rows to %s", symbol, len(rows), output_path.relative_to(PROJECT_ROOT))
    return len(rows)


def main() -> int:
    """Fetch every configured Tiingo symbol. Return the process exit code."""
    setup_logging()

    load_dotenv()
    api_key = os.getenv("TIINGO_API_KEY")
    if not api_key:
        logger.error(
            "TIINGO_API_KEY not found in environment variables. "
            "Copy .env.example to .env and add your key"
        )
        return 1

    config = load_config()
    logger.info(
        "Fetching %d Tiingo symbol(s) from %s to %s",
        len(config.tiingo_symbols),
        config.start_date,
        config.end_date,
    )

    for symbol in config.tiingo_symbols:
        try:
            fetch_symbol(symbol, config.start_date, config.end_date, api_key)
        except requests.exceptions.HTTPError as e:
            logger.error("%s: %s", symbol, e)
            logger.error("%s: response body: %s", symbol, e.response.text)
            return 1
        except requests.exceptions.RequestException as e:
            logger.error("%s: request failed: %s", symbol, e)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())