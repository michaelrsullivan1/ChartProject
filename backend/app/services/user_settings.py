from __future__ import annotations

from dataclasses import dataclass
import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.cohort_tag import CohortTag
from app.models.tweet import Tweet
from app.models.tweet_mood_score import TweetMoodScore
from app.models.user import User
from app.models.user_cohort_tag import UserCohortTag
from app.services.moods import DEFAULT_MOOD_MODEL


_COHORT_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


@dataclass(slots=True)
class UserSettingsCohortTagsRequest:
    model_key: str = DEFAULT_MOOD_MODEL
    eligible_only: bool = False
    view_name: str = "user-settings-cohort-tags"


@dataclass(slots=True)
class CreateUserSettingsCohortTagRequest:
    name: str
    view_name: str = "user-settings-create-cohort-tag"


@dataclass(slots=True)
class UserSettingsUsersRequest:
    model_key: str = DEFAULT_MOOD_MODEL
    view_name: str = "user-settings-users"


@dataclass(slots=True)
class UpdateUserSettingsUserCohortTagsRequest:
    user_id: int
    tag_slugs: tuple[str, ...]
    model_key: str = DEFAULT_MOOD_MODEL
    view_name: str = "user-settings-update-user-cohort-tags"


def build_user_settings_cohort_tags(
    request: UserSettingsCohortTagsRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        eligible_user_ids = _load_eligible_user_ids(session, model_key=request.model_key)
        tag_rows = session.execute(
            select(CohortTag.id, CohortTag.slug, CohortTag.name).order_by(
                func.lower(CohortTag.name).asc(),
                CohortTag.id.asc(),
            )
        ).all()
        link_rows = session.execute(
            select(UserCohortTag.cohort_tag_id, UserCohortTag.user_id)
        ).all()

        assigned_users_by_tag: dict[int, set[int]] = {}
        eligible_users_by_tag: dict[int, set[int]] = {}
        for cohort_tag_id, user_id in link_rows:
            tag_assigned_set = assigned_users_by_tag.setdefault(int(cohort_tag_id), set())
            tag_assigned_set.add(int(user_id))
            if int(user_id) in eligible_user_ids:
                tag_eligible_set = eligible_users_by_tag.setdefault(int(cohort_tag_id), set())
                tag_eligible_set.add(int(user_id))

        cohort_tags: list[dict[str, object]] = []
        for cohort_tag_id, slug, name in tag_rows:
            eligible_user_count = len(eligible_users_by_tag.get(int(cohort_tag_id), set()))
            if request.eligible_only and eligible_user_count <= 0:
                continue

            cohort_tags.append(
                {
                    "id": int(cohort_tag_id),
                    "slug": slug,
                    "name": name,
                    "assigned_user_count": len(assigned_users_by_tag.get(int(cohort_tag_id), set())),
                    "eligible_user_count": eligible_user_count,
                }
            )

        return {
            "view": request.view_name,
            "model": {
                "model_key": request.model_key,
            },
            "eligible_user_count": len(eligible_user_ids),
            "cohort_tags": cohort_tags,
        }
    finally:
        session.close()


def build_create_user_settings_cohort_tag(
    request: CreateUserSettingsCohortTagRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    cleaned_name = _normalize_name(request.name)
    normalized_slug = _normalize_slug(cleaned_name)

    session = session_factory()
    try:
        existing = session.scalar(
            select(CohortTag).where(
                or_(
                    CohortTag.slug == normalized_slug,
                    func.lower(CohortTag.name) == cleaned_name.lower(),
                )
            )
        )
        if existing is not None:
            raise RuntimeError(
                f"A cohort tag already exists for name={cleaned_name!r} or slug={normalized_slug!r}."
            )

        cohort_tag = CohortTag(
            slug=normalized_slug,
            name=cleaned_name,
        )
        session.add(cohort_tag)
        session.commit()
        session.refresh(cohort_tag)

        return {
            "view": request.view_name,
            "cohort_tag": {
                "id": cohort_tag.id,
                "slug": cohort_tag.slug,
                "name": cohort_tag.name,
                "assigned_user_count": 0,
                "eligible_user_count": 0,
            },
        }
    finally:
        session.close()


def build_user_settings_users(
    request: UserSettingsUsersRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        eligible_user_ids = _load_eligible_user_ids(session, model_key=request.model_key)
        if not eligible_user_ids:
            return {
                "view": request.view_name,
                "model": {"model_key": request.model_key},
                "users": [],
            }

        user_rows = session.execute(
            select(
                User.id,
                User.platform_user_id,
                User.username,
                User.display_name,
            )
            .where(User.id.in_(eligible_user_ids))
            .order_by(func.lower(User.username).asc())
        ).all()

        tag_rows = session.execute(
            select(
                UserCohortTag.user_id,
                CohortTag.id,
                CohortTag.slug,
                CohortTag.name,
            )
            .join(CohortTag, CohortTag.id == UserCohortTag.cohort_tag_id)
            .where(UserCohortTag.user_id.in_({int(row.id) for row in user_rows}))
            .order_by(func.lower(CohortTag.name).asc(), CohortTag.id.asc())
        ).all()

        tags_by_user_id: dict[int, list[dict[str, object]]] = {}
        for user_id, cohort_tag_id, slug, name in tag_rows:
            tags_by_user_id.setdefault(int(user_id), []).append(
                {
                    "id": int(cohort_tag_id),
                    "slug": slug,
                    "name": name,
                }
            )

        users = [
            {
                "id": int(row.id),
                "platform_user_id": row.platform_user_id,
                "username": row.username,
                "display_name": row.display_name,
                "cohort_tags": tags_by_user_id.get(int(row.id), []),
            }
            for row in user_rows
        ]

        return {
            "view": request.view_name,
            "model": {"model_key": request.model_key},
            "users": users,
        }
    finally:
        session.close()


def build_update_user_settings_user_cohort_tags(
    request: UpdateUserSettingsUserCohortTagsRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    normalized_tag_slugs = tuple(
        dict.fromkeys(
            _normalize_slug(tag_slug)
            for tag_slug in request.tag_slugs
            if tag_slug.strip()
        ).keys()
    )

    session = session_factory()
    try:
        eligible_user_ids = _load_eligible_user_ids(session, model_key=request.model_key)
        if request.user_id not in eligible_user_ids:
            raise RuntimeError(
                f"User id={request.user_id} is not eligible for cohort tagging for model_key={request.model_key!r}."
            )

        user = session.scalar(select(User).where(User.id == request.user_id))
        if user is None:
            raise RuntimeError(f"No canonical user exists for id={request.user_id}.")

        target_tags = list(
            session.scalars(
                select(CohortTag).where(CohortTag.slug.in_(normalized_tag_slugs))
            )
        )
        tag_by_slug = {tag.slug: tag for tag in target_tags}
        missing_tag_slugs = sorted(set(normalized_tag_slugs) - set(tag_by_slug.keys()))
        if missing_tag_slugs:
            raise RuntimeError(f"Unknown cohort tag slugs: {missing_tag_slugs!r}.")

        existing_links = list(
            session.scalars(
                select(UserCohortTag).where(UserCohortTag.user_id == request.user_id)
            )
        )
        existing_tag_ids = {link.cohort_tag_id for link in existing_links}
        target_tag_ids = {tag.id for tag in target_tags}

        for link in existing_links:
            if link.cohort_tag_id not in target_tag_ids:
                session.delete(link)

        for tag in target_tags:
            if tag.id not in existing_tag_ids:
                session.add(UserCohortTag(user_id=request.user_id, cohort_tag_id=tag.id))

        session.commit()

        assigned_tags = session.execute(
            select(CohortTag.id, CohortTag.slug, CohortTag.name)
            .join(UserCohortTag, UserCohortTag.cohort_tag_id == CohortTag.id)
            .where(UserCohortTag.user_id == request.user_id)
            .order_by(func.lower(CohortTag.name).asc(), CohortTag.id.asc())
        ).all()

        return {
            "view": request.view_name,
            "model": {"model_key": request.model_key},
            "user": {
                "id": user.id,
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
                "cohort_tags": [
                    {
                        "id": int(tag_id),
                        "slug": slug,
                        "name": name,
                    }
                    for tag_id, slug, name in assigned_tags
                ],
            },
        }
    finally:
        session.close()


def _load_eligible_user_ids(session: Session, *, model_key: str) -> set[int]:
    rows = session.execute(
        select(Tweet.author_user_id)
        .join(TweetMoodScore, TweetMoodScore.tweet_id == Tweet.id)
        .where(
            TweetMoodScore.model_key == model_key,
            TweetMoodScore.status == "scored",
        )
        .group_by(Tweet.author_user_id)
    ).all()
    return {int(row.author_user_id) for row in rows}


def _normalize_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise RuntimeError("Cohort tag name cannot be empty.")
    if len(cleaned) > 128:
        raise RuntimeError("Cohort tag name cannot exceed 128 characters.")
    return cleaned


def _normalize_slug(value: str) -> str:
    lowered = value.strip().lower()
    slug = _COHORT_SLUG_PATTERN.sub("-", lowered).strip("-")
    if not slug:
        raise RuntimeError("Cohort tag slug cannot be empty.")
    if len(slug) > 64:
        raise RuntimeError("Cohort tag slug cannot exceed 64 characters.")
    return slug
