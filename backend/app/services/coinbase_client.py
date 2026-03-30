from __future__ import annotations

from typing import Any

import httpx


class CoinbaseClient:
    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def get_spot_price(self, product: str) -> dict[str, Any]:
        response = self._client.get(f"https://api.coinbase.com/v2/prices/{product}/spot")
        response.raise_for_status()
        return response.json()
