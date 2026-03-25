from dataclasses import dataclass
from datetime import UTC, datetime
import json
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.ingestion_run import IngestionRun
from app.models.raw_ingestion_artifact import RawIngestionArtifact
from app.services.twitterapi_client import (
    TwitterApiClient,
    TwitterTweetAdvancedSearchRequest,
    TwitterUserInfoRequest,
)


@dataclass(slots=True)
class RawUserInfoRequest:
    username: str
    import_type: str = "full_backfill"
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    debug: bool = False
    dry_run: bool = False


@dataclass(slots=True)
class RawTweetSearchWindowRequest:
    username: str
    since: datetime
    until: datetime
    import_type: str = "full_backfill"
    query_fragment: str = ""
    query_type: str = "Latest"
    page_delay_seconds: float = 0.25
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    resume_run_id: int | None = None
    target_user_platform_id: str | None = None
    debug: bool = False
    dry_run: bool = False


@dataclass(slots=True)
class IngestionSummary:
    run_id: int | None
    endpoint_name: str
    username: str
    query: str | None
    resolved_user_platform_id: str | None
    requested_since: datetime | None
    requested_until: datetime | None
    started_at: datetime
    completed_at: datetime | None
    import_type: str
    pages_fetched: int
    artifacts_created: int
    tweets_returned: int
    status: str
    resumed_from_run_id: int | None
    last_cursor: str | None
    dry_run: bool
    notes: str


