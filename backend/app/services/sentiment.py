from __future__ import annotations

from dataclasses import dataclass
import re

import torch
from sqlalchemy import and_, delete, func, select
from sqlalchemy.orm import Session, aliased, sessionmaker
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

from app.db.session import SessionLocal
from app.models.tweet import Tweet
from app.models.tweet_sentiment_score import TweetSentimentScore
from app.models.user import User


DEFAULT_SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
SCORABLE_LANGUAGE_CODES = {"en"}
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+")
MENTION_PATTERN = re.compile(r"(?<!\w)@\w+")
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(slots=True)
class ScoreTweetsSentimentRequest:
    usernames: list[str]
    model_key: str = DEFAULT_SENTIMENT_MODEL
    model_name: str = DEFAULT_SENTIMENT_MODEL
    batch_size: int = 32
    overwrite_existing: bool = False
    dry_run: bool = False


@dataclass(slots=True)
class ScoreTweetsSentimentSummary:
    usernames_requested: list[str]
    usernames_matched: list[str]
    model_key: str
    tweets_considered: int
    tweets_already_scored: int
    tweets_scored: int
    tweets_skipped: int
    tweets_truncated: int
    device: str
    dry_run: bool
    notes: str


@dataclass(slots=True)
class PreparedTweetText:
    tweet_id: int
    text: str
    input_char_count: int


@dataclass(slots=True)
class ScoredTweetText:
    label: str
    confidence: float
    negative_score: float
    neutral_score: float
    positive_score: float
    is_truncated: bool


@dataclass(slots=True)
class TweetCandidate:
    tweet_id: int
    text: str
    language: str | None


class RobertaTweetSentimentScorer:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.device = self._select_device()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.config = AutoConfig.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        self.max_length = _resolve_model_max_length(self.tokenizer, self.config)

    def score(self, prepared_texts: list[PreparedTweetText]) -> list[ScoredTweetText]:
        if not prepared_texts:
            return []

        untruncated_token_ids = self.tokenizer(
            [item.text for item in prepared_texts],
            add_special_tokens=True,
            truncation=False,
        )["input_ids"]
        encoded = self.tokenizer(
            [item.text for item in prepared_texts],
            add_special_tokens=True,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}

        with torch.no_grad():
            logits = self.model(**encoded).logits
            probabilities = torch.softmax(logits, dim=-1).cpu()

        scored_items: list[ScoredTweetText] = []
        for index, row in enumerate(probabilities):
            label = str(self.config.id2label[int(torch.argmax(row).item())]).lower()
            scored_items.append(
                ScoredTweetText(
                    label=label,
                    confidence=float(torch.max(row).item()),
                    negative_score=float(row[0].item()),
                    neutral_score=float(row[1].item()),
                    positive_score=float(row[2].item()),
                    is_truncated=len(untruncated_token_ids[index]) > self.max_length,
                )
            )
        return scored_items

    @staticmethod
    def _select_device() -> torch.device:
        if torch.backends.mps.is_available():
            return torch.device("mps")
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")


