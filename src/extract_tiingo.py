import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "tiingo"

# Load environment variables from .env file
load_dotenv()

# read the Tiingo API key from environment variables
api_key = os.getenv("TIINGO_API_KEY")

if not api_key:
    sys.exit("TIINGO_API_KEY not found in environment variables. Copy .env.example to .env and add your key")

symbol = "NVDA"
url = f"https://api.tiingo.com/tiingo/daily/{symbol}/prices"

headers = {
    "Authorization": "Token " + api_key
}

params = {
    "startDate": "2024-06-05",
    "endDate": "2024-06-12",
}

timeout = 10

# send the request to the Tiingo API
try:
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=timeout,
    )
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}", file=sys.stderr)
    sys.exit(1)

# Check if the request was successful
if response.status_code != 200:
    print(f"Error: {response.status_code}", file=sys.stderr)
    print(response.text, file=sys.stderr)
    sys.exit(1)

# Save the raw response exactly as received, one file per fetch
fetched_at = datetime.now(timezone.utc)
output_dir = RAW_DIR / symbol
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / f"{fetched_at:%Y%m%dT%H%M%SZ}.json"
with output_path.open("x", encoding="utf-8") as f:
    f.write(response.text)

rows = response.json()
print(f"Received rows: {len(rows)}")
print(f"Saved raw response to: {output_path.relative_to(PROJECT_ROOT)}")
