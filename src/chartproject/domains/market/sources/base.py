from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class MarketPullResult:
    source_name: str
    source_url: str
    raw_payload: str
    raw_extension: str
    dataframe: pd.DataFrame


class MarketDataSource(Protocol):
    source_name: str

    def fetch_daily_prices(self) -> MarketPullResult:
        """Fetch daily BTC price data and return normalized frame contract."""
