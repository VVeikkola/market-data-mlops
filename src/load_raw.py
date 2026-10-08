import json
from pathlib import Path

import pandas as pd

#Project root is the parent of the src directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

##Common schema: every source is converted to these columns in this order
COLUMNS = [
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "adj_volume",
    "source",
    "raw_file"
]

#Coinbase candles are listed without field names in this order
COINBASE_FIELDS = [
    "time",
    "low",
    "high",
    "open",
    "close",
    "volume"
]

def latest_tiingo_file(symbol: str) -> Path:
    """Return the latest Tiingo raw file for a symbol"""
    files = sorted((RAW_DIR / "tiingo" / symbol).glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No Tiingo files found for symbol {symbol}")
    return files[-1]

def latest_coinbase_run(product_id: str) -> Path:
    """Return the newest complete (_SUCCESS) Coinbase run directory"""
    runs = sorted(
        run_dir
        for run_dir in (RAW_DIR / "coinbase" / product_id).iterdir()
        if (run_dir / "_SUCCESS").exists()
    )
    if not runs:
        raise FileNotFoundError(f"No complete Coinbase runs found for product {product_id}")
    return runs[-1]

def load_tiingo(path: Path, symbol: str) -> pd.DataFrame:
    """Read one raw Tiingo file into common schema."""
    records = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame.from_records(records)

    #Tiingo writes trading date as "2024-06-05T00:00:00.000Z". Keep only date apart because of timezone issues
    df["date"] = pd.to_datetime(df["date"].str[0:10], format="%Y-%m-%d")
    df = df.rename(columns={
        "adjClose": "adj_close",
        "adjVolume": "adj_volume"
    })
    df["symbol"] = symbol
    df["source"] = "tiingo"
    df["raw_file"] = str(path.relative_to(PROJECT_ROOT))
    return df[COLUMNS]

def load_coinbase(run_dir: Path, product_id: str) -> pd.DataFrame:
    """Read alll pages of one Coinbase run into common schema."""
    frames = []
    for path in sorted(run_dir.glob("*.json")):
        candles = json.loads(path.read_text(encoding="utf-8"))
        page = pd.DataFrame.from_records(candles, columns=COINBASE_FIELDS)
        page["raw_file"] = str(path.relative_to(PROJECT_ROOT))
        frames.append(page)
    df = pd.concat(frames, ignore_index=True)

    #Unix time is UTC and daily candles start at 00:00:00 UTC.
    df["date"] = pd.to_datetime(df["time"], unit="s")
    df["adj_close"] = df["close"]  # Crypto has no splits or dividends, so adjusted close is the same as close
    df["adj_volume"] = df["volume"]  # Crypto has no splits, so adjusted volume is the same as volume
    df["symbol"] = product_id
    df["source"] = "coinbase"
    return df[COLUMNS]

if __name__ == "__main__":
    nvda = load_tiingo(latest_tiingo_file("NVDA"), "NVDA")
    btc = load_coinbase(latest_coinbase_run("BTC-USD"), "BTC-USD")
    df = pd.concat([nvda, btc], ignore_index=True)

    print(df.dtypes)
    print()
    print(df.head(8).to_string())
    print()
    print(df.groupby("symbol").size())
