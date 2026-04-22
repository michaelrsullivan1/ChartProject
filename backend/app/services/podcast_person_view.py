from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.podcast_appearance import PodcastAppearance
from app.models.podcast_belief import PodcastBelief
from app.models.podcast_episode import PodcastEpisode
from app.models.podcast_person import PodcastPerson
from app.models.podcast_show import PodcastShow


@dataclass(slots=True)
class PodcastPersonViewRequest:
    person_slug: str
    view_name: str = "podcast-person-view"


def build_podcast_person_view(
    request: PodcastPersonViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        person = session.scalar(
            select(PodcastPerson).where(PodcastPerson.slug == request.person_slug)
        )
        if person is None:
            raise RuntimeError(f"No podcast person exists for slug={request.person_slug!r}.")

        appearance_count = session.scalar(
            select(func.count())
            .select_from(PodcastAppearance)
            .where(PodcastAppearance.podcast_person_id == person.id)
        ) or 0
        belief_count = session.scalar(
            select(func.count())
            .select_from(PodcastBelief)
            .where(PodcastBelief.podcast_person_id == person.id)
        ) or 0

        date_range = session.execute(
            select(
                func.min(PodcastEpisode.published_at),
                func.max(PodcastEpisode.published_at),
            )
            .join(PodcastAppearance, PodcastAppearance.podcast_episode_id == PodcastEpisode.id)
            .where(PodcastAppearance.podcast_person_id == person.id)
        ).one()

        top_shows = session.execute(
            select(
                PodcastShow.source_slug,
                PodcastShow.display_name,
                func.count().label("appearance_count"),
            )
            .join(PodcastEpisode, PodcastEpisode.podcast_show_id == PodcastShow.id)
            .join(PodcastAppearance, PodcastAppearance.podcast_episode_id == PodcastEpisode.id)
            .where(PodcastAppearance.podcast_person_id == person.id)
            .group_by(PodcastShow.id)
            .order_by(func.count().desc(), PodcastShow.display_name.asc())
            .limit(10)
        ).all()

        top_topics = session.execute(
            select(
                PodcastBelief.topic,
                func.count().label("belief_count"),
            )
            .where(
                PodcastBelief.podcast_person_id == person.id,
                PodcastBelief.topic.is_not(None),
            )
            .group_by(PodcastBelief.topic)
            .order_by(func.count().desc(), PodcastBelief.topic.asc())
            .limit(20)
        ).all()

        month_start = func.date_trunc("month", PodcastEpisode.published_at)
        monthly_topic_rows = session.execute(
            select(
                month_start.label("month_start"),
                PodcastBelief.topic,
                func.count().label("belief_count"),
            )
            .join(PodcastEpisode, PodcastEpisode.id == PodcastBelief.podcast_episode_id)
            .where(
                PodcastBelief.podcast_person_id == person.id,
                PodcastBelief.topic.is_not(None),
                PodcastEpisode.published_at.is_not(None),
            )
            .group_by(
                month_start,
                PodcastBelief.topic,
            )
            .order_by(
                month_start.asc(),
                func.count().desc(),
                PodcastBelief.topic.asc(),
            )
        ).all()

        appearances = session.execute(
            select(
                PodcastEpisode.published_at,
                PodcastShow.display_name,
                PodcastEpisode.title,
            )
            .join(PodcastAppearance, PodcastAppearance.podcast_episode_id == PodcastEpisode.id)
            .join(PodcastShow, PodcastShow.id == PodcastEpisode.podcast_show_id)
            .where(PodcastAppearance.podcast_person_id == person.id)
            .order_by(PodcastEpisode.published_at.asc(), PodcastEpisode.title.asc())
        ).all()

        recent_beliefs = session.execute(
            select(
                PodcastEpisode.published_at,
                PodcastShow.display_name,
                PodcastEpisode.title,
                PodcastBelief.topic,
                PodcastBelief.atomic_belief,
                PodcastBelief.quote,
            )
            .join(PodcastEpisode, PodcastEpisode.id == PodcastBelief.podcast_episode_id)
            .join(PodcastShow, PodcastShow.id == PodcastBelief.podcast_show_id)
            .where(PodcastBelief.podcast_person_id == person.id)
            .order_by(PodcastEpisode.published_at.desc(), PodcastBelief.id.desc())
            .limit(40)
        ).all()

        return {
            "view": request.view_name,
            "subject": {
                "slug": person.slug,
                "name": person.name,
                "source_person_id": person.source_person_id,
            },
            "summary": {
                "appearance_count": appearance_count,
                "belief_count": belief_count,
                "source_total_beliefs": person.total_beliefs_source,
                "range_start": _serialize_datetime(date_range[0]),
                "range_end": _serialize_datetime(date_range[1]),
            },
            "top_shows": [
                {
                    "show_slug": show_slug,
                    "show_name": show_name,
                    "appearance_count": appearance_total,
                }
                for show_slug, show_name, appearance_total in top_shows
            ],
            "top_topics": [
                {
                    "topic": topic,
                    "belief_count": belief_total,
                }
                for topic, belief_total in top_topics
            ],
            "monthly_topic_counts": [
                {
                    "month_start": _serialize_datetime(month_start),
                    "topic": topic,
                    "belief_count": belief_total,
                }
                for month_start, topic, belief_total in monthly_topic_rows
            ],
            "appearances": [
                {
                    "published_at": _serialize_datetime(published_at),
                    "show_name": show_name,
                    "episode_title": title,
                }
                for published_at, show_name, title in appearances
            ],
            "recent_beliefs": [
                {
                    "published_at": _serialize_datetime(published_at),
                    "show_name": show_name,
                    "episode_title": title,
                    "topic": topic,
                    "atomic_belief": atomic_belief,
                    "quote": quote,
                }
                for published_at, show_name, title, topic, atomic_belief, quote in recent_beliefs
            ],
        }
    finally:
        session.close()


def _serialize_datetime(value: object) -> str | None:
    if value is None:
        return None
    if not hasattr(value, "isoformat"):
        return None
    return value.isoformat().replace("+00:00", "Z")
