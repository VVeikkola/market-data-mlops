import sys
import time
from datetime import date, datetime, timedelta, timezone

import requests

from config import PROJECT_ROOT, load_config

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "coinbase"
BASE_URL = "https://api.exchange.coinbase.com/products"
GRANULARITY_SECONDS = 60 * 60 * 24  # 1 day in seconds
MAX_CANDLES_PER_REQUEST = 300
PAUSE_BETWEEN_REQUESTS = 0.5
TIMEOUT_SECONDS = 10


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
        print(f"{product_id}: fetched {len(rows)} rows for {chunk_start} to {chunk_end}")

        chunk_start = chunk_end + timedelta(days=1)
        time.sleep(PAUSE_BETWEEN_REQUESTS)

    # Mark the run as complete. Readers must ignore run directories without this file.
    (run_dir / "_SUCCESS").touch()
    print(f"{product_id}: saved {total_rows} rows to {run_dir.relative_to(PROJECT_ROOT)}")
    return total_rows


def main() -> int:
    """Fetch every configured Coinbase product. Return the process exit code."""
    config = load_config()

    for product_id in config.coinbase_products:
        try:
            fetch_product(product_id, config.start_date, config.end_date)
        except requests.exceptions.HTTPError as e:
            print(f"{product_id}: {e}", file=sys.stderr)
            print(e.response.text, file=sys.stderr)
            return 1
        except requests.exceptions.RequestException as e:
            print(f"{product_id}: request failed: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())