import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "coinbase"

BASE_URL = "https://api.exchange.coinbase.com/products"
GRANULARITY_SECONDS = 60 * 60 * 24  # 1 day in seconds
MAX_CANDLES_PER_REQUEST = 300
PAUSE_BETWEEN_REQUESTS = 0.5

product_id = "BTC-USD"
start_date = date(2024, 1, 1)
end_date = date(2025, 12, 31)
timeout = 10

url = f"{BASE_URL}/{product_id}/candles"

#One directory per fetch, one file per API response
fetched_at = datetime.now(timezone.utc)
run_dir = RAW_DIR / product_id / f"{fetched_at:%Y%m%dT%H%M%SZ}"
run_dir.mkdir(parents=True, exist_ok=False)

chunk_start = start_date
total_rows = 0

while chunk_start <= end_date:
    # start and end are both inclusive, so 300 candles = start + 299 days
    chunk_end = min(chunk_start + timedelta(days=MAX_CANDLES_PER_REQUEST - 1), end_date)

    params = {
        "granularity": GRANULARITY_SECONDS,
        "start": f"{chunk_start.isoformat()}T00:00:00Z",
        "end": f"{chunk_end.isoformat()}T00:00:00Z",
    }

    try:
        response = requests.get(url, params=params, timeout=timeout)
    except requests.exceptions.RequestException as e:
        print(f"Request failed for {chunk_start} to {chunk_end}: {e}", file=sys.stderr)
        sys.exit(1)

    if response.status_code != 200:
        print(f"Error: {response.status_code} for {chunk_start} to {chunk_end}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        sys.exit(1)

    output_path = run_dir / f"{chunk_start.isoformat()}_to_{chunk_end.isoformat()}.json"
    with output_path.open("x", encoding="utf-8") as f:
        f.write(response.text)

    rows = response.json()
    total_rows += len(rows)
    print(f"Fetched {len(rows)} rows for {chunk_start} to {chunk_end}")

    chunk_start = chunk_end + timedelta(days=1)
    time.sleep(PAUSE_BETWEEN_REQUESTS)

# Mark the run as complete. Readers must ignore run directories without this file.
(run_dir / "_SUCCESS").touch()

print(f"Total rows: {total_rows}")
print(f"Saved raw responses to: {run_dir.relative_to(PROJECT_ROOT)}")