def score_tweets_sentiment(
    request: ScoreTweetsSentimentRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> ScoreTweetsSentimentSummary:
    normalized_usernames = _normalize_usernames(request.usernames)
    if not normalized_usernames:
        raise RuntimeError("score_tweets_sentiment requires at least one username.")
    if request.batch_size < 1:
        raise RuntimeError("score_tweets_sentiment requires batch_size >= 1.")

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

        user_id_to_username = {user_id: username for user_id, username in matched_users}
        matched_user_ids = list(user_id_to_username.keys())
        matched_usernames = [user_id_to_username[user_id] for user_id in matched_user_ids]

        already_scored = session.scalar(
            select(func.count())
            .select_from(TweetSentimentScore)
            .join(Tweet, Tweet.id == TweetSentimentScore.tweet_id)
            .where(
                Tweet.author_user_id.in_(matched_user_ids),
                TweetSentimentScore.model_key == request.model_key,
            )
        ) or 0

        if request.overwrite_existing and not request.dry_run:
            session.execute(
                delete(TweetSentimentScore).where(
                    TweetSentimentScore.model_key == request.model_key,
                    TweetSentimentScore.tweet_id.in_(
                        select(Tweet.id).where(Tweet.author_user_id.in_(matched_user_ids))
                    ),
                )
            )
            session.commit()
            already_scored = 0

        score_alias = aliased(TweetSentimentScore)
        pending_rows = session.execute(
            select(Tweet.id, Tweet.text, Tweet.language)
            .outerjoin(
                score_alias,
                and_(
                    score_alias.tweet_id == Tweet.id,
                    score_alias.model_key == request.model_key,
                ),
            )
            .where(
                Tweet.author_user_id.in_(matched_user_ids),
                score_alias.id.is_(None),
            )
            .order_by(Tweet.author_user_id.asc(), Tweet.created_at_platform.asc(), Tweet.id.asc())
        ).all()

        tweets_considered = len(pending_rows)
        if request.dry_run:
            tweets_skipped = 0
            for tweet_id, text, language in pending_rows:
                if _build_skip_reason(text, language) is not None:
                    tweets_skipped += 1
                    continue
                if _prepare_tweet_text(TweetCandidate(tweet_id=tweet_id, text=text, language=language)) is None:
                    tweets_skipped += 1
            tweets_scored = tweets_considered - tweets_skipped
            notes = (
                "Dry run completed. "
                f"Matched users={len(matched_usernames)}; pending tweets={tweets_considered}."
            )
            return ScoreTweetsSentimentSummary(
                usernames_requested=sorted(normalized_usernames),
                usernames_matched=matched_usernames,
                model_key=request.model_key,
                tweets_considered=tweets_considered,
                tweets_already_scored=already_scored,
                tweets_scored=tweets_scored,
                tweets_skipped=tweets_skipped,
                tweets_truncated=0,
                device="not-loaded",
                dry_run=True,
                notes=notes,
            )

        scorer: RobertaTweetSentimentScorer | None = None
        pending_batch: list[PreparedTweetText] = []
        score_rows: list[TweetSentimentScore] = []
        tweets_scored = 0
        tweets_skipped = 0
        tweets_truncated = 0

        for tweet_id, text, language in pending_rows:
            skip_reason = _build_skip_reason(text, language)
            if skip_reason is not None:
                score_rows.append(
                    TweetSentimentScore(
                        tweet_id=tweet_id,
                        model_key=request.model_key,
                        status="skipped",
                        skip_reason=skip_reason,
                        is_truncated=False,
                        input_char_count=len(text or ""),
                    )
                )
                tweets_skipped += 1
            else:
                prepared_text = _prepare_tweet_text(TweetCandidate(tweet_id=tweet_id, text=text, language=language))
                if prepared_text is None:
                    score_rows.append(
                        TweetSentimentScore(
                            tweet_id=tweet_id,
                            model_key=request.model_key,
                            status="skipped",
                            skip_reason="empty_after_preprocess",
                            is_truncated=False,
                            input_char_count=len(text or ""),
                        )
                    )
                    tweets_skipped += 1
                else:
                    pending_batch.append(prepared_text)

            if len(pending_batch) >= request.batch_size:
                if scorer is None:
                    scorer = RobertaTweetSentimentScorer(request.model_name)
                batch_scores = scorer.score(pending_batch)
                tweets_scored += _append_scored_rows(
                    score_rows,
                    request.model_key,
                    pending_batch,
                    batch_scores,
                )
                tweets_truncated += sum(1 for item in batch_scores if item.is_truncated)
                pending_batch = []
                session.add_all(score_rows)
                session.commit()
                score_rows = []

        if pending_batch:
            if scorer is None:
                scorer = RobertaTweetSentimentScorer(request.model_name)
            batch_scores = scorer.score(pending_batch)
            tweets_scored += _append_scored_rows(
                score_rows,
                request.model_key,
                pending_batch,
                batch_scores,
            )
            tweets_truncated += sum(1 for item in batch_scores if item.is_truncated)

        if score_rows:
            session.add_all(score_rows)
            session.commit()

        notes = (
            "Sentiment scoring completed. "
            f"Scored={tweets_scored}; skipped={tweets_skipped}; already_scored={already_scored}."
        )
        return ScoreTweetsSentimentSummary(
            usernames_requested=sorted(normalized_usernames),
            usernames_matched=matched_usernames,
            model_key=request.model_key,
            tweets_considered=tweets_considered,
            tweets_already_scored=already_scored,
            tweets_scored=tweets_scored,
            tweets_skipped=tweets_skipped,
            tweets_truncated=tweets_truncated,
            device="cpu" if scorer is None else scorer.device.type,
            dry_run=False,
            notes=notes,
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _append_scored_rows(
    score_rows: list[TweetSentimentScore],
    model_key: str,
    prepared_texts: list[PreparedTweetText],
    batch_scores: list[ScoredTweetText],
) -> int:
    for prepared_text, batch_score in zip(prepared_texts, batch_scores, strict=True):
        score_rows.append(
            TweetSentimentScore(
                tweet_id=prepared_text.tweet_id,
                model_key=model_key,
                status="scored",
                sentiment_label=batch_score.label,
                confidence=batch_score.confidence,
                negative_score=batch_score.negative_score,
                neutral_score=batch_score.neutral_score,
                positive_score=batch_score.positive_score,
                is_truncated=batch_score.is_truncated,
                input_char_count=prepared_text.input_char_count,
            )
        )
    return len(batch_scores)


def _normalize_usernames(usernames: list[str]) -> set[str]:
    return {username.strip().casefold() for username in usernames if username.strip()}


def _build_skip_reason(text: str | None, language: str | None) -> str | None:
    if text is None or not text.strip():
        return "empty_text"
    if language is None or language.strip().casefold() not in SCORABLE_LANGUAGE_CODES:
        return "language_not_supported"
    return None


def _prepare_tweet_text(candidate: TweetCandidate) -> PreparedTweetText | None:
    cleaned_text = URL_PATTERN.sub(" ", candidate.text)
    cleaned_text = MENTION_PATTERN.sub("@user", cleaned_text)
    cleaned_text = WHITESPACE_PATTERN.sub(" ", cleaned_text).strip()
    if not cleaned_text:
        return None
    return PreparedTweetText(
        tweet_id=candidate.tweet_id,
        text=cleaned_text,
        input_char_count=len(cleaned_text),
    )


def _resolve_model_max_length(tokenizer, config) -> int:
    candidate_lengths: list[int] = []
    for raw_value in (
        getattr(tokenizer, "model_max_length", None),
        getattr(config, "max_position_embeddings", None),
    ):
        if isinstance(raw_value, int) and 0 < raw_value < 100_000:
            candidate_lengths.append(raw_value)

    if candidate_lengths:
        return min(candidate_lengths)
    return 512
