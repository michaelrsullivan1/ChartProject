from __future__ import annotations

from io import StringIO
import logging
import subprocess
from urllib.error import URLError
from urllib.request import urlopen

import pandas as pd

from chartproject.domains.market.sources.base import MarketPullResult

LOGGER = logging.getLogger(__name__)


class StooqBtcUsdDailySource:
    """Pull BTC/USD daily candles from stooq CSV endpoint."""

    source_name = "stooq"
    source_url = "https://stooq.com/q/d/l/?s=btcusd&i=d"

    def _download_payload(self) -> str:
        try:
            with urlopen(self.source_url, timeout=30) as response:
                return response.read().decode("utf-8")
        except URLError as error:
            LOGGER.warning("urllib download failed (%s); trying curl fallback", error)
            result = subprocess.run(
                ["curl", "-fsSL", self.source_url],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout

    def fetch_daily_prices(self) -> MarketPullResult:
        payload = self._download_payload()
        frame = pd.read_csv(StringIO(payload))
        return MarketPullResult(
            source_name=self.source_name,
            source_url=self.source_url,
            raw_payload=payload,
            raw_extension="csv",
            dataframe=frame,
        )
