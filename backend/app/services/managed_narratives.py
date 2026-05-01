from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import re

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.managed_author_view import ManagedAuthorView
from app.models.managed_narrative import ManagedNarrative
from app.models.tweet import Tweet
from app.models.tweet_narrative_match import TweetNarrativeMatch
from app.models.user import User


MANAGED_NARRATIVE_MODEL_KEY = "managed-narratives"
_NARRATIVE_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")
_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
_MENTION_PATTERN = re.compile(r"(?<!\w)@\w+")
_HASHTAG_PATTERN = re.compile(r"#(\w+)")
_TOKEN_PATTERN = re.compile(r"[a-z0-9$#₿']+")


@dataclass(slots=True)
class ManagedNarrativesRequest:
    view_name: str = "global-settings-narratives"


@dataclass(slots=True)
class CreateManagedNarrativeRequest:
    phrase: str
    name: str | None = None
    view_name: str = "global-settings-create-narrative"
    rebuild_outputs: bool = True


@dataclass(slots=True)
class UpdateManagedNarrativeRequest:
    narrative_id: int
    phrase: str
    name: str | None = None
    view_name: str = "global-settings-update-narrative"
    rebuild_outputs: bool = True


@dataclass(slots=True)
class SyncManagedNarrativeMatchesRequest:
    usernames: list[str] | None = None
    narrative_slugs: list[str] | None = None
    created_since: str | None = None
    overwrite_existing: bool = False
    tracked_only: bool = True
    published_only: bool = True
    dry_run: bool = False


@dataclass(slots=True)
class SyncManagedNarrativeMatchesSummary:
    usernames_requested: list[str]
    usernames_matched: list[str]
    tracked_only: bool
    published_only: bool
    narratives_considered: int
    narrative_slugs: list[str]
    tweets_considered: int
    tweets_with_matches: int
    match_rows_prepared: int
    match_rows_written: int
    dry_run: bool
    notes: str


