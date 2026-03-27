import argparse
from dataclasses import asdict
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.market_data import RawMarketChartRangeRequest, archive_btc_market_chart_range_raw
from scripts.ingest._common import parse_utc_timestamp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive raw BTC/USD market chart range data from CoinGecko."
    )
    parser.add_argument("--since", required=True, help="UTC start timestamp, for example 2012-01-01T00:00:00Z")
    parser.add_argument("--until", required=True, help="UTC end timestamp, for example 2026-03-27T00:00:00Z")
    parser.add_argument("--asset-symbol", default="BTC")
    parser.add_argument("--quote-currency", default="USD")
    parser.add_argument("--source-asset-id", default="bitcoin")
    parser.add_argument("--import-type", default="full_backfill", choices=["full_backfill", "refresh"])
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = archive_btc_market_chart_range_raw(
        RawMarketChartRangeRequest(
            asset_symbol=args.asset_symbol,
            quote_currency=args.quote_currency,
            source_asset_id=args.source_asset_id,
            since=parse_utc_timestamp(args.since),
            until=parse_utc_timestamp(args.until),
            import_type=args.import_type,
            dry_run=args.dry_run,
        )
    )
    pprint(asdict(summary))


if __name__ == "__main__":
    main()
