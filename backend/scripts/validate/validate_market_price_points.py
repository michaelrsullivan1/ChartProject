import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.market_data import (
    ValidateMarketPriceRequest,
    render_market_price_validation_report,
    validate_market_price_points,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate canonical market_price_points against archived raw BTC market chart artifacts."
    )
    parser.add_argument("--asset-symbol", default="BTC")
    parser.add_argument("--quote-currency", default="USD")
    parser.add_argument("--interval", default="day")
    parser.add_argument("--sample-limit", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = validate_market_price_points(
        ValidateMarketPriceRequest(
            asset_symbol=args.asset_symbol,
            quote_currency=args.quote_currency,
            interval=args.interval,
            sample_limit=args.sample_limit,
        )
    )
    print(render_market_price_validation_report(summary))
    if summary.status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
