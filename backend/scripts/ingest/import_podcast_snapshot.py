import argparse
from collections.abc import Iterable
from datetime import UTC, datetime
import json
from pathlib import Path
from pprint import pprint
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.podcast_appearance import PodcastAppearance
from app.models.podcast_belief import PodcastBelief
from app.models.podcast_episode import PodcastEpisode
from app.models.podcast_person import PodcastPerson
from app.models.podcast_show import PodcastShow


DEFAULT_EXTRACTED_ROOT = (
    BACKEND_ROOT.parent / "data" / "raw" / "beliefengines" / "extracted" / "podcast-etl-data"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import the extracted Belief Engines podcast snapshot into the normalized podcast tables."
        )
    )
    parser.add_argument(
        "--extracted-root",
        default=str(DEFAULT_EXTRACTED_ROOT),
        help="Path to the extracted podcast-etl-data directory.",
    )
    parser.add_argument(
        "--limit-shows",
        type=int,
        help="Optional limit on how many shows to import for debugging.",
    )
    parser.add_argument(
        "--limit-persons",
        type=int,
        help="Optional limit on how many person profiles to import for debugging.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and summarize without committing changes.",
    )
    return parser.parse_args()


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def load_global_belief_record(
    extracted_root: Path,
    source_belief_id: str,
) -> dict[str, object] | None:
    belief_prefix = source_belief_id[2:6]
    belief_path = extracted_root / "beliefs" / belief_prefix / f"{source_belief_id}.json"
    if not belief_path.exists():
        return None
    return load_json(belief_path)


def slug_to_display_name(slug: str) -> str:
    return slug.replace("-", " ").strip().title()


def choose_first_non_empty(*values: object) -> object | None:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def iter_manifest_paths(manifest_root: Path, *, limit_shows: int | None = None) -> Iterable[Path]:
    show_dirs = sorted(path for path in manifest_root.iterdir() if path.is_dir())
    if limit_shows is not None:
        show_dirs = show_dirs[:limit_shows]
    for show_dir in show_dirs:
        yield from sorted(show_dir.glob("*.json"))


def iter_person_dirs(person_root: Path, *, limit_persons: int | None = None) -> Iterable[Path]:
    person_dirs = sorted(path for path in person_root.iterdir() if path.is_dir())
    if limit_persons is not None:
        person_dirs = person_dirs[:limit_persons]
    return person_dirs


def upsert_show(session: Session, *, source_slug: str) -> PodcastShow:
    show = session.scalar(select(PodcastShow).where(PodcastShow.source_slug == source_slug))
    if show is None:
        show = PodcastShow(
            source_slug=source_slug,
            display_name=slug_to_display_name(source_slug),
        )
        session.add(show)
        session.flush()
    return show


def upsert_episode(
    session: Session,
    *,
    show: PodcastShow,
    manifest_path: Path,
    extracted_root: Path,
) -> PodcastEpisode:
    manifest = load_json(manifest_path)
    transcript_path = (
        extracted_root
        / "raw"
        / "podcasts"
        / show.source_slug
        / "episodes"
        / manifest_path.stem
        / "transcript.json"
    )
    transcript = load_json(transcript_path) if transcript_path.exists() else {}
    transcript_episode = transcript.get("episode", {}) if isinstance(transcript, dict) else {}

    source_episode_id = str(
        choose_first_non_empty(
            manifest.get("episode_id"),
            manifest.get("episode_slug"),
            manifest_path.stem,
        )
    )
    title = str(
        choose_first_non_empty(
            manifest.get("title"),
            transcript_episode.get("title") if isinstance(transcript_episode, dict) else None,
            manifest_path.stem,
        )
    )

    episode = session.scalar(
        select(PodcastEpisode).where(PodcastEpisode.source_episode_id == source_episode_id)
    )
    if episode is None:
        episode = PodcastEpisode(
            source_episode_id=source_episode_id,
            episode_slug=str(manifest.get("episode_slug") or manifest_path.stem),
            podcast_show_id=show.id,
            title=title,
        )
        session.add(episode)
        session.flush()

    episode.episode_slug = str(manifest.get("episode_slug") or manifest_path.stem)
    episode.podcast_show_id = show.id
    episode.title = title
    episode.description = choose_first_non_empty(
        transcript_episode.get("description") if isinstance(transcript_episode, dict) else None,
        manifest.get("description"),
    )
    episode.published_at = parse_timestamp(
        choose_first_non_empty(
            transcript_episode.get("published_at") if isinstance(transcript_episode, dict) else None,
            manifest.get("published_at"),
            manifest.get("published_date"),
        )
    )
    duration_value = choose_first_non_empty(
        transcript_episode.get("duration_seconds") if isinstance(transcript_episode, dict) else None,
        manifest.get("duration_seconds"),
    )
    episode.duration_seconds = int(duration_value) if duration_value is not None else None
    episode.audio_url = choose_first_non_empty(
        transcript_episode.get("audio_url") if isinstance(transcript_episode, dict) else None,
        manifest.get("audio_url"),
    )
    episode.manifest_status = choose_first_non_empty(manifest.get("status"), None)
    episode.manifest_created_at = parse_timestamp(manifest.get("created_at"))
    episode.manifest_updated_at = parse_timestamp(manifest.get("updated_at"))
    episode.source_manifest_path = str(manifest_path.relative_to(extracted_root))
    return episode


