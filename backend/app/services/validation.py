from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.tweet import Tweet
from app.models.tweet_reference import TweetReference
from app.models.user import User
from app.services.normalization import (
    TweetSnapshot,
    UserSnapshot,
    _build_archived_artifact_query,
    _build_tweet_snapshot,
    _build_user_snapshot_from_tweet_author,
    _build_user_snapshot_from_user_info,
    _can_build_user_snapshot,
    _extract_search_tweets,
    _extract_user_info_payload,
    _max_datetime,
    _merge_tweet_snapshot,
    _merge_user_snapshot,
    _min_datetime,
    _normalize_username,
    _parse_platform_datetime,
    _coerce_string,
)


@dataclass(slots=True)
class ValidateArchivedUserRequest:
    username: str
    sample_limit: int = 10


@dataclass(slots=True)
class ValidationIssue:
    check: str
    severity: str
    message: str
    samples: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ValidateArchivedUserSummary:
    username: str
    status: str
    target_platform_user_id: str
    raw_user_artifacts_matched: int
    raw_tweet_artifacts_scanned: int
    expected_user_count: int
    normalized_user_count: int
    missing_expected_user_count: int
    raw_distinct_tweets: int
    normalized_tweet_count: int
    missing_normalized_tweet_count: int
    extra_normalized_tweet_count: int
    duplicate_canonical_tweet_id_count: int
    raw_first_tweet_at: datetime | None
    raw_last_tweet_at: datetime | None
    normalized_first_tweet_at: datetime | None
    normalized_last_tweet_at: datetime | None
    raw_conversation_count: int
    normalized_conversation_count: int
    raw_reply_count: int
    normalized_reply_field_count: int
    normalized_reply_reference_count: int
    raw_quote_count: int
    normalized_quote_field_count: int
    normalized_quote_reference_count: int
    missing_reference_count: int
    extra_reference_count: int
    issues: list[ValidationIssue] = field(default_factory=list)
    notes: str = ""


