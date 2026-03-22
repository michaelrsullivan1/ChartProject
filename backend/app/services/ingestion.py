from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class IngestionRequest:
    user_id: str
    import_type: str = "backfill"
    since: str | None = None
    until: str | None = None
    dry_run: bool = False


@dataclass(slots=True)
class IngestionSummary:
    source_name: str
    endpoint_name: str
    target_user_platform_id: str
    import_type: str
    started_at: datetime
    dry_run: bool
    notes: str
    raw_record_count_estimate: int | None = None


def build_ingestion_summary(
    request: IngestionRequest,
    raw_payload: dict[str, Any] | None = None,
) -> IngestionSummary:
    record_count_estimate = None
    if raw_payload and isinstance(raw_payload.get("tweets"), list):
        record_count_estimate = len(raw_payload["tweets"])

    return IngestionSummary(
        source_name="twitterapi.io",
        endpoint_name="user_tweets",
        target_user_platform_id=request.user_id,
        import_type=request.import_type,
        started_at=datetime.now(UTC),
        dry_run=request.dry_run,
        notes="Scaffold summary only. Parsing and DB commit are the next implementation steps.",
        raw_record_count_estimate=record_count_estimate,
    )
