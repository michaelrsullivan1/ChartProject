from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.tweet import Tweet
from app.models.tweet_keyword import TweetKeyword
from app.models.user import User


DEFAULT_KEYWORD_EXTRACTOR_KEY = "exact-ngram"
DEFAULT_KEYWORD_EXTRACTOR_VERSION = "v1"
DEFAULT_KEYWORD_TYPE = "exact_ngram"
DEFAULT_KEYWORD_ANALYSIS_START = "2020-08-01T00:00:00Z"
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
MENTION_PATTERN = re.compile(r"(?<!\w)@\w+")
HASHTAG_PATTERN = re.compile(r"#(\w+)")
WHITESPACE_PATTERN = re.compile(r"\s+")
TOKEN_PATTERN = re.compile(r"[a-z0-9$#₿']+")
STOPWORDS = {
    "again",
    "a",
    "all",
    "also",
    "amp",
    "an",
    "and",
    "are",
    "as",
    "at",
    "any",
    "be",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "here",
    "him",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "just",
    "like",
    "me",
    "more",
    "most",
    "my",
    "new",
    "need",
    "no",
    "not",
    "now",
    "of",
    "only",
    "on",
    "or",
    "our",
    "out",
    "she",
    "same",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "too",
    "up",
    "us",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "would",
    "yes",
    "you",
    "your",
}
GENERIC_TOKEN_DENYLIST = {
    "amp",
    "people",
    "time",
    "world",
}
GENERIC_PHRASE_DENYLIST = {
    "a bitcoin",
    "bitcoin and",
    "bitcoin as",
    "bitcoin is",
    "for bitcoin",
    "going to",
    "in bitcoin",
    "is digital",
    "of bitcoin",
    "on bitcoin",
    "per bitcoin",
    "the bitcoin",
    "the first",
    "the future",
    "the world",
}


@dataclass(slots=True)
class ExtractTweetKeywordsRequest:
    usernames: list[str]
    analysis_start: str = DEFAULT_KEYWORD_ANALYSIS_START
    extractor_key: str = DEFAULT_KEYWORD_EXTRACTOR_KEY
    extractor_version: str = DEFAULT_KEYWORD_EXTRACTOR_VERSION
    overwrite_existing: bool = False
    dry_run: bool = False


@dataclass(slots=True)
class ExtractTweetKeywordsSummary:
    usernames_requested: list[str]
    usernames_matched: list[str]
    extractor_key: str
    extractor_version: str
    tweets_considered: int
    tweets_with_keywords: int
    keyword_rows_prepared: int
    keyword_rows_written: int
    dry_run: bool
    notes: str


