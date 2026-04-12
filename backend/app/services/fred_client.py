from __future__ import annotations

import httpx


class FredClient:
    def __init__(self, *, timeout_seconds: float = 30.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def get_series_csv(self, series_id: str) -> str:
        response = self._client.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}")
        response.raise_for_status()
        return response.text