def build_managed_narratives(
    request: ManagedNarrativesRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        narratives = list(
            session.scalars(
                select(ManagedNarrative).order_by(
                    func.lower(ManagedNarrative.name).asc(),
                    ManagedNarrative.id.asc(),
                )
            )
        )
        return {
            "view": request.view_name,
            "narratives": [_serialize_managed_narrative(narrative) for narrative in narratives],
        }
    finally:
        session.close()


def build_create_managed_narrative(
    request: CreateManagedNarrativeRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    normalized_phrase = normalize_managed_narrative_phrase(request.phrase)
    cleaned_name = _normalize_name(request.name or request.phrase)
    normalized_slug = _normalize_slug(cleaned_name or normalized_phrase)

    session = session_factory()
    try:
        existing = session.scalar(
            select(ManagedNarrative).where(
                or_(
                    ManagedNarrative.slug == normalized_slug,
                    func.lower(ManagedNarrative.name) == cleaned_name.lower(),
                    ManagedNarrative.phrase == normalized_phrase,
                )
            )
        )
        if existing is not None:
            raise RuntimeError(
                "A managed narrative already exists for this phrase, name, or slug."
            )

        narrative = ManagedNarrative(
            slug=normalized_slug,
            name=cleaned_name,
            phrase=normalized_phrase,
        )
        session.add(narrative)
        session.commit()
        session.refresh(narrative)
    finally:
        session.close()

    sync_summary = None
    snapshot_summary = None
    if request.rebuild_outputs:
        sync_summary = sync_managed_narrative_matches(
            SyncManagedNarrativeMatchesRequest(
                narrative_slugs=[narrative.slug],
                overwrite_existing=True,
            ),
            session_factory=session_factory,
        )
        from app.services.aggregate_narrative_view import rebuild_aggregate_narrative_snapshots

        snapshot_summary = rebuild_aggregate_narrative_snapshots(
            session_factory=session_factory
        )

    return {
        "view": request.view_name,
        "narrative": _serialize_managed_narrative(narrative),
        "sync_summary": asdict(sync_summary) if sync_summary is not None else None,
        "snapshot_summary": snapshot_summary,
    }


def build_update_managed_narrative(
    request: UpdateManagedNarrativeRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    normalized_phrase = normalize_managed_narrative_phrase(request.phrase)
    cleaned_name = _normalize_name(request.name or request.phrase)
    normalized_slug = _normalize_slug(cleaned_name or normalized_phrase)

    session = session_factory()
    try:
        narrative = session.scalar(
            select(ManagedNarrative).where(ManagedNarrative.id == request.narrative_id)
        )
        if narrative is None:
            raise RuntimeError(f"No managed narrative exists for id={request.narrative_id}.")

        existing = session.scalar(
            select(ManagedNarrative).where(
                ManagedNarrative.id != request.narrative_id,
                or_(
                    ManagedNarrative.slug == normalized_slug,
                    func.lower(ManagedNarrative.name) == cleaned_name.lower(),
                    ManagedNarrative.phrase == normalized_phrase,
                ),
            )
        )
        if existing is not None:
            raise RuntimeError(
                "Another managed narrative already exists for this phrase, name, or slug."
            )

        narrative.slug = normalized_slug
        narrative.name = cleaned_name
        narrative.phrase = normalized_phrase
        session.commit()
        session.refresh(narrative)
    finally:
        session.close()

    sync_summary = None
    snapshot_summary = None
    if request.rebuild_outputs:
        sync_summary = sync_managed_narrative_matches(
            SyncManagedNarrativeMatchesRequest(
                narrative_slugs=[narrative.slug],
                overwrite_existing=True,
            ),
            session_factory=session_factory,
        )
        from app.services.aggregate_narrative_view import rebuild_aggregate_narrative_snapshots

        snapshot_summary = rebuild_aggregate_narrative_snapshots(
            session_factory=session_factory
        )

    return {
        "view": request.view_name,
        "narrative": _serialize_managed_narrative(narrative),
        "sync_summary": asdict(sync_summary) if sync_summary is not None else None,
        "snapshot_summary": snapshot_summary,
    }


def sync_managed_narrative_matches(
    request: SyncManagedNarrativeMatchesRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> SyncManagedNarrativeMatchesSummary:
    normalized_usernames = _normalize_usernames(request.usernames)
    normalized_narrative_slugs = _normalize_narrative_slugs(request.narrative_slugs)
    created_since = (
        _parse_utc_datetime(request.created_since)
        if request.created_since is not None
        else None
    )

    session = session_factory()
    try:
        matched_users: list[tuple[int, str]] = []
        if normalized_usernames:
            matched_users = session.execute(
                select(User.id, User.username)
                .where(func.lower(User.username).in_(normalized_usernames))
                .order_by(func.lower(User.username).asc())
            ).all()
            if not matched_users:
                raise RuntimeError(
                    f"No canonical users found for usernames={sorted(normalized_usernames)!r}."
                )

        narratives = list(
            session.scalars(
                _build_managed_narrative_query(normalized_narrative_slugs)
            )
        )
        if not narratives:
            return SyncManagedNarrativeMatchesSummary(
                usernames_requested=sorted(normalized_usernames),
                usernames_matched=[username for _user_id, username in matched_users],
                tracked_only=request.tracked_only,
                published_only=request.published_only,
                narratives_considered=0,
                narrative_slugs=[],
                tweets_considered=0,
                tweets_with_matches=0,
                match_rows_prepared=0,
                match_rows_written=0,
                dry_run=request.dry_run,
                notes="No managed narratives are configured.",
            )

        narrative_ids = [narrative.id for narrative in narratives]
        matched_user_ids = [user_id for user_id, _username in matched_users]
        matched_usernames = [username for _user_id, username in matched_users]
        tweet_scope_query = _build_tweet_scope_query(
            matched_user_ids=matched_user_ids,
            tracked_only=request.tracked_only,
            published_only=request.published_only,
            created_since=created_since,
        )

        if request.overwrite_existing and not request.dry_run:
            session.execute(
                delete(TweetNarrativeMatch).where(
                    TweetNarrativeMatch.managed_narrative_id.in_(narrative_ids),
                    TweetNarrativeMatch.tweet_id.in_(tweet_scope_query.with_only_columns(Tweet.id)),
                )
            )
            session.commit()

        tweet_rows = session.execute(
            tweet_scope_query.with_only_columns(Tweet.id, Tweet.text)
            .order_by(Tweet.author_user_id.asc(), Tweet.created_at_platform.asc(), Tweet.id.asc())
        ).all()

        prepared_rows: list[dict[str, object]] = []
        tweets_with_matches = 0
        compiled_narratives = [
            {
                "id": narrative.id,
                "slug": narrative.slug,
                "phrase": narrative.phrase,
                "tokens": narrative_phrase_tokens(narrative.phrase),
            }
            for narrative in narratives
        ]

        for tweet_id, tweet_text in tweet_rows:
            tweet_tokens = tokenize_text_for_narrative_matching(tweet_text)
            matched_any = False
            for compiled in compiled_narratives:
                if not tweet_tokens or not _tweet_contains_phrase_tokens(
                    tweet_tokens,
                    compiled["tokens"],
                ):
                    continue
                prepared_rows.append(
                    {
                        "tweet_id": tweet_id,
                        "managed_narrative_id": compiled["id"],
                        "matched_phrase": compiled["phrase"],
                    }
                )
                matched_any = True
            if matched_any:
                tweets_with_matches += 1

        if request.dry_run:
            return SyncManagedNarrativeMatchesSummary(
                usernames_requested=sorted(normalized_usernames),
                usernames_matched=matched_usernames,
                tracked_only=request.tracked_only,
                published_only=request.published_only,
                narratives_considered=len(compiled_narratives),
                narrative_slugs=[str(item["slug"]) for item in compiled_narratives],
                tweets_considered=len(tweet_rows),
                tweets_with_matches=tweets_with_matches,
                match_rows_prepared=len(prepared_rows),
                match_rows_written=0,
                dry_run=True,
                notes="Dry run completed. No narrative match rows were written.",
            )

        for chunk in _chunked(prepared_rows, size=2000):
            if not chunk:
                continue
            stmt = insert(TweetNarrativeMatch).values(chunk)
            session.execute(
                stmt.on_conflict_do_nothing(
                    constraint="uq_tweet_narrative_matches_tweet_id_managed_narrative_id"
                )
            )

        session.commit()

        rows_written = session.scalar(
            select(func.count())
            .select_from(TweetNarrativeMatch)
            .join(Tweet, Tweet.id == TweetNarrativeMatch.tweet_id)
            .where(
                TweetNarrativeMatch.managed_narrative_id.in_(narrative_ids),
                Tweet.id.in_(_build_tweet_scope_query(
                    matched_user_ids=matched_user_ids,
                    tracked_only=request.tracked_only,
                    published_only=request.published_only,
                    created_since=created_since,
                ).with_only_columns(Tweet.id)),
            )
        ) or 0

        return SyncManagedNarrativeMatchesSummary(
            usernames_requested=sorted(normalized_usernames),
            usernames_matched=matched_usernames,
            tracked_only=request.tracked_only,
            published_only=request.published_only,
            narratives_considered=len(compiled_narratives),
            narrative_slugs=[str(item["slug"]) for item in compiled_narratives],
            tweets_considered=len(tweet_rows),
            tweets_with_matches=tweets_with_matches,
            match_rows_prepared=len(prepared_rows),
            match_rows_written=int(rows_written),
            dry_run=False,
            notes="Managed narrative match sync completed.",
        )
    finally:
        session.close()


def narrative_phrase_tokens(value: str) -> tuple[str, ...]:
    normalized_phrase = normalize_managed_narrative_phrase(value)
    tokens = tuple(normalized_phrase.split())
    if not tokens:
        raise RuntimeError("Managed narrative phrase cannot be empty after normalization.")
    return tokens


def normalize_managed_narrative_phrase(value: str) -> str:
    tokens = tokenize_text_for_narrative_matching(value)
    normalized = " ".join(tokens)
    if not normalized:
        raise RuntimeError("Managed narrative phrase cannot be empty.")
    if len(normalized) > 255:
        raise RuntimeError("Managed narrative phrase cannot exceed 255 characters.")
    return normalized


def tokenize_text_for_narrative_matching(text: str | None) -> list[str]:
    if not text:
        return []

    normalized = _URL_PATTERN.sub(" ", text)
    normalized = _MENTION_PATTERN.sub(" ", normalized)
    normalized = normalized.replace("₿", " bitcoin ")
    normalized = _HASHTAG_PATTERN.sub(r"\1", normalized)
    normalized = normalized.lower()

    tokens: list[str] = []
    for raw_token in _TOKEN_PATTERN.findall(normalized):
        token = raw_token.strip("'")
        token = token.lstrip("$#")
        if not token:
            continue
        tokens.append(token)
    return tokens


def _build_managed_narrative_query(narrative_slugs: set[str]) -> object:
    query = select(ManagedNarrative).order_by(
        func.lower(ManagedNarrative.name).asc(),
        ManagedNarrative.id.asc(),
    )
    if narrative_slugs:
        query = query.where(ManagedNarrative.slug.in_(narrative_slugs))
    return query


def _build_tweet_scope_query(
    *,
    matched_user_ids: list[int],
    tracked_only: bool,
    published_only: bool,
    created_since: datetime | None,
) -> object:
    query = select(Tweet).join(User, User.id == Tweet.author_user_id)
    if tracked_only or published_only:
        query = query.join(ManagedAuthorView, ManagedAuthorView.user_id == User.id)
        if tracked_only:
            query = query.where(ManagedAuthorView.is_tracked.is_(True))
        if published_only:
            query = query.where(ManagedAuthorView.published.is_(True))
    if matched_user_ids:
        query = query.where(Tweet.author_user_id.in_(matched_user_ids))
    if created_since is not None:
        query = query.where(Tweet.created_at_platform >= created_since)
    return query


def _parse_utc_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).astimezone(UTC)


def _serialize_managed_narrative(narrative: ManagedNarrative) -> dict[str, object]:
    return {
        "id": int(narrative.id),
        "slug": narrative.slug,
        "name": narrative.name,
        "phrase": narrative.phrase,
    }


def _tweet_contains_phrase_tokens(tweet_tokens: list[str], phrase_tokens: tuple[str, ...]) -> bool:
    if not tweet_tokens or not phrase_tokens or len(tweet_tokens) < len(phrase_tokens):
        return False

    phrase_length = len(phrase_tokens)
    for index in range(0, len(tweet_tokens) - phrase_length + 1):
        if tuple(tweet_tokens[index : index + phrase_length]) == phrase_tokens:
            return True
    return False


def _normalize_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise RuntimeError("Managed narrative name cannot be empty.")
    if len(cleaned) > 255:
        raise RuntimeError("Managed narrative name cannot exceed 255 characters.")
    return cleaned


def _normalize_slug(value: str) -> str:
    lowered = value.strip().lower()
    slug = _NARRATIVE_SLUG_PATTERN.sub("-", lowered).strip("-")
    if not slug:
        raise RuntimeError("Managed narrative slug cannot be empty.")
    if len(slug) > 128:
        raise RuntimeError("Managed narrative slug cannot exceed 128 characters.")
    return slug


def _normalize_usernames(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    return {
        username.strip().lower()
        for username in values
        if username is not None and username.strip()
    }


def _normalize_narrative_slugs(values: list[str] | None) -> set[str]:
    if not values:
        return set()
    return {
        _normalize_slug(value)
        for value in values
        if value is not None and value.strip()
    }


def _chunked(values: list[dict[str, object]], *, size: int) -> list[list[dict[str, object]]]:
    return [values[index : index + size] for index in range(0, len(values), size)]