def validate_archived_user(
    request: ValidateArchivedUserRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> ValidateArchivedUserSummary:
    username_key = request.username.strip().casefold()
    if not username_key:
        raise RuntimeError("validate_archived_user requires a non-empty username.")

    session = session_factory()
    try:
        (
            expected_users,
            expected_tweets,
            target_platform_user_id,
            raw_user_artifacts_matched,
            raw_tweet_artifacts_scanned,
            raw_first_tweet_at,
            raw_last_tweet_at,
        ) = _build_expected_dataset(session, username_key=username_key)

        expected_user_ids = set(expected_users.keys())
        expected_tweet_ids = set(expected_tweets.keys())
        expected_reference_tuples = _build_expected_reference_tuples(expected_tweets)
        raw_conversation_count = sum(
            1
            for snapshot in expected_tweets.values()
            if snapshot.conversation_id_platform is not None
        )
        raw_reply_count = sum(
            1
            for snapshot in expected_tweets.values()
            if snapshot.in_reply_to_platform_tweet_id is not None
        )
        raw_quote_count = sum(
            1
            for snapshot in expected_tweets.values()
            if snapshot.quoted_platform_tweet_id is not None
        )

        normalized_target_user_rows = session.execute(
            select(User.id, User.platform_user_id).where(User.platform_user_id == target_platform_user_id)
        ).all()
        target_user_id = normalized_target_user_rows[0][0] if normalized_target_user_rows else None

        normalized_expected_user_ids = set(
            session.scalars(
                select(User.platform_user_id).where(User.platform_user_id.in_(expected_user_ids))
            ).all()
        )
        missing_expected_user_ids = expected_user_ids - normalized_expected_user_ids

        normalized_tweets = session.execute(
            select(
                Tweet.platform_tweet_id,
                Tweet.created_at_platform,
                Tweet.conversation_id_platform,
                Tweet.in_reply_to_platform_tweet_id,
                Tweet.quoted_platform_tweet_id,
            ).where(Tweet.author_user_id == target_user_id)
        ).all() if target_user_id is not None else []

        normalized_tweet_ids = {row[0] for row in normalized_tweets}
        missing_normalized_tweet_ids = expected_tweet_ids - normalized_tweet_ids
        extra_normalized_tweet_ids = normalized_tweet_ids - expected_tweet_ids

        normalized_first_tweet_at = min((row[1] for row in normalized_tweets), default=None)
        normalized_last_tweet_at = max((row[1] for row in normalized_tweets), default=None)
        normalized_conversation_count = sum(1 for row in normalized_tweets if row[2] is not None)
        normalized_reply_field_count = sum(1 for row in normalized_tweets if row[3] is not None)
        normalized_quote_field_count = sum(1 for row in normalized_tweets if row[4] is not None)

        normalized_reference_rows = session.execute(
            select(
                Tweet.platform_tweet_id,
                TweetReference.reference_type,
                TweetReference.referenced_tweet_platform_id,
                TweetReference.referenced_user_platform_id,
            )
            .join(TweetReference, TweetReference.tweet_id == Tweet.id)
            .where(Tweet.author_user_id == target_user_id)
        ).all() if target_user_id is not None else []
        normalized_reference_tuples = {
            (
                platform_tweet_id,
                reference_type,
                referenced_tweet_platform_id,
                referenced_user_platform_id or "",
            )
            for (
                platform_tweet_id,
                reference_type,
                referenced_tweet_platform_id,
                referenced_user_platform_id,
            ) in normalized_reference_rows
        }
        missing_reference_tuples = expected_reference_tuples - normalized_reference_tuples
        extra_reference_tuples = normalized_reference_tuples - expected_reference_tuples
        normalized_reply_reference_count = sum(
            1 for row in normalized_reference_rows if row[1] == "replied_to"
        )
        normalized_quote_reference_count = sum(
            1 for row in normalized_reference_rows if row[1] == "quoted"
        )

        duplicate_canonical_tweet_id_count = (
            session.execute(
                select(func.count())
                .select_from(
                    select(Tweet.platform_tweet_id)
                    .where(Tweet.author_user_id == target_user_id)
                    .group_by(Tweet.platform_tweet_id)
                    .having(func.count(Tweet.id) > 1)
                    .subquery()
                )
            ).scalar_one()
            if target_user_id is not None
            else 0
        )

        issues: list[ValidationIssue] = []
        if raw_user_artifacts_matched == 0:
            issues.append(
                ValidationIssue(
                    check="raw user info coverage",
                    severity="warn",
                    message=(
                        "No archived user_info artifacts matched this username. Validation relied only "
                        "on embedded author data from tweet payloads."
                    ),
                )
            )
        if len(normalized_target_user_rows) != 1:
            issues.append(
                ValidationIssue(
                    check="target user row",
                    severity="fail",
                    message=(
                        f"Expected exactly 1 canonical user row for platform_user_id="
                        f"{target_platform_user_id}, found {len(normalized_target_user_rows)}."
                    ),
                )
            )
        if missing_expected_user_ids:
            issues.append(
                ValidationIssue(
                    check="user coverage",
                    severity="fail",
                    message=(
                        f"Canonical users are missing {len(missing_expected_user_ids)} platform user ids "
                        "that appear in archived raw payloads."
                    ),
                    samples=sorted(missing_expected_user_ids)[: request.sample_limit],
                )
            )
        if missing_normalized_tweet_ids:
            issues.append(
                ValidationIssue(
                    check="tweet coverage",
                    severity="fail",
                    message=(
                        f"Canonical tweets are missing {len(missing_normalized_tweet_ids)} raw tweet ids "
                        "for the target user."
                    ),
                    samples=sorted(missing_normalized_tweet_ids)[: request.sample_limit],
                )
            )
        if extra_normalized_tweet_ids:
            issues.append(
                ValidationIssue(
                    check="tweet extras",
                    severity="fail",
                    message=(
                        f"Canonical tweets include {len(extra_normalized_tweet_ids)} ids for the target "
                        "user that were not present in the archived raw corpus."
                    ),
                    samples=sorted(extra_normalized_tweet_ids)[: request.sample_limit],
                )
            )
        if raw_first_tweet_at != normalized_first_tweet_at or raw_last_tweet_at != normalized_last_tweet_at:
            issues.append(
                ValidationIssue(
                    check="date range",
                    severity="fail",
                    message=(
                        "Canonical min/max tweet timestamps do not match the archived raw corpus."
                    ),
                    samples=[
                        f"raw_first={raw_first_tweet_at}",
                        f"normalized_first={normalized_first_tweet_at}",
                        f"raw_last={raw_last_tweet_at}",
                        f"normalized_last={normalized_last_tweet_at}",
                    ],
                )
            )
        if duplicate_canonical_tweet_id_count != 0:
            issues.append(
                ValidationIssue(
                    check="duplicate canonical tweets",
                    severity="fail",
                    message=(
                        f"Found {duplicate_canonical_tweet_id_count} duplicate canonical tweet id groups "
                        "for the target user."
                    ),
                )
            )
        if raw_conversation_count != normalized_conversation_count:
            issues.append(
                ValidationIssue(
                    check="conversation linkage",
                    severity="fail",
                    message=(
                        f"Raw conversation count={raw_conversation_count} but canonical "
                        f"conversation count={normalized_conversation_count}."
                    ),
                )
            )
        if raw_reply_count != normalized_reply_field_count or raw_reply_count != normalized_reply_reference_count:
            issues.append(
                ValidationIssue(
                    check="reply linkage",
                    severity="fail",
                    message=(
                        f"Raw reply count={raw_reply_count}, canonical reply field count="
                        f"{normalized_reply_field_count}, canonical reply reference count="
                        f"{normalized_reply_reference_count}."
                    ),
                )
            )
        if raw_quote_count != normalized_quote_field_count or raw_quote_count != normalized_quote_reference_count:
            issues.append(
                ValidationIssue(
                    check="quote linkage",
                    severity="fail",
                    message=(
                        f"Raw quote count={raw_quote_count}, canonical quote field count="
                        f"{normalized_quote_field_count}, canonical quote reference count="
                        f"{normalized_quote_reference_count}."
                    ),
                )
            )
        if missing_reference_tuples:
            issues.append(
                ValidationIssue(
                    check="reference coverage",
                    severity="fail",
                    message=(
                        f"Canonical tweet_references are missing {len(missing_reference_tuples)} "
                        "reference tuples present in the raw corpus."
                    ),
                    samples=_format_reference_samples(
                        sorted(missing_reference_tuples)[: request.sample_limit]
                    ),
                )
            )
        if extra_reference_tuples:
            issues.append(
                ValidationIssue(
                    check="reference extras",
                    severity="fail",
                    message=(
                        f"Canonical tweet_references include {len(extra_reference_tuples)} tuples not "
                        "present in the raw corpus."
                    ),
                    samples=_format_reference_samples(
                        sorted(extra_reference_tuples)[: request.sample_limit]
                    ),
                )
            )

        status = "PASS"
        if any(issue.severity == "fail" for issue in issues):
            status = "FAIL"
        elif issues:
            status = "WARN"

        notes = (
            f"Validated {len(expected_tweet_ids)} raw distinct tweets for {request.username} against "
            "canonical users, tweets, and tweet references."
        )

        return ValidateArchivedUserSummary(
            username=request.username,
            status=status,
            target_platform_user_id=target_platform_user_id,
            raw_user_artifacts_matched=raw_user_artifacts_matched,
            raw_tweet_artifacts_scanned=raw_tweet_artifacts_scanned,
            expected_user_count=len(expected_user_ids),
            normalized_user_count=len(normalized_expected_user_ids),
            missing_expected_user_count=len(missing_expected_user_ids),
            raw_distinct_tweets=len(expected_tweet_ids),
            normalized_tweet_count=len(normalized_tweet_ids),
            missing_normalized_tweet_count=len(missing_normalized_tweet_ids),
            extra_normalized_tweet_count=len(extra_normalized_tweet_ids),
            duplicate_canonical_tweet_id_count=duplicate_canonical_tweet_id_count,
            raw_first_tweet_at=raw_first_tweet_at,
            raw_last_tweet_at=raw_last_tweet_at,
            normalized_first_tweet_at=normalized_first_tweet_at,
            normalized_last_tweet_at=normalized_last_tweet_at,
            raw_conversation_count=raw_conversation_count,
            normalized_conversation_count=normalized_conversation_count,
            raw_reply_count=raw_reply_count,
            normalized_reply_field_count=normalized_reply_field_count,
            normalized_reply_reference_count=normalized_reply_reference_count,
            raw_quote_count=raw_quote_count,
            normalized_quote_field_count=normalized_quote_field_count,
            normalized_quote_reference_count=normalized_quote_reference_count,
            missing_reference_count=len(missing_reference_tuples),
            extra_reference_count=len(extra_reference_tuples),
            issues=issues,
            notes=notes,
        )
    finally:
        session.close()


def render_validation_report(summary: ValidateArchivedUserSummary) -> str:
    lines = [
        f"Validation report for {summary.username}",
        f"status: {summary.status}",
        "",
        "coverage:",
        f"- raw user artifacts matched: {summary.raw_user_artifacts_matched}",
        f"- raw tweet artifacts scanned: {summary.raw_tweet_artifacts_scanned}",
        f"- expected users from raw: {summary.expected_user_count}",
        f"- normalized expected users present: {summary.normalized_user_count}",
        f"- raw distinct tweets: {summary.raw_distinct_tweets}",
        f"- normalized tweets: {summary.normalized_tweet_count}",
        f"- missing normalized tweet ids: {summary.missing_normalized_tweet_count}",
        f"- extra normalized tweet ids: {summary.extra_normalized_tweet_count}",
        "",
        "dates:",
        f"- raw first tweet: {summary.raw_first_tweet_at}",
        f"- normalized first tweet: {summary.normalized_first_tweet_at}",
        f"- raw last tweet: {summary.raw_last_tweet_at}",
        f"- normalized last tweet: {summary.normalized_last_tweet_at}",
        "",
        "linkage:",
        f"- raw conversations: {summary.raw_conversation_count}",
        f"- normalized conversations: {summary.normalized_conversation_count}",
        f"- raw replies: {summary.raw_reply_count}",
        f"- normalized reply fields: {summary.normalized_reply_field_count}",
        f"- normalized reply references: {summary.normalized_reply_reference_count}",
        f"- raw quotes: {summary.raw_quote_count}",
        f"- normalized quote fields: {summary.normalized_quote_field_count}",
        f"- normalized quote references: {summary.normalized_quote_reference_count}",
        f"- missing reference tuples: {summary.missing_reference_count}",
        f"- extra reference tuples: {summary.extra_reference_count}",
        "",
        "integrity:",
        f"- duplicate canonical tweet id groups: {summary.duplicate_canonical_tweet_id_count}",
        f"- missing expected users: {summary.missing_expected_user_count}",
        "",
        f"notes: {summary.notes}",
    ]
    if summary.issues:
        lines.extend(["", "issues:"])
        for issue in summary.issues:
            lines.append(f"- [{issue.severity}] {issue.check}: {issue.message}")
            for sample in issue.samples:
                lines.append(f"  sample: {sample}")
    else:
        lines.extend(["", "issues:", "- none"])
    return "\n".join(lines)


def _build_expected_dataset(
    session: Session,
    *,
    username_key: str,
) -> tuple[
    dict[str, UserSnapshot],
    dict[str, TweetSnapshot],
    str,
    int,
    int,
    datetime | None,
    datetime | None,
]:
    artifacts = session.execute(
        _build_archived_artifact_query(session, username_key=username_key)
    ).all()

    expected_users: dict[str, UserSnapshot] = {}
    expected_tweets: dict[str, TweetSnapshot] = {}
    raw_user_artifacts_matched = 0
    raw_tweet_artifacts_scanned = 0
    raw_first_tweet_at: datetime | None = None
    raw_last_tweet_at: datetime | None = None
    target_platform_user_id: str | None = None

    for artifact, _run in artifacts:
        if artifact.artifact_type == "user_info":
            user_payload = _extract_user_info_payload(artifact.payload_json)
            if user_payload is None:
                continue
            if _normalize_username(_coerce_string(user_payload.get("userName"))) != username_key:
                continue

            raw_user_artifacts_matched += 1
            snapshot = _build_user_snapshot_from_user_info(
                user_payload,
                observed_at=artifact.created_at,
            )
            _merge_user_snapshot(expected_users, snapshot)
            target_platform_user_id = snapshot.platform_user_id
            continue

        tweets = _extract_search_tweets(artifact.payload_json)
        if tweets is None:
            continue

        raw_tweet_artifacts_scanned += 1
        for tweet_payload in tweets:
            author_payload = tweet_payload.get("author")
            if not isinstance(author_payload, dict):
                continue
            if _normalize_username(_coerce_string(author_payload.get("userName"))) != username_key:
                continue

            author_snapshot = _build_user_snapshot_from_tweet_author(
                author_payload,
                observed_at=artifact.created_at,
                tweet_created_at=_parse_platform_datetime(tweet_payload.get("createdAt")),
            )
            _merge_user_snapshot(expected_users, author_snapshot)
            target_platform_user_id = author_snapshot.platform_user_id

            quoted_tweet_payload = tweet_payload.get("quoted_tweet")
            if isinstance(quoted_tweet_payload, dict):
                quoted_author_payload = quoted_tweet_payload.get("author")
                if isinstance(quoted_author_payload, dict) and _can_build_user_snapshot(
                    quoted_author_payload
                ):
                    _merge_user_snapshot(
                        expected_users,
                        _build_user_snapshot_from_tweet_author(
                            quoted_author_payload,
                            observed_at=artifact.created_at,
                            tweet_created_at=_parse_platform_datetime(
                                quoted_tweet_payload.get("createdAt")
                            ),
                        ),
                    )

            snapshot = _build_tweet_snapshot(tweet_payload)
            expected_tweets[snapshot.platform_tweet_id] = _merge_tweet_snapshot(
                expected_tweets.get(snapshot.platform_tweet_id),
                snapshot,
            )
            raw_first_tweet_at = _min_datetime(raw_first_tweet_at, snapshot.created_at_platform)
            raw_last_tweet_at = _max_datetime(raw_last_tweet_at, snapshot.created_at_platform)

    if not expected_tweets:
        raise RuntimeError("No archived tweets matched the requested username.")
    if target_platform_user_id is None:
        raise RuntimeError("Unable to resolve target platform user id from archived raw artifacts.")

    return (
        expected_users,
        expected_tweets,
        target_platform_user_id,
        raw_user_artifacts_matched,
        raw_tweet_artifacts_scanned,
        raw_first_tweet_at,
        raw_last_tweet_at,
    )


def _build_expected_reference_tuples(
    expected_tweets: dict[str, TweetSnapshot],
) -> set[tuple[str, str, str, str]]:
    tuples: set[tuple[str, str, str, str]] = set()
    for snapshot in expected_tweets.values():
        for reference in snapshot.references:
            tuples.add(
                (
                    snapshot.platform_tweet_id,
                    reference.reference_type,
                    reference.referenced_tweet_platform_id,
                    reference.referenced_user_platform_id or "",
                )
            )
    return tuples


def _format_reference_samples(
    samples: list[tuple[str, str, str, str]],
) -> list[str]:
    return [
        (
            f"tweet_id={tweet_id} type={reference_type} referenced_tweet_id={referenced_tweet_id} "
            f"referenced_user_id={referenced_user_id or '<none>'}"
        )
        for tweet_id, reference_type, referenced_tweet_id, referenced_user_id in samples
    ]
