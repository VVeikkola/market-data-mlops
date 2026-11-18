from datetime import date, datetime, timezone

import pytest

from config import load_config

GOOD_CONFIG = """
[date_range]
start_date = 2024-01-01
end_date = 2024-12-31

[tiingo]
symbols = ["NVDA"]

[coinbase]
products = ["BTC-USD"]

[validation]
max_abs_daily_return = 0.5
max_invalid_share = 0.05
"""


def write_config(tmp_path, text):
    """Write config text to a temporary file and return its path."""
    path = tmp_path / "config.toml"
    path.write_text(text)
    return path


def test_good_config_loads(tmp_path):
    path = write_config(tmp_path, GOOD_CONFIG)

    config = load_config(path)

    assert config.start_date == date(2024, 1, 1)
    assert config.tiingo_symbols == ["NVDA"]
    assert config.max_invalid_share == 0.05


def test_start_after_end_fails(tmp_path):
    text = GOOD_CONFIG.replace("start_date = 2024-01-01", "start_date = 2025-01-01")
    path = write_config(tmp_path, text)

    with pytest.raises(ValueError, match="is after end_date"):
        load_config(path)


def test_end_date_today_fails(tmp_path):
    today = datetime.now(timezone.utc).date()
    text = GOOD_CONFIG.replace("end_date = 2024-12-31", f"end_date = {today}")
    path = write_config(tmp_path, text)

    with pytest.raises(ValueError, match="must be before today"):
        load_config(path)
