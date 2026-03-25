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
    TwitterUserInfoRequest,
    TwitterUserLastTweetsRequest,
)


@dataclass(slots=True)
class IngestionRequest:
    username: str
    import_type: str = "full_backfill"
    include_replies: bool = True
    page_delay_seconds: float = 0.25
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    resume_run_id: int | None = None
    debug: bool = False
    dry_run: bool = False


@dataclass(slots=True)
class IngestionSummary:
    run_id: int | None
    username: str
    resolved_user_platform_id: str | None
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


def archive_user_timeline_raw(
    request: IngestionRequest,
    *,
    client: TwitterApiClient | None = None,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> IngestionSummary:
    started_at = datetime.now(UTC)
    run_id: int | None = None
    resolved_user_platform_id: str | None = None
    pages_fetched = 0
    artifacts_created = 0
    tweets_returned = 0
    status = "started"
    resumed_from_run_id: int | None = None
    next_cursor_to_request = ""
    seen_cursors: set[str] = set()
    seen_page_signatures: set[tuple[str, ...]] = set()
    notes = (
        "Raw-only archive. No normalization or relational upserts are performed in this step."
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
                run = _load_resumable_run(session, request.resume_run_id)
                resumed_from_run_id = run.id
                run.status = "started"
                run.completed_at = None
                session.commit()
            else:
                run = _create_ingestion_run(session, request, started_at)
            run_id = run.id
            pages_fetched = run.pages_fetched
            tweets_returned = run.raw_tweets_fetched
            next_cursor_to_request = run.last_cursor or ""
            if next_cursor_to_request:
                seen_cursors.add(next_cursor_to_request)

        if resumed_from_run_id is not None and run and run.target_user_platform_id:
            resolved_user_platform_id = run.target_user_platform_id
        else:
            if request.debug:
                _print_debug_request(
                    endpoint="/twitter/user/info",
                    params={"userName": request.username},
                )
            user_info_payload = client.get_user_info(TwitterUserInfoRequest(username=request.username))
            if request.debug:
                _print_debug_response(
                    label="user_info",
                    payload=user_info_payload,
                )
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
                        params={"userName": request.username},
                        response_payload=user_info_payload,
                    ),
                    record_count_estimate=1,
                )
                artifacts_created += 1

        while True:
            timeline_params = _build_last_tweets_request_params(
                username=request.username,
                include_replies=request.include_replies,
                cursor=next_cursor_to_request,
            )
            if request.debug:
                _print_debug_request(
                    endpoint="/twitter/user/last_tweets",
                    params=timeline_params,
                )
            timeline_payload = client.get_user_last_tweets_page(
                TwitterUserLastTweetsRequest(
                    user_name=request.username,
                    include_replies=request.include_replies,
                    cursor=next_cursor_to_request,
                )
            )
            if request.debug:
                _print_debug_response(
                    label="user_last_tweets_page",
                    payload=timeline_payload,
                )

            tweets = _extract_timeline_tweets(timeline_payload)
            if not isinstance(tweets, list):
                if session and run:
                    page_index = run.pages_fetched + 1
                    _store_raw_artifact(
                        session=session,
                        ingestion_run_id=run.id,
                        artifact_type="user_last_tweets_page_unexpected",
                        payload_json=_wrap_raw_payload(
                            endpoint="/twitter/user/last_tweets",
                            params=_build_last_tweets_request_params(
                                username=request.username,
                                include_replies=request.include_replies,
                                cursor=next_cursor_to_request,
                                page_index=page_index,
                            ),
                            response_payload=timeline_payload,
                        ),
                        record_count_estimate=0,
                    )
                    artifacts_created += 1

                raise RuntimeError(
                    "twitterapi.io last_tweets response did not include a tweets array. "
                    f"Payload shape: {_summarize_payload_shape(timeline_payload)}"
                )

            page_signature = _build_page_signature(tweets)
            if page_signature and page_signature in seen_page_signatures:
                if session and run:
                    page_index = run.pages_fetched + 1
                    _store_raw_artifact(
                        session=session,
                        ingestion_run_id=run.id,
                        artifact_type="user_last_tweets_page_duplicate",
                        payload_json=_wrap_raw_payload(
                            endpoint="/twitter/user/last_tweets",
                            params=_build_last_tweets_request_params(
                                username=request.username,
                                include_replies=request.include_replies,
                                cursor=next_cursor_to_request,
                                page_index=page_index,
                            ),
                            response_payload=timeline_payload,
                        ),
                        record_count_estimate=len(tweets),
                    )
                    artifacts_created += 1

                raise RuntimeError(
                    "twitterapi.io returned a duplicate last_tweets page while paginating. "
                    "Aborting to avoid looping on the same tweet set."
                )

            pages_fetched += 1
            tweets_returned += len(tweets)
            next_cursor = timeline_payload.get("next_cursor")
            has_next_page = bool(timeline_payload.get("has_next_page"))
            if page_signature:
                seen_page_signatures.add(page_signature)

            if session and run:
                page_index = run.pages_fetched + 1
                _store_raw_artifact(
                    session=session,
                    ingestion_run_id=run.id,
                    artifact_type="user_last_tweets_page",
                    payload_json=_wrap_raw_payload(
                        endpoint="/twitter/user/last_tweets",
                        params=_build_last_tweets_request_params(
                            username=request.username,
                            include_replies=request.include_replies,
                            cursor=next_cursor_to_request,
                            page_index=page_index,
                        ),
                        response_payload=timeline_payload,
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
        status = "completed"
        notes = (
            "Raw archive completed successfully. "
            f"Fetched {pages_fetched} last_tweets pages and archived {tweets_returned} tweets."
        )

        if session and run:
            run.completed_at = completed_at
            run.status = status
            run.last_cursor = None
            run.notes = notes
            session.commit()

        return IngestionSummary(
            run_id=run_id,
            username=request.username,
            resolved_user_platform_id=resolved_user_platform_id,
            started_at=started_at,
            completed_at=completed_at,
            import_type=request.import_type,
            pages_fetched=pages_fetched,
            artifacts_created=artifacts_created,
            tweets_returned=tweets_returned,
            status=status,
            resumed_from_run_id=resumed_from_run_id,
            last_cursor=None,
            dry_run=request.dry_run,
            notes=notes,
        )
    except Exception as exc:
        completed_at = datetime.now(UTC)
        status = "failed"
        notes = f"Raw archive failed: {exc}"
        if session and run:
            session.rollback()
            run.status = status
            run.completed_at = completed_at
            run.last_cursor = next_cursor_to_request or run.last_cursor
            run.pages_fetched = pages_fetched
            run.raw_tweets_fetched = tweets_returned
            run.notes = notes
            session.commit()

        return IngestionSummary(
            run_id=run_id,
            username=request.username,
            resolved_user_platform_id=resolved_user_platform_id,
            started_at=started_at,
            completed_at=completed_at,
            import_type=request.import_type,
            pages_fetched=pages_fetched,
            artifacts_created=artifacts_created,
            tweets_returned=tweets_returned,
            status=status,
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
    request: IngestionRequest,
    started_at: datetime,
) -> IngestionRun:
    run = IngestionRun(
        source_name="twitterapi.io",
        endpoint_name="user_last_tweets_raw_archive",
        target_user_platform_id=None,
        import_type=request.import_type,
        started_at=started_at,
        status="started",
        last_cursor="",
        pages_fetched=0,
        raw_tweets_fetched=0,
        notes=(
            f"username={request.username}; "
            f"include_replies={request.include_replies}; "
            "endpoint=/twitter/user/last_tweets; "
            "timeline_lookup=userName"
        ),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def _load_resumable_run(session: Session, run_id: int) -> IngestionRun:
    run = session.scalar(select(IngestionRun).where(IngestionRun.id == run_id))
    if run is None:
        raise RuntimeError(f"No ingestion run found for resume_run_id={run_id}.")
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


def _extract_required_string(
    payload: dict[str, Any],
    key: str,
    context: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value == "":
        raise RuntimeError(f"Missing required string '{key}' in {context}.")
    return value


def _build_last_tweets_request_params(
    *,
    username: str,
    include_replies: bool,
    cursor: str,
    page_index: int | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "userName": username,
        "includeReplies": include_replies,
    }
    if cursor:
        params["cursor"] = cursor
    if page_index is not None:
        params["pageIndex"] = page_index
    return params


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


def _extract_timeline_tweets(payload: dict[str, Any]) -> Any:
    tweets = payload.get("tweets")
    if isinstance(tweets, list):
        return tweets

    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        nested_tweets = data.get("tweets")
        if isinstance(nested_tweets, list):
            return nested_tweets

    return None


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
