from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close"]


def normalize_daily_market_frame(frame: pd.DataFrame, source_name: str) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    normalized = pd.DataFrame(
        {
            "date": pd.to_datetime(frame["Date"], utc=True, errors="coerce").dt.date,
            "timestamp": pd.to_datetime(frame["Date"], utc=True, errors="coerce"),
            "open": pd.to_numeric(frame["Open"], errors="coerce"),
            "high": pd.to_numeric(frame["High"], errors="coerce"),
            "low": pd.to_numeric(frame["Low"], errors="coerce"),
            "close": pd.to_numeric(frame["Close"], errors="coerce"),
            "volume": pd.to_numeric(frame.get("Volume"), errors="coerce"),
            "source": source_name,
        }
    )
    normalized = normalized.dropna(subset=["date", "open", "high", "low", "close"])
    normalized = normalized.sort_values("date").drop_duplicates(subset=["date", "source"], keep="last")
    return normalized.reset_index(drop=True)