def archive_user_info_raw(
    request: RawUserInfoRequest,
    *,
    client: TwitterApiClient | None = None,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> IngestionSummary:
    started_at = datetime.now(UTC)
    endpoint_name = "user_info_raw_archive"
    run_id: int | None = None
    artifacts_created = 0
    resolved_user_platform_id: str | None = None
    notes = "Raw-only archive of twitterapi.io user info. No normalization is performed."
    own_client = client is None
    client = client or TwitterApiClient(
        max_retries=request.max_retries,
        retry_backoff_seconds=request.retry_backoff_seconds,
    )

    session: Session | None = None
    run: IngestionRun | None = None

    try:
        if not request.dry_run:
            session = session_factory()
            run = _create_ingestion_run(
                session=session,
                endpoint_name=endpoint_name,
                username=request.username,
                import_type=request.import_type,
                started_at=started_at,
                notes=notes,
            )
            run_id = run.id

        request_params = {"userName": request.username}
        if request.debug:
            _print_debug_request(endpoint="/twitter/user/info", params=request_params)

        user_info_payload = client.get_user_info(TwitterUserInfoRequest(username=request.username))
        if request.debug:
            _print_debug_response(label="user_info", payload=user_info_payload)

        user_data = user_info_payload.get("data")
        if not isinstance(user_data, dict):
            raise RuntimeError("twitterapi.io user info response did not include a data object.")

        resolved_user_platform_id = _extract_required_string(
            user_data,
            "id",
            "user info response",
        )

        if session and run:
            run.target_user_platform_id = resolved_user_platform_id
            session.commit()
            _store_raw_artifact(
                session=session,
                ingestion_run_id=run.id,
                artifact_type="user_info",
                payload_json=_wrap_raw_payload(
                    endpoint="/twitter/user/info",
                    params=request_params,
                    response_payload=user_info_payload,
                ),
                record_count_estimate=1,
            )
            artifacts_created += 1

        completed_at = datetime.now(UTC)
        notes = (
            "Raw user info archive completed successfully. "
            f"Resolved platform user id {resolved_user_platform_id}."
        )
        if session and run:
            run.completed_at = completed_at
            run.status = "completed"
            run.notes = notes
            session.commit()

        return IngestionSummary(
            run_id=run_id,
            endpoint_name=endpoint_name,
            username=request.username,
            query=None,
            resolved_user_platform_id=resolved_user_platform_id,
            requested_since=None,
            requested_until=None,
            started_at=started_at,
            completed_at=completed_at,
            import_type=request.import_type,
            pages_fetched=0,
            artifacts_created=artifacts_created,
            tweets_returned=0,
            status="completed",
            resumed_from_run_id=None,
            last_cursor=None,
            dry_run=request.dry_run,
            notes=notes,
        )
    except Exception as exc:
        completed_at = datetime.now(UTC)
        notes = f"Raw user info archive failed: {exc}"
        if session and run:
            session.rollback()
            run.status = "failed"
            run.completed_at = completed_at
            run.notes = notes
            session.commit()

        return IngestionSummary(
            run_id=run_id,
            endpoint_name=endpoint_name,
            username=request.username,
            query=None,
            resolved_user_platform_id=resolved_user_platform_id,
            requested_since=None,
            requested_until=None,
            started_at=started_at,
            completed_at=completed_at,
            import_type=request.import_type,
            pages_fetched=0,
            artifacts_created=artifacts_created,
            tweets_returned=0,
            status="failed",
            resumed_from_run_id=None,
            last_cursor=None,
            dry_run=request.dry_run,
            notes=notes,
        )
    finally:
        if session:
            session.close()
        if own_client:
            client.close()


def archive_tweet_search_window_raw(
    request: RawTweetSearchWindowRequest,
    *,
    client: TwitterApiClient | None = None,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> IngestionSummary:
    _validate_search_window_request(request)

    started_at = datetime.now(UTC)
    endpoint_name = "tweet_advanced_search_raw_archive"
    query = _build_advanced_search_query(
        username=request.username,
        since=request.since,
        until=request.until,
        query_fragment=request.query_fragment,
    )

    run_id: int | None = None
    pages_fetched = 0
    artifacts_created = 0
    tweets_returned = 0
    resumed_from_run_id: int | None = None
    next_cursor_to_request = ""
    seen_cursors: set[str] = set()
    seen_page_signatures: set[tuple[str, ...]] = set()
    notes = (
        "Raw-only archive of twitterapi.io advanced_search pages. "
        "No normalization or relational upserts are performed in this step."
    )
    own_client = client is None
    client = client or TwitterApiClient(
        max_retries=request.max_retries,
        retry_backoff_seconds=request.retry_backoff_seconds,
    )

    session: Session | None = None
    run: IngestionRun | None = None

    try:
        if not request.dry_run:
            session = session_factory()
            if request.resume_run_id is not None:
                run = _load_resumable_run(session, request.resume_run_id, endpoint_name=endpoint_name)
                resumed_from_run_id = run.id
                run.status = "started"
                run.completed_at = None
                session.commit()
            else:
                run = _create_ingestion_run(
                    session=session,
                    endpoint_name=endpoint_name,
                    username=request.username,
                    import_type=request.import_type,
                    started_at=started_at,
                    notes=(
                        f"{notes} query={query!r}; "
                        f"query_type={request.query_type}; "
                        f"requested_since={request.since.isoformat()}; "
                        f"requested_until={request.until.isoformat()}"
                    ),
                    requested_since=request.since,
                    requested_until=request.until,
                    target_user_platform_id=request.target_user_platform_id,
                )
            run_id = run.id
            pages_fetched = run.pages_fetched
            tweets_returned = run.raw_tweets_fetched
            next_cursor_to_request = run.last_cursor or ""
            if next_cursor_to_request:
                seen_cursors.add(next_cursor_to_request)
            if run.target_user_platform_id:
                request.target_user_platform_id = run.target_user_platform_id

        while True:
            request_params = _build_advanced_search_request_params(
                query=query,
                query_type=request.query_type,
                cursor=next_cursor_to_request,
            )
            if request.debug:
                _print_debug_request(
                    endpoint="/twitter/tweet/advanced_search",
                    params=request_params,
                )

            search_payload = client.get_tweet_advanced_search_page(
                TwitterTweetAdvancedSearchRequest(
                    query=query,
                    query_type=request.query_type,
                    cursor=next_cursor_to_request,
                )
            )
            if request.debug:
                _print_debug_response(
                    label="tweet_advanced_search_page",
                    payload=search_payload,
                )

            tweets = _extract_search_tweets(search_payload)
            if not isinstance(tweets, list):
                if session and run:
                    page_index = run.pages_fetched + 1
                    _store_raw_artifact(
                        session=session,
                        ingestion_run_id=run.id,
                        artifact_type="tweet_advanced_search_page_unexpected",
                        payload_json=_wrap_raw_payload(
                            endpoint="/twitter/tweet/advanced_search",
                            params=_build_advanced_search_request_params(
                                query=query,
                                query_type=request.query_type,
                                cursor=next_cursor_to_request,
                                page_index=page_index,
                            ),
                            response_payload=search_payload,
                        ),
                        record_count_estimate=0,
                    )
                    artifacts_created += 1

                raise RuntimeError(
                    "twitterapi.io advanced_search response did not include a tweets array. "
                    f"Payload shape: {_summarize_payload_shape(search_payload)}"
                )

            page_signature = _build_page_signature(tweets)
            if page_signature and page_signature in seen_page_signatures:
                if session and run:
                    page_index = run.pages_fetched + 1
                    _store_raw_artifact(
                        session=session,
                        ingestion_run_id=run.id,
                        artifact_type="tweet_advanced_search_page_duplicate",
                        payload_json=_wrap_raw_payload(
                            endpoint="/twitter/tweet/advanced_search",
                            params=_build_advanced_search_request_params(
                                query=query,
                                query_type=request.query_type,
                                cursor=next_cursor_to_request,
                                page_index=page_index,
                            ),
                            response_payload=search_payload,
                        ),
                        record_count_estimate=len(tweets),
                    )
                    artifacts_created += 1

                raise RuntimeError(
                    "twitterapi.io returned a duplicate advanced_search page while paginating. "
                    "Aborting to avoid looping on the same tweet set."
                )

            pages_fetched += 1
            tweets_returned += len(tweets)
            next_cursor = search_payload.get("next_cursor")
            has_next_page = bool(search_payload.get("has_next_page"))
            if page_signature:
                seen_page_signatures.add(page_signature)

            if session and run:
                page_index = run.pages_fetched + 1
                _store_raw_artifact(
                    session=session,
                    ingestion_run_id=run.id,
                    artifact_type="tweet_advanced_search_page",
                    payload_json=_wrap_raw_payload(
                        endpoint="/twitter/tweet/advanced_search",
                        params=_build_advanced_search_request_params(
                            query=query,
                            query_type=request.query_type,
                            cursor=next_cursor_to_request,
                            page_index=page_index,
                        ),
                        response_payload=search_payload,
                    ),
                    record_count_estimate=len(tweets),
                )
                artifacts_created += 1
                run.pages_fetched = pages_fetched
                run.raw_tweets_fetched = tweets_returned
                run.last_cursor = next_cursor if has_next_page else None
                session.commit()

            if not has_next_page or not isinstance(next_cursor, str) or next_cursor == "":
                break

            if next_cursor in seen_cursors:
                raise RuntimeError(
                    "twitterapi.io returned a cursor that was already seen in this run. "
                    "Aborting to avoid a pagination loop."
                )

            next_cursor_to_request = next_cursor
            seen_cursors.add(next_cursor_to_request)
            if request.page_delay_seconds > 0:
                time.sleep(request.page_delay_seconds)

        completed_at = datetime.now(UTC)
        notes = (
            "Raw advanced_search archive completed successfully. "
            f"Fetched {pages_fetched} pages and archived {tweets_returned} tweets for query {query!r}."
        )
        if session and run:
            run.completed_at = completed_at
            run.status = "completed"
            run.last_cursor = None
            run.notes = notes
            session.commit()

        return IngestionSummary(
            run_id=run_id,
            endpoint_name=endpoint_name,
            username=request.username,
            query=query,
            resolved_user_platform_id=request.target_user_platform_id,
            requested_since=request.since,
            requested_until=request.until,
            started_at=started_at,
            completed_at=completed_at,
            import_type=request.import_type,
            pages_fetched=pages_fetched,
            artifacts_created=artifacts_created,
            tweets_returned=tweets_returned,
            status="completed",
            resumed_from_run_id=resumed_from_run_id,
            last_cursor=None,
            dry_run=request.dry_run,
            notes=notes,
        )
    except Exception as exc:
        completed_at = datetime.now(UTC)
        notes = f"Raw advanced_search archive failed: {exc}"
        if session and run:
            session.rollback()
            run.status = "failed"
            run.completed_at = completed_at
            run.last_cursor = next_cursor_to_request or run.last_cursor
            run.pages_fetched = pages_fetched
            run.raw_tweets_fetched = tweets_returned
            run.notes = notes
            session.commit()

        return IngestionSummary(
            run_id=run_id,
            endpoint_name=endpoint_name,
            username=request.username,
            query=query,
            resolved_user_platform_id=request.target_user_platform_id,
            requested_since=request.since,
            requested_until=request.until,
            started_at=started_at,
            completed_at=completed_at,
            import_type=request.import_type,
            pages_fetched=pages_fetched,
            artifacts_created=artifacts_created,
            tweets_returned=tweets_returned,
            status="failed",
            resumed_from_run_id=resumed_from_run_id,
            last_cursor=next_cursor_to_request or None,
            dry_run=request.dry_run,
            notes=notes,
        )
    finally:
        if session:
            session.close()
        if own_client:
            client.close()


def _create_ingestion_run(
    session: Session,
    *,
    endpoint_name: str,
    username: str,
    import_type: str,
    started_at: datetime,
    notes: str,
    requested_since: datetime | None = None,
    requested_until: datetime | None = None,
    target_user_platform_id: str | None = None,
) -> IngestionRun:
    run = IngestionRun(
        source_name="twitterapi.io",
        endpoint_name=endpoint_name,
        target_user_platform_id=target_user_platform_id,
        import_type=import_type,
        requested_since=requested_since,
        requested_until=requested_until,
        started_at=started_at,
        status="started",
        last_cursor="",
        pages_fetched=0,
        raw_tweets_fetched=0,
        notes=f"username={username}; {notes}",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def _load_resumable_run(
    session: Session,
    run_id: int,
    *,
    endpoint_name: str,
) -> IngestionRun:
    run = session.scalar(select(IngestionRun).where(IngestionRun.id == run_id))
    if run is None:
        raise RuntimeError(f"No ingestion run found for resume_run_id={run_id}.")
    if run.endpoint_name != endpoint_name:
        raise RuntimeError(
            f"Ingestion run {run_id} uses endpoint_name={run.endpoint_name!r}, "
            f"expected {endpoint_name!r}."
        )
    if run.status == "completed":
        raise RuntimeError(f"Ingestion run {run_id} is already completed and cannot be resumed.")
    return run


def _store_raw_artifact(
    *,
    session: Session,
    ingestion_run_id: int,
    artifact_type: str,
    payload_json: dict[str, Any],
    record_count_estimate: int | None,
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


def _wrap_raw_payload(
    *,
    endpoint: str,
    params: dict[str, Any],
    response_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "endpoint": endpoint,
        "request": {
            "params": params,
            "fetched_at": datetime.now(UTC).isoformat(),
        },
        "response": response_payload,
    }


def _validate_search_window_request(request: RawTweetSearchWindowRequest) -> None:
    if request.since.tzinfo is None or request.until.tzinfo is None:
        raise RuntimeError("Search window timestamps must be timezone-aware.")
    if request.until <= request.since:
        raise RuntimeError("Search window requires until > since.")
    if request.query_type != "Latest":
        raise RuntimeError("Only queryType=Latest is currently supported by this ingest flow.")


def _build_advanced_search_query(
    *,
    username: str,
    since: datetime,
    until: datetime,
    query_fragment: str,
) -> str:
    parts = [f"from:{username}"]
    fragment = query_fragment.strip()
    if fragment:
        parts.append(fragment)
    parts.append(f"since:{_format_search_query_timestamp(since)}")
    parts.append(f"until:{_format_search_query_timestamp(until)}")
    return " ".join(parts)


def _build_advanced_search_request_params(
    *,
    query: str,
    query_type: str,
    cursor: str,
    page_index: int | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "query": query,
        "queryType": query_type,
    }
    if cursor:
        params["cursor"] = cursor
    if page_index is not None:
        params["pageIndex"] = page_index
    return params


def _format_search_query_timestamp(value: datetime) -> str:
    normalized = value.astimezone(UTC)
    return normalized.strftime("%Y-%m-%d_%H:%M:%S_UTC")


def _extract_required_string(
    payload: dict[str, Any],
    key: str,
    context: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value == "":
        raise RuntimeError(f"Missing required string '{key}' in {context}.")
    return value


def _extract_search_tweets(payload: dict[str, Any]) -> Any:
    tweets = payload.get("tweets")
    if isinstance(tweets, list):
        return tweets

    data = payload.get("data")
    if isinstance(data, dict):
        nested_tweets = data.get("tweets")
        if isinstance(nested_tweets, list):
            return nested_tweets

    return None


def _summarize_payload_keys(payload: dict[str, Any]) -> str:
    keys = sorted(str(key) for key in payload.keys())
    if not keys:
        return "<none>"
    return ", ".join(keys)


def _summarize_payload_shape(payload: dict[str, Any]) -> str:
    parts = [f"top-level keys: {_summarize_payload_keys(payload)}"]
    data = payload.get("data")
    if isinstance(data, list):
        parts.append(f"data=list(len={len(data)})")
    elif isinstance(data, dict):
        parts.append(f"data=dict(keys={_summarize_payload_keys(data)})")
    elif data is None:
        parts.append("data=<none>")
    else:
        parts.append(f"data={type(data).__name__}")
    tweets = payload.get("tweets")
    if isinstance(tweets, list):
        parts.append(f"tweets=list(len={len(tweets)})")
    elif tweets is None:
        parts.append("tweets=<none>")
    else:
        parts.append(f"tweets={type(tweets).__name__}")
    return "; ".join(parts)


def _print_debug_request(*, endpoint: str, params: dict[str, Any]) -> None:
    print(f"[debug] request endpoint={endpoint} params={params}")


def _print_debug_response(*, label: str, payload: dict[str, Any]) -> None:
    print(f"[debug] response {label} shape: {_summarize_payload_shape(payload)}")
    preview = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    if len(preview) > 4000:
        preview = f"{preview[:4000]}\n...<truncated>"
    print(f"[debug] response {label} payload:\n{preview}")


def _build_page_signature(tweets: list[Any]) -> tuple[str, ...]:
    signature: list[str] = []
    for tweet in tweets:
        if isinstance(tweet, dict):
            tweet_id = tweet.get("id")
            if isinstance(tweet_id, str) and tweet_id:
                signature.append(tweet_id)
    return tuple(signature)
