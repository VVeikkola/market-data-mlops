import logging
import sys
import time
from datetime import date, datetime, timedelta, timezone

import requests

from config import PROJECT_ROOT, load_config
from logging_setup import setup_logging

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "coinbase"
BASE_URL = "https://api.exchange.coinbase.com/products"
GRANULARITY_SECONDS = 60 * 60 * 24  # 1 day in seconds
MAX_CANDLES_PER_REQUEST = 300
PAUSE_BETWEEN_REQUESTS = 0.5
TIMEOUT_SECONDS = 10

logger = logging.getLogger(__name__)

def fetch_product(product_id: str, start_date: date, end_date: date) -> int:
    """Fetch daily candles for one product in 300-day chunks. Return the total row count."""
    url = f"{BASE_URL}/{product_id}/candles"

    # One directory per fetch, one file per API response
    fetched_at = datetime.now(timezone.utc)
    run_dir = RAW_DIR / product_id / f"{fetched_at:%Y%m%dT%H%M%SZ}"
    run_dir.mkdir(parents=True, exist_ok=False)

    chunk_start = start_date
    total_rows = 0

    while chunk_start <= end_date:
        # start and end are both inclusive, so 300 candles = start + 299 days
        max_chunk_end = chunk_start + timedelta(days=MAX_CANDLES_PER_REQUEST - 1)
        chunk_end = min(max_chunk_end, end_date)

        params = {
            "granularity": GRANULARITY_SECONDS,
            "start": f"{chunk_start.isoformat()}T00:00:00Z",
            "end": f"{chunk_end.isoformat()}T00:00:00Z",
        }

        response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()

        output_path = run_dir / f"{chunk_start.isoformat()}_to_{chunk_end.isoformat()}.json"
        with output_path.open("x", encoding="utf-8") as f:
            f.write(response.text)

        rows = response.json()
        total_rows += len(rows)
        logger.info("%s: fetched %d rows for %s to %s", product_id, len(rows), chunk_start, chunk_end)

        chunk_start = chunk_end + timedelta(days=1)
        time.sleep(PAUSE_BETWEEN_REQUESTS)

    # Mark the run as complete. Readers must ignore run directories without this file.
    (run_dir / "_SUCCESS").touch()
    logger.info( "%s: saved %d rows to %s", product_id, total_rows, run_dir.relative_to(PROJECT_ROOT))
    return total_rows


def main() -> int:
    """Fetch every configured Coinbase product. Return the process exit code."""
    setup_logging()

    config = load_config()
    logger.info(
        "Fetching %d Coinbase product(s) from %s to %s",
        len(config.coinbase_products),
        config.start_date,
        config.end_date,
    )

    for product_id in config.coinbase_products:
        try:
            fetch_product(product_id, config.start_date, config.end_date)
        except requests.exceptions.HTTPError as e:
            logger.error("%s: %s", product_id, e)
            logger.error("%s: response body: %s", product_id, e.response.text)
            return 1
        except requests.exceptions.RequestException as e:
            logger.error("%s: request failed: %s", product_id, e)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())