def extract_tweet_keywords(
    request: ExtractTweetKeywordsRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> ExtractTweetKeywordsSummary:
    normalized_usernames = _normalize_usernames(request.usernames)
    if not normalized_usernames:
        raise RuntimeError("extract_tweet_keywords requires at least one username.")

    analysis_start = _parse_utc_datetime(request.analysis_start)
    session = session_factory()
    try:
        matched_users = session.execute(
            select(User.id, User.username)
            .where(func.lower(User.username).in_(normalized_usernames))
            .order_by(User.username.asc())
        ).all()
        if not matched_users:
            raise RuntimeError(
                f"No canonical users found for usernames={sorted(normalized_usernames)!r}."
            )

        matched_user_ids = [user_id for user_id, _ in matched_users]
        matched_usernames = [username for _, username in matched_users]

        if request.overwrite_existing and not request.dry_run:
            session.execute(
                delete(TweetKeyword).where(
                    TweetKeyword.extractor_key == request.extractor_key,
                    TweetKeyword.extractor_version == request.extractor_version,
                    TweetKeyword.tweet_id.in_(
                        select(Tweet.id).where(
                            Tweet.author_user_id.in_(matched_user_ids),
                            Tweet.created_at_platform >= analysis_start,
                        )
                    ),
                )
            )
            session.commit()

        tweet_rows = session.execute(
            select(Tweet.id, Tweet.text)
            .where(
                Tweet.author_user_id.in_(matched_user_ids),
                Tweet.created_at_platform >= analysis_start,
            )
            .order_by(Tweet.author_user_id.asc(), Tweet.created_at_platform.asc(), Tweet.id.asc())
        ).all()

        prepared_rows: list[dict[str, object]] = []
        tweets_with_keywords = 0
        for tweet_id, text in tweet_rows:
            keywords = extract_keywords_from_text(text)
            if keywords:
                tweets_with_keywords += 1
            for keyword in keywords:
                prepared_rows.append(
                    {
                        "tweet_id": tweet_id,
                        "keyword": keyword,
                        "normalized_keyword": keyword,
                        "keyword_length": len(keyword.split()),
                        "keyword_type": DEFAULT_KEYWORD_TYPE,
                        "extractor_key": request.extractor_key,
                        "extractor_version": request.extractor_version,
                    }
                )

        if request.dry_run:
            return ExtractTweetKeywordsSummary(
                usernames_requested=sorted(normalized_usernames),
                usernames_matched=matched_usernames,
                extractor_key=request.extractor_key,
                extractor_version=request.extractor_version,
                tweets_considered=len(tweet_rows),
                tweets_with_keywords=tweets_with_keywords,
                keyword_rows_prepared=len(prepared_rows),
                keyword_rows_written=0,
                dry_run=True,
                notes="Dry run completed. No keyword rows were written.",
            )

        for chunk in _chunked(prepared_rows, size=2000):
            if not chunk:
                continue
            stmt = insert(TweetKeyword).values(chunk)
            session.execute(
                stmt.on_conflict_do_nothing(
                    constraint="uq_tweet_keywords_tweet_keyword_extractor"
                )
            )

        session.commit()
        rows_written = session.scalar(
            select(func.count())
            .select_from(TweetKeyword)
            .join(Tweet, Tweet.id == TweetKeyword.tweet_id)
            .where(
                Tweet.author_user_id.in_(matched_user_ids),
                Tweet.created_at_platform >= analysis_start,
                TweetKeyword.extractor_key == request.extractor_key,
                TweetKeyword.extractor_version == request.extractor_version,
            )
        ) or 0

        return ExtractTweetKeywordsSummary(
            usernames_requested=sorted(normalized_usernames),
            usernames_matched=matched_usernames,
            extractor_key=request.extractor_key,
            extractor_version=request.extractor_version,
            tweets_considered=len(tweet_rows),
            tweets_with_keywords=tweets_with_keywords,
            keyword_rows_prepared=len(prepared_rows),
            keyword_rows_written=rows_written,
            dry_run=False,
            notes="Keyword extraction completed.",
        )
    finally:
        session.close()


def extract_keywords_from_text(text: str | None) -> list[str]:
    if not text:
        return []

    tokens = _tokenize_text(text)
    if not tokens:
        return []

    phrases: set[str] = set()
    for size in (1, 2, 3):
        if len(tokens) < size:
            continue
        for start in range(0, len(tokens) - size + 1):
            parts = tokens[start : start + size]
            phrase = " ".join(parts)
            if not _should_keep_phrase(parts, phrase):
                continue
            phrases.add(phrase)
    return sorted(phrases)


def _tokenize_text(text: str) -> list[str]:
    normalized = URL_PATTERN.sub(" ", text)
    normalized = MENTION_PATTERN.sub(" ", normalized)
    normalized = normalized.replace("₿", " bitcoin ")
    normalized = HASHTAG_PATTERN.sub(r"\1", normalized)
    normalized = normalized.lower()
    tokens: list[str] = []
    for raw_token in TOKEN_PATTERN.findall(normalized):
        token = raw_token.strip("'")
        token = token.lstrip("$#")
        if not token or token.isdigit():
            continue
        tokens.append(token)
    return tokens


def _should_keep_phrase(parts: list[str], phrase: str) -> bool:
    if phrase in GENERIC_PHRASE_DENYLIST:
        return False

    non_stopword_count = sum(part not in STOPWORDS for part in parts)
    if non_stopword_count == 0:
        return False

    if len(parts) == 1:
        token = parts[0]
        if token in STOPWORDS:
            return False
        if token in GENERIC_TOKEN_DENYLIST:
            return False
        if len(token) < 2:
            return False
        return True

    if parts[0] in STOPWORDS or parts[-1] in STOPWORDS:
        return False

    if sum(part in STOPWORDS for part in parts) > 1:
        return False

    if any(len(part) < 2 for part in parts if part not in STOPWORDS):
        return False

    return True


def _normalize_usernames(usernames: list[str]) -> list[str]:
    return sorted({username.strip().lower() for username in usernames if username.strip()})


def _parse_utc_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"Invalid analysis_start datetime {value!r}.") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)

    return parsed.astimezone(UTC)


def _chunked(values: list[dict[str, object]], *, size: int) -> list[list[dict[str, object]]]:
    return [values[index : index + size] for index in range(0, len(values), size)]
