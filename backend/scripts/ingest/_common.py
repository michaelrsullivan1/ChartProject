from calendar import monthrange
from datetime import UTC, datetime


def parse_utc_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include timezone information, for example 2024-01-01T00:00:00Z.")
    return parsed.astimezone(UTC)


def add_months(value: datetime, months: int) -> datetime:
    if months < 1:
        raise ValueError("months must be >= 1")
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)
