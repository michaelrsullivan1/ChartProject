from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.podcast_appearance import PodcastAppearance
from app.models.podcast_belief import PodcastBelief
from app.models.podcast_episode import PodcastEpisode
from app.models.podcast_person import PodcastPerson
from app.models.podcast_show import PodcastShow


@dataclass(slots=True)
class PodcastNarrativeMixViewRequest:
    person_slug: str
    view_name: str = "podcast-narrative-mix-view"


@dataclass(slots=True)
class _PeriodAccumulator:
    key: str
    label: str
    start: datetime | None
    end: datetime | None
    appearance_count: int = 0
    total_beliefs: int = 0
    topic_labeled_beliefs: int = 0
    topic_counts: dict[str, int] = field(default_factory=dict)
    appearance_start_index: int | None = None
    appearance_end_index: int | None = None
    show_name: str | None = None
    episode_title: str | None = None


def build_podcast_narrative_mix_view(
    request: PodcastNarrativeMixViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        person = session.scalar(
            select(PodcastPerson).where(PodcastPerson.slug == request.person_slug)
        )
        if person is None:
            raise RuntimeError(
                f"No podcast person exists for slug={request.person_slug!r}."
            )

        appearance_rows = session.execute(
            select(
                PodcastEpisode.id,
                PodcastEpisode.published_at,
                PodcastShow.display_name,
                PodcastEpisode.title,
            )
            .join(PodcastAppearance, PodcastAppearance.podcast_episode_id == PodcastEpisode.id)
            .join(PodcastShow, PodcastShow.id == PodcastEpisode.podcast_show_id)
            .where(
                PodcastAppearance.podcast_person_id == person.id,
                PodcastEpisode.published_at.is_not(None),
            )
            .order_by(PodcastEpisode.published_at.asc(), PodcastEpisode.id.asc())
        ).all()

        belief_rows = session.execute(
            select(
                PodcastEpisode.id,
                PodcastEpisode.published_at,
                PodcastBelief.topic,
            )
            .join(PodcastEpisode, PodcastEpisode.id == PodcastBelief.podcast_episode_id)
            .where(
                PodcastBelief.podcast_person_id == person.id,
                PodcastEpisode.published_at.is_not(None),
            )
            .order_by(PodcastEpisode.published_at.asc(), PodcastBelief.id.asc())
        ).all()

        month_periods = _build_month_periods(appearance_rows, belief_rows)
        appearance_periods = _build_appearance_index_periods(appearance_rows, belief_rows)
        topic_rows = _build_topic_rows(
            belief_rows,
            month_periods,
            appearance_periods,
        )

        range_start = appearance_rows[0][1] if appearance_rows else None
        range_end = appearance_rows[-1][1] if appearance_rows else None

        return {
            "view": request.view_name,
            "subject": {
                "slug": person.slug,
                "name": person.name,
                "source_person_id": person.source_person_id,
            },
            "summary": {
                "appearance_count": len(appearance_rows),
                "belief_count": len(belief_rows),
                "range_start": _serialize_datetime(range_start),
                "range_end": _serialize_datetime(range_end),
            },
            "timeline_modes": {
                "month": {
                    "mode": "month",
                    "label": "Calendar Month",
                    "periods": [_serialize_period(period) for period in month_periods],
                },
                "appearance_index": {
                    "mode": "appearance_index",
                    "label": "Appearance Index",
                    "periods": [_serialize_period(period) for period in appearance_periods],
                },
            },
            "topics": topic_rows,
            "generated_at": _serialize_datetime(datetime.now(tz=UTC)),
        }
    finally:
        session.close()


def _build_month_periods(appearance_rows: list[tuple], belief_rows: list[tuple]) -> list[_PeriodAccumulator]:
    period_by_key: dict[str, _PeriodAccumulator] = {}

    for _, published_at, _, _ in appearance_rows:
        if published_at is None:
            continue
        key, start = _month_key_start(published_at)
        period = period_by_key.get(key)
        if period is None:
            period = _PeriodAccumulator(
                key=key,
                label=start.strftime("%b %Y"),
                start=start,
                end=start,
            )
            period_by_key[key] = period
        period.appearance_count += 1

    for _, published_at, topic in belief_rows:
        if published_at is None:
            continue
        key, start = _month_key_start(published_at)
        period = period_by_key.get(key)
        if period is None:
            period = _PeriodAccumulator(
                key=key,
                label=start.strftime("%b %Y"),
                start=start,
                end=start,
            )
            period_by_key[key] = period
        period.total_beliefs += 1
        if isinstance(topic, str) and topic.strip():
            normalized_topic = topic.strip()
            period.topic_labeled_beliefs += 1
            period.topic_counts[normalized_topic] = period.topic_counts.get(normalized_topic, 0) + 1

    return [period_by_key[key] for key in sorted(period_by_key)]


def _build_appearance_index_periods(
    appearance_rows: list[tuple],
    belief_rows: list[tuple],
) -> list[_PeriodAccumulator]:
    periods: list[_PeriodAccumulator] = []
    episode_to_period: dict[int, _PeriodAccumulator] = {}

    for index, (episode_id, published_at, show_name, episode_title) in enumerate(
        appearance_rows,
        start=1,
    ):
        period = _PeriodAccumulator(
            key=f"appearance-{index}",
            label=f"A{index}",
            start=published_at,
            end=published_at,
            appearance_count=1,
            appearance_start_index=index,
            appearance_end_index=index,
            show_name=show_name,
            episode_title=episode_title,
        )
        periods.append(period)
        episode_to_period[episode_id] = period

    for episode_id, _, topic in belief_rows:
        period = episode_to_period.get(episode_id)
        if period is None:
            continue
        period.total_beliefs += 1
        if isinstance(topic, str) and topic.strip():
            normalized_topic = topic.strip()
            period.topic_labeled_beliefs += 1
            period.topic_counts[normalized_topic] = period.topic_counts.get(normalized_topic, 0) + 1

    return periods


def _build_topic_rows(
    belief_rows: list[tuple],
    month_periods: list[_PeriodAccumulator],
    appearance_periods: list[_PeriodAccumulator],
) -> list[dict[str, object]]:
    topic_counts: dict[str, int] = {}
    topic_first_seen: dict[str, datetime] = {}
    topic_last_seen: dict[str, datetime] = {}

    for _, published_at, topic in belief_rows:
        if published_at is None or not isinstance(topic, str) or not topic.strip():
            continue
        normalized_topic = topic.strip()
        topic_counts[normalized_topic] = topic_counts.get(normalized_topic, 0) + 1
        topic_first_seen[normalized_topic] = min(
            topic_first_seen.get(normalized_topic, published_at),
            published_at,
        )
        topic_last_seen[normalized_topic] = max(
            topic_last_seen.get(normalized_topic, published_at),
            published_at,
        )

    total_topic_labeled_beliefs = sum(topic_counts.values())
    active_month_counts: dict[str, int] = {}
    active_appearance_counts: dict[str, int] = {}

    for period in month_periods:
        for topic in period.topic_counts:
            active_month_counts[topic] = active_month_counts.get(topic, 0) + 1
    for period in appearance_periods:
        for topic in period.topic_counts:
            active_appearance_counts[topic] = active_appearance_counts.get(topic, 0) + 1

    sorted_topics = sorted(
        topic_counts.items(),
        key=lambda item: (-item[1], item[0].lower()),
    )
    return [
        {
            "topic": topic,
            "total_beliefs": total,
            "overall_share": (
                float(total / total_topic_labeled_beliefs)
                if total_topic_labeled_beliefs
                else 0.0
            ),
            "first_seen": _serialize_datetime(topic_first_seen.get(topic)),
            "last_seen": _serialize_datetime(topic_last_seen.get(topic)),
            "active_month_count": active_month_counts.get(topic, 0),
            "active_appearance_count": active_appearance_counts.get(topic, 0),
        }
        for topic, total in sorted_topics
    ]


def _serialize_period(period: _PeriodAccumulator) -> dict[str, object]:
    sorted_topics = sorted(
        period.topic_counts.items(),
        key=lambda item: (-item[1], item[0].lower()),
    )
    return {
        "period_key": period.key,
        "period_label": period.label,
        "period_start": _serialize_datetime(period.start),
        "period_end": _serialize_datetime(period.end),
        "appearance_start_index": period.appearance_start_index,
        "appearance_end_index": period.appearance_end_index,
        "show_name": period.show_name,
        "episode_title": period.episode_title,
        "appearance_count": period.appearance_count,
        "total_beliefs": period.total_beliefs,
        "topic_labeled_beliefs": period.topic_labeled_beliefs,
        "topics": [
            {
                "topic": topic,
                "belief_count": count,
                "topic_share": (
                    float(count / period.topic_labeled_beliefs)
                    if period.topic_labeled_beliefs
                    else 0.0
                ),
            }
            for topic, count in sorted_topics
        ],
    }


def _month_key_start(value: datetime) -> tuple[str, datetime]:
    start = value.astimezone(UTC).replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return start.strftime("%Y-%m-%d"), start


def _serialize_datetime(value: object) -> str | None:
    if value is None:
        return None
    if not hasattr(value, "isoformat"):
        return None
    return value.isoformat().replace("+00:00", "Z")
