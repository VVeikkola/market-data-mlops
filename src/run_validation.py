import logging
import sys
from datetime import datetime, timezone

from config import PROJECT_ROOT, load_config
from load_raw import load_all_raw
from logging_setup import setup_logging
from validate import validate_prices

QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"

logger = logging.getLogger(__name__)


def main() -> int:
    """Validate the latest raw data. Return the process exit code."""
    setup_logging()
    config = load_config()

    try:
        df = load_all_raw(config)
    except (FileNotFoundError, KeyError, ValueError) as e:
        logger.error("Could not load raw data: %s", e)
        return 1

    result = validate_prices(df, config)
    logger.info(
        "Checked %d rows: %d valid, %d quarantined",
        len(df),
        len(result.valid),
        len(result.quarantined),
    )

    if not result.quarantined.empty:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        path = QUARANTINE_DIR / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.csv"
        result.quarantined.to_csv(path, index=False, mode="x")
        logger.warning(
            "%d row(s) broke hard rules, saved to %s",
            len(result.quarantined),
            path.relative_to(PROJECT_ROOT),
        )

    suspicious = result.valid[result.valid["suspicious_return"]]
    for row in suspicious.itertuples():
        logger.warning("%s %s: daily return exceeds the soft limit", row.symbol, row.date.date())

    for error in result.errors:
        logger.error("%s", error)

    if result.errors:
        return 1

    logger.info("Validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())