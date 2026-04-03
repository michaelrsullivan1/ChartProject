from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.tweet import Tweet
from app.models.tweet_mood_score import TweetMoodScore
from app.models.user import User
from app.services.sentiment import (
    PreparedTweetText,
    TweetCandidate,
    _build_skip_reason,
    _normalize_usernames,
    _prepare_tweet_text,
    _resolve_model_max_length,
)


DEFAULT_MOOD_MODEL = "SamLowe/roberta-base-go_emotions"
DEFAULT_VISIBLE_MOOD_LABELS = (
    "optimism",
    "fear",
    "nervousness",
    "annoyance",
    "excitement",
    "confusion",
    "anger",
    "disapproval",
    "curiosity",
    "surprise",
    "disappointment",
    "disgust",
    "embarrassment",
)
SKIP_MOOD_LABEL = "__skip__"


@dataclass(slots=True)
class ScoreTweetsMoodsRequest:
    usernames: list[str]
    model_key: str = DEFAULT_MOOD_MODEL
    model_name: str = DEFAULT_MOOD_MODEL
    batch_size: int = 16
    overwrite_existing: bool = False
    dry_run: bool = False


@dataclass(slots=True)
class ScoreTweetsMoodsSummary:
    usernames_requested: list[str]
    usernames_matched: list[str]
    model_key: str
    tweets_considered: int
    tweets_already_scored: int
    tweets_scored: int
    tweets_skipped: int
    tweets_truncated: int
    mood_rows_written: int
    device: str
    dry_run: bool
    notes: str


@dataclass(slots=True)
class ScoredMoodTweetText:
    label_scores: dict[str, float]
    is_truncated: bool


class RobertaTweetMoodScorer:
    def __init__(self, model_name: str) -> None:
        import torch
        from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

        self.model_name = model_name
        self._torch = torch
        self.device = self._select_device()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.config = AutoConfig.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        self.max_length = _resolve_model_max_length(self.tokenizer, self.config)
        self.label_names = [
            str(self.config.id2label[index]).lower()
            for index in sorted(self.config.id2label)
        ]

    def score(self, prepared_texts: list[PreparedTweetText]) -> list[ScoredMoodTweetText]:
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

        with self._torch.no_grad():
            logits = self.model(**encoded).logits
            probabilities = self._torch.sigmoid(logits).cpu()

        scored_items: list[ScoredMoodTweetText] = []
        for index, row in enumerate(probabilities):
            label_scores = {
                label_name: float(row[label_index].item())
                for label_index, label_name in enumerate(self.label_names)
            }
            scored_items.append(
                ScoredMoodTweetText(
                    label_scores=label_scores,
                    is_truncated=len(untruncated_token_ids[index]) > self.max_length,
                )
            )
        return scored_items

    @staticmethod
    def _select_device() -> Any:
        import torch

        if torch.backends.mps.is_available():
            return torch.device("mps")
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")