def upsert_person(session: Session, *, person_dir: Path) -> PodcastPerson:
    profile = load_json(person_dir / "profile.json")
    trust_path = person_dir / "trust.json"
    trust = load_json(trust_path) if trust_path.exists() else {}

    source_person_id = str(profile.get("id") or person_dir.name)
    slug = str(profile.get("slug") or source_person_id)
    person = session.scalar(
        select(PodcastPerson).where(PodcastPerson.source_person_id == source_person_id)
    )
    if person is None:
        person = PodcastPerson(
            source_person_id=source_person_id,
            slug=slug,
            name=str(profile.get("name") or source_person_id),
            has_wiki=bool(profile.get("has_wiki") or False),
        )
        session.add(person)
        session.flush()

    bio = profile.get("bio") or {}
    stats = profile.get("stats") or {}
    person.slug = slug
    person.name = str(profile.get("name") or source_person_id)
    person.bio_summary = bio.get("summary") if isinstance(bio, dict) else None
    person.has_wiki = bool(profile.get("has_wiki") or False)
    person.wiki_url = trust.get("wiki_url") if isinstance(trust, dict) else None
    if profile.get("wiki") and isinstance(profile["wiki"], dict):
        person.wiki_url = choose_first_non_empty(profile["wiki"].get("url"), person.wiki_url)
    person.total_beliefs_source = (
        int(stats.get("total_beliefs")) if isinstance(stats, dict) and stats.get("total_beliefs") is not None else None
    )
    person.trust_badge = trust.get("badge") if isinstance(trust, dict) else None
    person.trust_score = float(trust["score"]) if isinstance(trust, dict) and trust.get("score") is not None else None
    person.source_created_at = parse_timestamp(profile.get("created_at"))
    person.source_updated_at = parse_timestamp(profile.get("updated_at"))
    person.trust_calculated_at = parse_timestamp(
        trust.get("calculated_at") if isinstance(trust, dict) else None
    )
    return person


def upsert_appearance(
    session: Session,
    *,
    person: PodcastPerson,
    episode: PodcastEpisode,
) -> None:
    appearance = session.scalar(
        select(PodcastAppearance).where(
            PodcastAppearance.podcast_person_id == person.id,
            PodcastAppearance.podcast_episode_id == episode.id,
        )
    )
    if appearance is None:
        appearance = PodcastAppearance(
            podcast_person_id=person.id,
            podcast_episode_id=episode.id,
            source_person_id=person.source_person_id,
            source_episode_id=episode.source_episode_id,
        )
        session.add(appearance)
        return

    appearance.source_person_id = person.source_person_id
    appearance.source_episode_id = episode.source_episode_id


