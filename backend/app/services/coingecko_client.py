from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass(slots=True)
class CoinGeckoMarketChartRangeRequest:
    coin_id: str
    vs_currency: str
    from_unix_seconds: int
    to_unix_seconds: int


class CoinGeckoClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = settings.coingecko_base_url.rstrip("/")
        self.api_key = settings.coingecko_api_key.strip()
        headers: dict[str, str] = {}
        if self.api_key:
            # CoinGecko uses different key types across plans; accept one configured value and send
            # both common header names so local scripts work regardless of plan tier.
            headers["x-cg-pro-api-key"] = self.api_key
            headers["x-cg-demo-api-key"] = self.api_key
        self._client = httpx.Client(timeout=timeout_seconds, headers=headers)

    def close(self) -> None:
        self._client.close()

    def get_market_chart_range(
        self,
        request: CoinGeckoMarketChartRangeRequest,
    ) -> dict[str, Any]:
        response = self._client.get(
            f"{self.base_url}/coins/{request.coin_id}/market_chart/range",
            params={
                "vs_currency": request.vs_currency,
                "from": request.from_unix_seconds,
                "to": request.to_unix_seconds,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("CoinGecko returned a non-object payload for market_chart/range.")
        return payload
