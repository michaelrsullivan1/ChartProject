from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import io
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.ingestion_run import IngestionRun
from app.models.market_price_point import MarketPricePoint
from app.models.raw_ingestion_artifact import RawIngestionArtifact
from app.services.coinbase_client import CoinbaseClient
from app.services.fred_client import FredClient
from app.services.twelvedata_client import TwelveDataClient


@dataclass(slots=True)
class RawFredSeriesRequest:
    series_id: str = "CBBTCUSD"
    asset_symbol: str = "BTC"
    quote_currency: str = "USD"
    interval: str = "day"
    import_type: str = "full_backfill"
    dry_run: bool = False


@dataclass(slots=True)
class RawEquitySeriesRequest:
    symbol: str
    asset_symbol: str
    quote_currency: str = "USD"
    interval: str = "day"
    import_type: str = "full_backfill"
    dry_run: bool = False


@dataclass(slots=True)
class RawMarketDataSummary:
    run_id: int | None
    asset_symbol: str
    quote_currency: str
    interval: str
    points_archived: int
    status: str
    started_at: datetime
    completed_at: datetime | None
    notes: str


@dataclass(slots=True)
class NormalizeMarketPriceRequest:
    asset_symbol: str = "BTC"
    quote_currency: str = "USD"
    interval: str = "day"
    dry_run: bool = False


@dataclass(slots=True)
class NormalizeMarketPriceSummary:
    asset_symbol: str
    quote_currency: str
    interval: str
    raw_artifacts_scanned: int
    raw_point_count: int
    normalized_point_count: int
    raw_first_point_at: datetime | None
    raw_last_point_at: datetime | None
    normalized_first_point_at: datetime | None
    normalized_last_point_at: datetime | None
    dry_run: bool
    notes: str


@dataclass(slots=True)
class ValidateMarketPriceRequest:
    asset_symbol: str = "BTC"
    quote_currency: str = "USD"
    interval: str = "day"
    sample_limit: int = 10


@dataclass(slots=True)
class ValidateMarketPriceSummary:
    asset_symbol: str
    quote_currency: str
    interval: str
    status: str
    raw_artifacts_scanned: int
    raw_point_count: int
    normalized_point_count: int
    raw_first_point_at: datetime | None
    raw_last_point_at: datetime | None
    normalized_first_point_at: datetime | None
    normalized_last_point_at: datetime | None
    missing_point_count: int
    extra_point_count: int
    sample_missing_points: list[str]
    sample_extra_points: list[str]
    notes: str


@dataclass(slots=True)
class MarketPriceSnapshot:
    asset_symbol: str
    quote_currency: str
    interval: str
    observed_at: datetime
    price: float
    market_cap: float | None
    total_volume: float | None
    source_name: str = "fred"


@dataclass(slots=True)
class SpotPriceSummary:
    asset_symbol: str
    quote_currency: str
    price: float
    fetched_at: datetime
    source_name: str


