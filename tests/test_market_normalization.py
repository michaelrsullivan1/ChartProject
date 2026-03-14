from __future__ import annotations

import pandas as pd

from chartproject.domains.market.normalization import normalize_daily_market_frame


def test_normalize_daily_market_frame_dedupes_and_drops_invalid_rows() -> None:
    frame = pd.DataFrame(
        {
            "Date": ["2024-01-01", "2024-01-01", "bad-date", "2024-01-02"],
            "Open": [100, 101, 120, 105],
            "High": [110, 111, 125, 115],
            "Low": [90, 91, 118, 95],
            "Close": [105, 106, 123, 110],
            "Volume": [10, 11, 12, 20],
        }
    )

    normalized = normalize_daily_market_frame(frame, "test_source")

    assert list(normalized.columns) == [
        "date",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
    ]
    assert len(normalized) == 2
    assert str(normalized.iloc[0]["date"]) == "2024-01-01"
    assert normalized.iloc[0]["open"] == 101
    assert normalized.iloc[0]["source"] == "test_source"
