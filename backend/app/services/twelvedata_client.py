from __future__ import annotations

from typing import Any

import httpx


class TwelveDataClient:
    def __init__(self, api_key: str, *, timeout_seconds: float = 30.0) -> None:
        if not api_key.strip():
            raise RuntimeError("Twelve Data API key is required to fetch equity price history.")
        self._api_key = api_key.strip()
        self._client = httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def get_time_series_daily_full(self, symbol: str) -> dict[str, Any]:
        response = self._client.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol": symbol,
                "interval": "1day",
                "outputsize": "5000",
                "apikey": self._api_key,
            },
        )
        response.raise_for_status()
        return response.json()
