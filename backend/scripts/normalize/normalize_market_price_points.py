import argparse
from dataclasses import asdict
from pathlib import Path
from pprint import pprint
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.market_data import NormalizeMarketPriceRequest, normalize_market_price_points


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize archived BTC/USD market chart artifacts into canonical market_price_points."
    )
    parser.add_argument("--asset-symbol", default="BTC")
    parser.add_argument("--quote-currency", default="USD")
    parser.add_argument("--interval", default="day")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = normalize_market_price_points(
        NormalizeMarketPriceRequest(
            asset_symbol=args.asset_symbol,
            quote_currency=args.quote_currency,
            interval=args.interval,
            dry_run=args.dry_run,
        )
    )
    pprint(asdict(summary))


if __name__ == "__main__":
    main()