def upsert_belief(
    session: Session,
    *,
    extracted_root: Path,
    person: PodcastPerson,
    episode: PodcastEpisode,
    show: PodcastShow,
    record: dict[str, object],
) -> None:
    source_belief_id = str(record.get("id"))
    global_record = load_global_belief_record(extracted_root, source_belief_id)
    belief = session.scalar(
        select(PodcastBelief).where(PodcastBelief.source_belief_id == source_belief_id)
    )
    if belief is None:
        belief = PodcastBelief(
            source_belief_id=source_belief_id,
            podcast_person_id=person.id,
            podcast_episode_id=episode.id,
            podcast_show_id=show.id,
            quote=str(record.get("quote") or ""),
            atomic_belief=str(record.get("atomic_belief") or ""),
        )
        session.add(belief)

    belief.podcast_person_id = person.id
    belief.podcast_episode_id = episode.id
    belief.podcast_show_id = show.id
    belief.quote = str(
        choose_first_non_empty(
            global_record.get("quote_text") if global_record else None,
            record.get("quote"),
            "",
        )
    )
    belief.atomic_belief = str(record.get("atomic_belief") or "")
    belief.topic = (
        choose_first_non_empty(
            global_record.get("topic") if global_record else None,
            record.get("topic"),
        )
        if isinstance(
            choose_first_non_empty(
                global_record.get("topic") if global_record else None,
                record.get("topic"),
            ),
            str,
        )
        else None
    )
    belief.domain = (
        record.get("domain") if isinstance(record.get("domain"), str) else None
    )
    belief.worldview = (
        choose_first_non_empty(
            global_record.get("worldview") if global_record else None,
            record.get("worldview"),
        )
        if isinstance(
            choose_first_non_empty(
                global_record.get("worldview") if global_record else None,
                record.get("worldview"),
            ),
            str,
        )
        else None
    )
    belief.core_axiom = (
        choose_first_non_empty(
            global_record.get("core_axiom") if global_record else None,
            record.get("core_axiom"),
        )
        if isinstance(
            choose_first_non_empty(
                global_record.get("core_axiom") if global_record else None,
                record.get("core_axiom"),
            ),
            str,
        )
        else None
    )
    weights_value = choose_first_non_empty(
        global_record.get("weights") if global_record else None,
        record.get("weights"),
    )
    belief.weights_json = weights_value if isinstance(weights_value, list) else None
    belief.timestamp_start_seconds = (
        float(
            choose_first_non_empty(
                global_record.get("timestamp_start") if global_record else None,
                record.get("timestamp_start"),
            )
        )
        if choose_first_non_empty(
            global_record.get("timestamp_start") if global_record else None,
            record.get("timestamp_start"),
        )
        is not None
        else None
    )
    belief.timestamp_end_seconds = (
        float(
            choose_first_non_empty(
                global_record.get("timestamp_end") if global_record else None,
                record.get("timestamp_end"),
            )
        )
        if choose_first_non_empty(
            global_record.get("timestamp_end") if global_record else None,
            record.get("timestamp_end"),
        )
        is not None
        else None
    )
    belief.source_created_at = parse_timestamp(record.get("created_at"))


def build_person_maps(session: Session) -> tuple[dict[str, PodcastPerson], dict[str, PodcastEpisode], dict[str, PodcastShow]]:
    persons = list(session.scalars(select(PodcastPerson)))
    episodes = list(session.scalars(select(PodcastEpisode)))
    shows = list(session.scalars(select(PodcastShow)))
    persons_by_source_id = {person.source_person_id: person for person in persons}
    episodes_by_source_id = {episode.source_episode_id: episode for episode in episodes}
    shows_by_source_slug = {show.source_slug: show for show in shows}
    return persons_by_source_id, episodes_by_source_id, shows_by_source_slug


def load_episode_maps(session: Session) -> tuple[dict[str, PodcastEpisode], dict[str, PodcastShow]]:
    episodes = list(session.scalars(select(PodcastEpisode)))
    shows = list(session.scalars(select(PodcastShow)))
    episodes_by_source_id = {episode.source_episode_id: episode for episode in episodes}
    shows_by_source_slug = {show.source_slug: show for show in shows}
    return episodes_by_source_id, shows_by_source_slug