def archive_fred_btc_daily_raw(
    request: RawFredSeriesRequest,
    *,
    client: FredClient | None = None,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> RawMarketDataSummary:
    if request.interval != "day":
        raise RuntimeError("FRED BTC ingestion currently supports only interval=day.")

    own_client = client is None
    client = client or FredClient()
    started_at = datetime.now(UTC)
    session: Session | None = None
    run: IngestionRun | None = None
    run_id: int | None = None
    try:
        csv_text = client.get_series_csv(request.series_id)
        points_archived = len(_extract_fred_series_points(csv_text))
        if not request.dry_run:
            session = session_factory()
            run = _create_market_ingestion_run(
                session=session,
                source_name="fred",
                endpoint_name="fred_series_csv_raw_archive",
                import_type=request.import_type,
                started_at=started_at,
                notes=(
                    f"asset_symbol={request.asset_symbol}; quote_currency={request.quote_currency}; "
                    f"interval={request.interval}; series_id={request.series_id}"
                ),
            )
            run_id = run.id
            _store_market_raw_artifact(
                session=session,
                ingestion_run_id=run.id,
                artifact_type="fred_series_csv",
                payload_json={
                    "endpoint": "/graph/fredgraph.csv",
                    "request": {
                        "series_id": request.series_id,
                        "asset_symbol": request.asset_symbol.upper(),
                        "quote_currency": request.quote_currency.upper(),
                        "interval": request.interval,
                        "fetched_at": datetime.now(UTC).isoformat(),
                    },
                    "response": {
                        "csv_text": csv_text,
                    },
                },
                record_count_estimate=points_archived,
            )
            completed_at = datetime.now(UTC)
            run.completed_at = completed_at
            run.status = "completed"
            run.notes = (
                f"Archived {points_archived} FRED price points for "
                f"{request.asset_symbol.upper()}/{request.quote_currency.upper()}."
            )
            session.commit()
        else:
            completed_at = datetime.now(UTC)

        return RawMarketDataSummary(
            run_id=run_id,
            asset_symbol=request.asset_symbol.upper(),
            quote_currency=request.quote_currency.upper(),
            interval=request.interval,
            points_archived=points_archived,
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
            notes="Raw FRED BTC daily archive completed successfully.",
        )
    finally:
        if session is not None:
            session.close()
        if own_client:
            client.close()


def fetch_coinbase_spot_price(
    *,
    product: str = "BTC-USD",
    client: CoinbaseClient | None = None,
) -> SpotPriceSummary:
    own_client = client is None
    client = client or CoinbaseClient()
    fetched_at = datetime.now(UTC)
    try:
        payload = client.get_spot_price(product)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("Coinbase spot price response did not include a data object.")

        raw_asset_symbol = data.get("base")
        raw_quote_currency = data.get("currency")
        raw_amount = data.get("amount")
        if not isinstance(raw_asset_symbol, str) or not isinstance(raw_quote_currency, str):
            raise RuntimeError("Coinbase spot price response was missing product symbols.")
        if not isinstance(raw_amount, str):
            raise RuntimeError("Coinbase spot price response was missing an amount.")

        return SpotPriceSummary(
            asset_symbol=raw_asset_symbol.upper(),
            quote_currency=raw_quote_currency.upper(),
            price=float(raw_amount),
            fetched_at=fetched_at,
            source_name="coinbase",
        )
    finally:
        if own_client:
            client.close()


def archive_twelvedata_equity_daily_raw(
    request: RawEquitySeriesRequest,
    *,
    client: TwelveDataClient | None = None,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> RawMarketDataSummary:
    if request.interval != "day":
        raise RuntimeError("Twelve Data equity ingestion currently supports only interval=day.")

    own_client = client is None
    client = client or TwelveDataClient(api_key=settings.twelvedata_api_key)
    started_at = datetime.now(UTC)
    session: Session | None = None
    run: IngestionRun | None = None
    run_id: int | None = None
    try:
        response_payload = client.get_time_series_daily_full(request.symbol)
        points_archived = len(_extract_twelvedata_series_points(response_payload))
        if not request.dry_run:
            session = session_factory()
            run = _create_market_ingestion_run(
                session=session,
                source_name="twelvedata",
                endpoint_name="time_series_raw_archive",
                import_type=request.import_type,
                started_at=started_at,
                notes=(
                    f"symbol={request.symbol}; asset_symbol={request.asset_symbol}; "
                    f"quote_currency={request.quote_currency}; interval={request.interval}"
                ),
            )
            run_id = run.id
            _store_market_raw_artifact(
                session=session,
                ingestion_run_id=run.id,
                artifact_type="twelvedata_time_series_json",
                payload_json={
                    "endpoint": "/time_series",
                    "request": {
                        "symbol": request.symbol.upper(),
                        "asset_symbol": request.asset_symbol.upper(),
                        "quote_currency": request.quote_currency.upper(),
                        "interval": request.interval,
                        "fetched_at": datetime.now(UTC).isoformat(),
                    },
                    "response": response_payload,
                },
                record_count_estimate=points_archived,
            )
            completed_at = datetime.now(UTC)
            run.completed_at = completed_at
            run.status = "completed"
            run.notes = (
                f"Archived {points_archived} Twelve Data price points for "
                f"{request.asset_symbol.upper()}/{request.quote_currency.upper()}."
            )
            session.commit()
        else:
            completed_at = datetime.now(UTC)

        return RawMarketDataSummary(
            run_id=run_id,
            asset_symbol=request.asset_symbol.upper(),
            quote_currency=request.quote_currency.upper(),
            interval=request.interval,
            points_archived=points_archived,
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
            notes="Raw Twelve Data equity daily archive completed successfully.",
        )
    finally:
        if session is not None:
            session.close()
        if own_client:
            client.close()


def normalize_market_price_points(
    request: NormalizeMarketPriceRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> NormalizeMarketPriceSummary:
    session = session_factory()
    try:
        snapshots, raw_artifacts_scanned, raw_first_point_at, raw_last_point_at = _build_market_snapshots(
            session,
            asset_symbol=request.asset_symbol,
            quote_currency=request.quote_currency,
            interval=request.interval,
        )
        if request.dry_run:
            return NormalizeMarketPriceSummary(
                asset_symbol=request.asset_symbol.upper(),
                quote_currency=request.quote_currency.upper(),
                interval=request.interval,
                raw_artifacts_scanned=raw_artifacts_scanned,
                raw_point_count=len(snapshots),
                normalized_point_count=0,
                raw_first_point_at=raw_first_point_at,
                raw_last_point_at=raw_last_point_at,
                normalized_first_point_at=None,
                normalized_last_point_at=None,
                dry_run=True,
                notes=f"Prepared {len(snapshots)} market price points without writing to canonical tables.",
            )

        _upsert_market_price_points(session, list(snapshots.values()))
        session.commit()

        normalized_point_count, normalized_first_point_at, normalized_last_point_at = session.execute(
            select(
                func.count(MarketPricePoint.id),
                func.min(MarketPricePoint.observed_at),
                func.max(MarketPricePoint.observed_at),
            ).where(
                MarketPricePoint.asset_symbol == request.asset_symbol.upper(),
                MarketPricePoint.quote_currency == request.quote_currency.upper(),
                MarketPricePoint.interval == request.interval,
            )
        ).one()
        return NormalizeMarketPriceSummary(
            asset_symbol=request.asset_symbol.upper(),
            quote_currency=request.quote_currency.upper(),
            interval=request.interval,
            raw_artifacts_scanned=raw_artifacts_scanned,
            raw_point_count=len(snapshots),
            normalized_point_count=normalized_point_count,
            raw_first_point_at=raw_first_point_at,
            raw_last_point_at=raw_last_point_at,
            normalized_first_point_at=normalized_first_point_at,
            normalized_last_point_at=normalized_last_point_at,
            dry_run=False,
            notes="Market price normalization completed successfully.",
        )
    finally:
        session.close()


def validate_market_price_points(
    request: ValidateMarketPriceRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> ValidateMarketPriceSummary:
    session = session_factory()
    try:
        snapshots, raw_artifacts_scanned, raw_first_point_at, raw_last_point_at = _build_market_snapshots(
            session,
            asset_symbol=request.asset_symbol,
            quote_currency=request.quote_currency,
            interval=request.interval,
        )
        expected_keys = set(snapshots.keys())
        normalized_rows = session.execute(
            select(MarketPricePoint.observed_at)
            .where(
                MarketPricePoint.asset_symbol == request.asset_symbol.upper(),
                MarketPricePoint.quote_currency == request.quote_currency.upper(),
                MarketPricePoint.interval == request.interval,
            )
            .order_by(MarketPricePoint.observed_at)
        ).all()
        normalized_keys = {row[0] for row in normalized_rows}
        missing_keys = expected_keys - normalized_keys
        extra_keys = normalized_keys - expected_keys
        normalized_first_point_at = normalized_rows[0][0] if normalized_rows else None
        normalized_last_point_at = normalized_rows[-1][0] if normalized_rows else None
        status = "PASS"
        if (
            missing_keys
            or extra_keys
            or raw_first_point_at != normalized_first_point_at
            or raw_last_point_at != normalized_last_point_at
        ):
            status = "FAIL"
        return ValidateMarketPriceSummary(
            asset_symbol=request.asset_symbol.upper(),
            quote_currency=request.quote_currency.upper(),
            interval=request.interval,
            status=status,
            raw_artifacts_scanned=raw_artifacts_scanned,
            raw_point_count=len(snapshots),
            normalized_point_count=len(normalized_keys),
            raw_first_point_at=raw_first_point_at,
            raw_last_point_at=raw_last_point_at,
            normalized_first_point_at=normalized_first_point_at,
            normalized_last_point_at=normalized_last_point_at,
            missing_point_count=len(missing_keys),
            extra_point_count=len(extra_keys),
            sample_missing_points=[item.isoformat() for item in sorted(missing_keys)[: request.sample_limit]],
            sample_extra_points=[item.isoformat() for item in sorted(extra_keys)[: request.sample_limit]],
            notes=(
                f"Validated {len(snapshots)} raw market price points against canonical "
                "market_price_points."
            ),
        )
    finally:
        session.close()


def render_market_price_validation_report(summary: ValidateMarketPriceSummary) -> str:
    lines = [
        f"Validation report for {summary.asset_symbol}/{summary.quote_currency} ({summary.interval})",
        f"status: {summary.status}",
        "",
        f"- raw artifacts scanned: {summary.raw_artifacts_scanned}",
        f"- raw point count: {summary.raw_point_count}",
        f"- normalized point count: {summary.normalized_point_count}",
        f"- raw first point: {summary.raw_first_point_at}",
        f"- normalized first point: {summary.normalized_first_point_at}",
        f"- raw last point: {summary.raw_last_point_at}",
        f"- normalized last point: {summary.normalized_last_point_at}",
        f"- missing points: {summary.missing_point_count}",
        f"- extra points: {summary.extra_point_count}",
        "",
        f"notes: {summary.notes}",
    ]
    if summary.sample_missing_points:
        lines.append("missing point samples:")
        lines.extend(f"- {sample}" for sample in summary.sample_missing_points)
    if summary.sample_extra_points:
        lines.append("extra point samples:")
        lines.extend(f"- {sample}" for sample in summary.sample_extra_points)
    return "\n".join(lines)


def _create_market_ingestion_run(
    session: Session,
    *,
    source_name: str,
    endpoint_name: str,
    import_type: str,
    started_at: datetime,
    notes: str,
) -> IngestionRun:
    run = IngestionRun(
        source_name=source_name,
        endpoint_name=endpoint_name,
        import_type=import_type,
        requested_since=None,
        requested_until=None,
        started_at=started_at,
        status="started",
        last_cursor=None,
        pages_fetched=1,
        raw_tweets_fetched=0,
        notes=notes,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def _store_market_raw_artifact(
    *,
    session: Session,
    ingestion_run_id: int,
    artifact_type: str,
    payload_json: dict[str, Any],
    record_count_estimate: int,
) -> RawIngestionArtifact:
    artifact = RawIngestionArtifact(
        ingestion_run_id=ingestion_run_id,
        artifact_type=artifact_type,
        payload_json=payload_json,
        record_count_estimate=record_count_estimate,
        source_path=None,
        created_at=datetime.now(UTC),
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return artifact


def _extract_fred_series_points(csv_text: str) -> list[tuple[datetime, float, float | None, float | None]]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows: list[tuple[datetime, float, float | None, float | None]] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        observation_date = row.get("observation_date")
        value = row.get("CBBTCUSD")
        if not isinstance(observation_date, str) or not isinstance(value, str):
            continue
        stripped = value.strip()
        if stripped == "":
            continue
        observed_at = datetime.fromisoformat(observation_date).replace(tzinfo=UTC)
        rows.append((observed_at, float(stripped), None, None))
    return rows


def _extract_twelvedata_series_points(
    payload: dict[str, Any],
) -> list[tuple[datetime, float, float | None, float | None]]:
    if not isinstance(payload, dict):
        return []
    if payload.get("status") == "error":
        code = payload.get("code")
        message = payload.get("message")
        raise RuntimeError(f"Twelve Data returned error code={code!r}: {message}")
    values = payload.get("values")
    if not isinstance(values, list):
        return []

    rows: list[tuple[datetime, float, float | None, float | None]] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        raw_date = item.get("datetime")
        raw_price = item.get("close")
        raw_volume = item.get("volume")
        if not isinstance(raw_date, str):
            continue
        if raw_price is None:
            continue
        try:
            observed_at = datetime.fromisoformat(raw_date).replace(tzinfo=UTC)
            price = float(raw_price)
            total_volume = None if raw_volume is None else float(raw_volume)
        except (TypeError, ValueError):
            continue
        rows.append((observed_at, price, None, total_volume))
    return rows


def _build_market_snapshots(
    session: Session,
    *,
    asset_symbol: str,
    quote_currency: str,
    interval: str,
) -> tuple[dict[datetime, MarketPriceSnapshot], int, datetime | None, datetime | None]:
    snapshots: dict[datetime, MarketPriceSnapshot] = {}
    raw_artifacts_scanned = 0
    raw_first_point_at: datetime | None = None
    raw_last_point_at: datetime | None = None
    artifacts = session.execute(
        select(RawIngestionArtifact, IngestionRun)
        .join(IngestionRun, IngestionRun.id == RawIngestionArtifact.ingestion_run_id)
        .where(
            RawIngestionArtifact.artifact_type.in_(
                ["fred_series_csv", "twelvedata_time_series_json"]
            ),
            IngestionRun.source_name.in_(["fred", "twelvedata"]),
        )
        .order_by(RawIngestionArtifact.id)
    ).all()

    for artifact, run in artifacts:
        payload = artifact.payload_json
        if not isinstance(payload, dict):
            continue
        request_payload = payload.get("request")
        response_payload = payload.get("response")
        if not isinstance(request_payload, dict):
            continue
        if not isinstance(response_payload, (dict, list)):
            continue
        if request_payload.get("asset_symbol") != asset_symbol.upper():
            continue
        if request_payload.get("quote_currency") != quote_currency.upper():
            continue
        if request_payload.get("interval") != interval:
            continue
        raw_artifacts_scanned += 1
        if artifact.artifact_type == "fred_series_csv":
            csv_text = response_payload.get("csv_text")
            if not isinstance(csv_text, str):
                continue
            extracted_rows = _extract_fred_series_points(csv_text)
        elif artifact.artifact_type == "twelvedata_time_series_json":
            if not isinstance(response_payload, dict):
                continue
            extracted_rows = _extract_twelvedata_series_points(response_payload)
        else:
            continue

        for observed_at, price, market_cap, total_volume in extracted_rows:
            snapshot = MarketPriceSnapshot(
                asset_symbol=asset_symbol.upper(),
                quote_currency=quote_currency.upper(),
                interval=interval,
                observed_at=floor_to_day(observed_at),
                price=price,
                market_cap=market_cap,
                total_volume=total_volume,
                source_name=run.source_name,
            )
            snapshots[snapshot.observed_at] = snapshot
            raw_first_point_at = (
                snapshot.observed_at if raw_first_point_at is None else min(raw_first_point_at, snapshot.observed_at)
            )
            raw_last_point_at = (
                snapshot.observed_at if raw_last_point_at is None else max(raw_last_point_at, snapshot.observed_at)
            )

    if not snapshots:
        raise RuntimeError(
            f"No archived market chart artifacts found for {asset_symbol.upper()}/{quote_currency.upper()} ({interval})."
        )
    return snapshots, raw_artifacts_scanned, raw_first_point_at, raw_last_point_at


def _upsert_market_price_points(session: Session, snapshots: list[MarketPriceSnapshot]) -> None:
    rows = [
        {
            "source_name": snapshot.source_name,
            "asset_symbol": snapshot.asset_symbol,
            "quote_currency": snapshot.quote_currency,
            "interval": snapshot.interval,
            "observed_at": snapshot.observed_at,
            "price": snapshot.price,
            "market_cap": snapshot.market_cap,
            "total_volume": snapshot.total_volume,
        }
        for snapshot in snapshots
    ]
    for chunk in _chunked(rows, size=1000):
        stmt = insert(MarketPricePoint).values(chunk)
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[
                    MarketPricePoint.asset_symbol,
                    MarketPricePoint.quote_currency,
                    MarketPricePoint.interval,
                    MarketPricePoint.observed_at,
                ],
                set_={
                    "source_name": stmt.excluded.source_name,
                    "price": stmt.excluded.price,
                    "market_cap": stmt.excluded.market_cap,
                    "total_volume": stmt.excluded.total_volume,
                    "updated_at": func.now(),
                },
            )
        )


def _chunked(values: list[Any], *, size: int) -> list[list[Any]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def floor_to_day(value: datetime) -> datetime:
    normalized = value.astimezone(UTC)
    return normalized.replace(hour=0, minute=0, second=0, microsecond=0)


def floor_to_week(value: datetime) -> datetime:
    day_start = floor_to_day(value)
    return day_start - timedelta(days=day_start.weekday())
