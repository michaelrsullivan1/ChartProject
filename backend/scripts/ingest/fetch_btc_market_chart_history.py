import argparse
from dataclasses import asdict
from datetime import timedelta
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
        description="Archive raw BTC/USD market chart data from CoinGecko across multiple UTC windows."
    )
    parser.add_argument("--since", required=True, help="UTC start timestamp, for example 2012-01-01T00:00:00Z")
    parser.add_argument("--until", required=True, help="UTC end timestamp, for example 2026-03-27T00:00:00Z")
    parser.add_argument("--asset-symbol", default="BTC")
    parser.add_argument("--quote-currency", default="USD")
    parser.add_argument("--source-asset-id", default="bitcoin")
    parser.add_argument("--window-days", type=int, default=365)
    parser.add_argument("--import-type", default="full_backfill", choices=["full_backfill", "refresh"])
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    since = parse_utc_timestamp(args.since)
    until = parse_utc_timestamp(args.until)
    if until <= since:
        raise SystemExit("--until must be greater than --since")
    if args.window_days < 91:
        raise SystemExit("--window-days must be >= 91 so CoinGecko returns daily historical data")

    summaries = []
    current_since = since
    while current_since < until:
        current_until = min(current_since + timedelta(days=args.window_days), until)
        summary = archive_btc_market_chart_range_raw(
            RawMarketChartRangeRequest(
                asset_symbol=args.asset_symbol,
                quote_currency=args.quote_currency,
                source_asset_id=args.source_asset_id,
                interval="day",
                since=current_since,
                until=current_until,
                import_type=args.import_type,
                dry_run=args.dry_run,
            )
        )
        summaries.append(summary)
        pprint({"window_summary": asdict(summary)})
        if summary.status != "completed":
            raise SystemExit(1)
        current_since = current_until

    pprint(
        {
            "asset_symbol": args.asset_symbol,
            "quote_currency": args.quote_currency,
            "history_since": since.isoformat(),
            "history_until": until.isoformat(),
            "window_days": args.window_days,
            "windows_completed": len(summaries),
            "points_archived": sum(item.points_archived for item in summaries),
        }
    )


if __name__ == "__main__":
    main()