def main() -> None:
    args = parse_args()
    extracted_root = Path(args.extracted_root).resolve()
    manifest_root = extracted_root / "runs" / "manifests"
    person_root = extracted_root / "persons"

    if not manifest_root.exists():
        raise RuntimeError(f"Manifest root not found: {manifest_root}")
    if not person_root.exists():
        raise RuntimeError(f"Person root not found: {person_root}")

    session = SessionLocal()
    try:
        touched_show_slugs: set[str] = set()
        episode_count = 0
        person_count = 0
        appearance_count = 0
        belief_count = 0

        for manifest_path in iter_manifest_paths(manifest_root, limit_shows=args.limit_shows):
            source_slug = manifest_path.parent.name
            show = upsert_show(session, source_slug=source_slug)
            episode = upsert_episode(
                session,
                show=show,
                manifest_path=manifest_path,
                extracted_root=extracted_root,
            )
            touched_show_slugs.add(source_slug)
            episode_count += 1

        session.flush()
        episodes_by_source_id, shows_by_source_slug = load_episode_maps(session)
        existing_belief_ids = set(session.scalars(select(PodcastBelief.source_belief_id)))
        staged_belief_ids = set(existing_belief_ids)

        for person_dir in iter_person_dirs(person_root, limit_persons=args.limit_persons):
            profile_path = person_dir / "profile.json"
            if not profile_path.exists():
                continue

            person = upsert_person(session, person_dir=person_dir)
            person_count += 1

            profile = load_json(profile_path)
            for source_episode_id in profile.get("appearances", []):
                if not isinstance(source_episode_id, str):
                    continue
                episode = episodes_by_source_id.get(source_episode_id)
                if episode is None:
                    continue
                upsert_appearance(session, person=person, episode=episode)
                appearance_count += 1

            beliefs_path = person_dir / "beliefs.jsonl"
            if not beliefs_path.exists():
                continue

            with beliefs_path.open() as handle:
                for line in handle:
                    normalized = line.strip()
                    if not normalized:
                        continue
                    record = json.loads(normalized)
                    source_episode_id = record.get("episode_id")
                    source_show_slug = record.get("podcast_id")
                    source_belief_id = record.get("id")
                    if not isinstance(source_episode_id, str):
                        continue
                    if not isinstance(source_show_slug, str):
                        continue
                    if not isinstance(source_belief_id, str):
                        continue
                    if source_belief_id in staged_belief_ids:
                        continue
                    episode = episodes_by_source_id.get(source_episode_id)
                    show = shows_by_source_slug.get(source_show_slug)
                    if episode is None or show is None:
                        continue
                    upsert_belief(
                        session,
                        extracted_root=extracted_root,
                        person=person,
                        episode=episode,
                        show=show,
                        record=record,
                    )
                    staged_belief_ids.add(source_belief_id)
                    belief_count += 1

        persons_by_source_id, episodes_by_source_id, shows_by_source_slug = build_person_maps(session)

        for manifest_path in iter_manifest_paths(manifest_root, limit_shows=args.limit_shows):
            manifest = load_json(manifest_path)
            source_episode_id = str(
                choose_first_non_empty(
                    manifest.get("episode_id"),
                    manifest.get("episode_slug"),
                    manifest_path.stem,
                )
            )
            source_show_slug = manifest_path.parent.name
            episode = episodes_by_source_id.get(source_episode_id)
            show = shows_by_source_slug.get(source_show_slug)
            if episode is None or show is None:
                continue

            artifact_paths = manifest.get("artifacts", {}).get("beliefs", [])
            if not isinstance(artifact_paths, list):
                continue

            for artifact_path in artifact_paths:
                if not isinstance(artifact_path, str):
                    continue
                belief_path = extracted_root / artifact_path
                if not belief_path.exists():
                    continue
                record = load_json(belief_path)
                source_belief_id = record.get("id")
                if not isinstance(source_belief_id, str):
                    continue
                if source_belief_id in staged_belief_ids:
                    continue
                speaker_slug = record.get("speaker_slug")
                if not isinstance(speaker_slug, str):
                    continue
                person = persons_by_source_id.get(speaker_slug)
                if person is None:
                    continue
                upsert_belief(
                    session,
                    extracted_root=extracted_root,
                    person=person,
                    episode=episode,
                    show=show,
                    record={
                        "id": record.get("id"),
                        "quote": record.get("quote_text"),
                        "atomic_belief": record.get("atomic_belief"),
                        "topic": record.get("topic"),
                        "domain": record.get("domain"),
                        "worldview": record.get("worldview"),
                        "core_axiom": record.get("core_axiom"),
                        "weights": record.get("weights"),
                        "timestamp_start": record.get("timestamp_start"),
                        "timestamp_end": record.get("timestamp_end"),
                        "created_at": record.get("created_at"),
                    },
                )
                staged_belief_ids.add(source_belief_id)
                belief_count += 1

        if args.dry_run:
            session.rollback()
        else:
            session.commit()

        pprint(
            {
                "extracted_root": str(extracted_root),
                "dry_run": args.dry_run,
                "manifest_rows_processed": episode_count,
                "shows_touched": len(touched_show_slugs),
                "person_profiles_processed": person_count,
                "appearance_links_processed": appearance_count,
                "belief_rows_processed": belief_count,
                "limit_shows": args.limit_shows,
                "limit_persons": args.limit_persons,
            }
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
