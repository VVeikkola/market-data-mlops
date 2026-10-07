import os
import sys

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# read the Tiingo API key from environment variables
api_key = os.getenv("TIINGO_API_KEY")

if not api_key:
    sys.exit("TIINGO_API_KEY not found in environment variables. Copy .env.example to .env and add your key")

url = "https://api.tiingo.com/tiingo/daily/NVDA/prices"

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
if response.status_code == 200:
    rows = response.json()
    print(f"Received rows: {len(rows)}")
else:
    print(f"Error: {response.status_code}", file=sys.stderr)
    print(response.text, file=sys.stderr)
    sys.exit(1)