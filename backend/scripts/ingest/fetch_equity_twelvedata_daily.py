import argparse
from dataclasses import asdict
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.market_data import (
    RawEquitySeriesRequest,
    archive_twelvedata_equity_daily_raw,
)
from app.services.twelvedata_client import TwelveDataClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive raw daily equity price history from Twelve Data."
    )
    parser.add_argument("--symbol", required=True, help="Provider symbol, for example MSTR")
    parser.add_argument("--asset-symbol", required=True, help="Canonical asset symbol, for example MSTR")
    parser.add_argument("--quote-currency", default="USD")
    parser.add_argument("--import-type", default="full_backfill", choices=["full_backfill", "refresh"])
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = TwelveDataClient(api_key=settings.twelvedata_api_key)
    try:
        summary = archive_twelvedata_equity_daily_raw(
            RawEquitySeriesRequest(
                symbol=args.symbol,
                asset_symbol=args.asset_symbol,
                quote_currency=args.quote_currency,
                interval="day",
                import_type=args.import_type,
                dry_run=args.dry_run,
            ),
            client=client,
        )
    finally:
        client.close()
    pprint(asdict(summary))


if __name__ == "__main__":
    main()
