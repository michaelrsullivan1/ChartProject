import argparse
from dataclasses import asdict
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.market_data import RawFredSeriesRequest, archive_fred_btc_daily_raw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive raw BTC/USD daily history from the FRED CBBTCUSD series."
    )
    parser.add_argument("--series-id", default="CBBTCUSD")
    parser.add_argument("--asset-symbol", default="BTC")
    parser.add_argument("--quote-currency", default="USD")
    parser.add_argument("--import-type", default="full_backfill", choices=["full_backfill", "refresh"])
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = archive_fred_btc_daily_raw(
        RawFredSeriesRequest(
            series_id=args.series_id,
            asset_symbol=args.asset_symbol,
            quote_currency=args.quote_currency,
            interval="day",
            import_type=args.import_type,
            dry_run=args.dry_run,
        )
    )
    pprint(asdict(summary))


if __name__ == "__main__":
    main()