def score_tweets_moods(
    request: ScoreTweetsMoodsRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> ScoreTweetsMoodsSummary:
    normalized_usernames = _normalize_usernames(request.usernames)
    if not normalized_usernames:
        raise RuntimeError("score_tweets_moods requires at least one username.")
    if request.batch_size < 1:
        raise RuntimeError("score_tweets_moods requires batch_size >= 1.")

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
            select(func.count(func.distinct(TweetMoodScore.tweet_id)))
            .select_from(TweetMoodScore)
            .join(Tweet, Tweet.id == TweetMoodScore.tweet_id)
            .where(
                Tweet.author_user_id.in_(matched_user_ids),
                TweetMoodScore.model_key == request.model_key,
            )
        ) or 0

        if request.overwrite_existing and not request.dry_run:
            session.execute(
                delete(TweetMoodScore).where(
                    TweetMoodScore.model_key == request.model_key,
                    TweetMoodScore.tweet_id.in_(
                        select(Tweet.id).where(Tweet.author_user_id.in_(matched_user_ids))
                    ),
                )
            )
            session.commit()
            already_scored = 0

        scored_tweet_ids = (
            select(TweetMoodScore.tweet_id)
            .where(TweetMoodScore.model_key == request.model_key)
            .group_by(TweetMoodScore.tweet_id)
            .subquery()
        )
        pending_rows = session.execute(
            select(Tweet.id, Tweet.text, Tweet.language)
            .outerjoin(scored_tweet_ids, scored_tweet_ids.c.tweet_id == Tweet.id)
            .where(
                Tweet.author_user_id.in_(matched_user_ids),
                scored_tweet_ids.c.tweet_id.is_(None),
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
                if _prepare_tweet_text(
                    TweetCandidate(tweet_id=tweet_id, text=text, language=language)
                ) is None:
                    tweets_skipped += 1
            tweets_scored = tweets_considered - tweets_skipped
            notes = (
                "Dry run completed. "
                f"Matched users={len(matched_usernames)}; pending tweets={tweets_considered}."
            )
            return ScoreTweetsMoodsSummary(
                usernames_requested=sorted(normalized_usernames),
                usernames_matched=matched_usernames,
                model_key=request.model_key,
                tweets_considered=tweets_considered,
                tweets_already_scored=already_scored,
                tweets_scored=tweets_scored,
                tweets_skipped=tweets_skipped,
                tweets_truncated=0,
                mood_rows_written=0,
                device="not-loaded",
                dry_run=True,
                notes=notes,
            )

        scorer: RobertaTweetMoodScorer | None = None
        pending_batch: list[PreparedTweetText] = []
        score_rows: list[TweetMoodScore] = []
        tweets_scored = 0
        tweets_skipped = 0
        tweets_truncated = 0
        mood_rows_written = 0

        for tweet_id, text, language in pending_rows:
            skip_reason = _build_skip_reason(text, language)
            if skip_reason is not None:
                score_rows.append(
                    TweetMoodScore(
                        tweet_id=tweet_id,
                        model_key=request.model_key,
                        mood_label=SKIP_MOOD_LABEL,
                        status="skipped",
                        skip_reason=skip_reason,
                        is_truncated=False,
                        input_char_count=len(text or ""),
                    )
                )
                tweets_skipped += 1
            else:
                prepared_text = _prepare_tweet_text(
                    TweetCandidate(tweet_id=tweet_id, text=text, language=language)
                )
                if prepared_text is None:
                    score_rows.append(
                        TweetMoodScore(
                            tweet_id=tweet_id,
                            model_key=request.model_key,
                            mood_label=SKIP_MOOD_LABEL,
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
                    scorer = RobertaTweetMoodScorer(request.model_name)
                batch_scores = scorer.score(pending_batch)
                batch_tweets_scored, batch_rows_written = _append_scored_rows(
                    score_rows,
                    request.model_key,
                    pending_batch,
                    batch_scores,
                )
                tweets_scored += batch_tweets_scored
                mood_rows_written += batch_rows_written
                tweets_truncated += sum(1 for item in batch_scores if item.is_truncated)
                pending_batch = []
                session.add_all(score_rows)
                session.commit()
                score_rows = []

        if pending_batch:
            if scorer is None:
                scorer = RobertaTweetMoodScorer(request.model_name)
            batch_scores = scorer.score(pending_batch)
            batch_tweets_scored, batch_rows_written = _append_scored_rows(
                score_rows,
                request.model_key,
                pending_batch,
                batch_scores,
            )
            tweets_scored += batch_tweets_scored
            mood_rows_written += batch_rows_written
            tweets_truncated += sum(1 for item in batch_scores if item.is_truncated)

        if score_rows:
            session.add_all(score_rows)
            session.commit()

        notes = (
            "Mood scoring completed. "
            f"Scored={tweets_scored}; skipped={tweets_skipped}; already_scored={already_scored}."
        )
        return ScoreTweetsMoodsSummary(
            usernames_requested=sorted(normalized_usernames),
            usernames_matched=matched_usernames,
            model_key=request.model_key,
            tweets_considered=tweets_considered,
            tweets_already_scored=already_scored,
            tweets_scored=tweets_scored,
            tweets_skipped=tweets_skipped,
            tweets_truncated=tweets_truncated,
            mood_rows_written=mood_rows_written,
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
    score_rows: list[TweetMoodScore],
    model_key: str,
    prepared_texts: list[PreparedTweetText],
    batch_scores: list[ScoredMoodTweetText],
) -> tuple[int, int]:
    rows_written = 0
    for prepared_text, batch_score in zip(prepared_texts, batch_scores, strict=True):
        for mood_label, score in batch_score.label_scores.items():
            score_rows.append(
                TweetMoodScore(
                    tweet_id=prepared_text.tweet_id,
                    model_key=model_key,
                    mood_label=mood_label,
                    status="scored",
                    score=score,
                    is_truncated=batch_score.is_truncated,
                    input_char_count=prepared_text.input_char_count,
                )
            )
            rows_written += 1
    return len(batch_scores), rows_written
