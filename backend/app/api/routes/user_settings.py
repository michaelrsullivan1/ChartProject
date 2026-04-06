from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.moods import DEFAULT_MOOD_MODEL
from app.services.user_settings import (
    CreateUserSettingsCohortTagRequest,
    UpdateUserSettingsUserCohortTagsRequest,
    UserSettingsCohortTagsRequest,
    UserSettingsUsersRequest,
    build_create_user_settings_cohort_tag,
    build_update_user_settings_user_cohort_tags,
    build_user_settings_cohort_tags,
    build_user_settings_users,
)


router = APIRouter(prefix="/user-settings")


class CreateCohortTagBody(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class UpdateUserCohortTagsBody(BaseModel):
    tag_slugs: list[str] = Field(default_factory=list)


@router.get("/cohort-tags")
def user_settings_cohort_tags(
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
    eligible_only: bool = Query(default=False),
) -> dict[str, object]:
    return build_user_settings_cohort_tags(
        UserSettingsCohortTagsRequest(
            model_key=model_key,
            eligible_only=eligible_only,
            view_name="user-settings-cohort-tags",
        )
    )


@router.post("/cohort-tags")
def create_user_settings_cohort_tag(body: CreateCohortTagBody) -> dict[str, object]:
    return build_create_user_settings_cohort_tag(
        CreateUserSettingsCohortTagRequest(
            name=body.name,
            view_name="user-settings-create-cohort-tag",
        )
    )


@router.get("/users")
def user_settings_users(
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return build_user_settings_users(
        UserSettingsUsersRequest(
            model_key=model_key,
            view_name="user-settings-users",
        )
    )


@router.put("/users/{user_id}/cohort-tags")
def update_user_settings_user_cohort_tags(
    user_id: int,
    body: UpdateUserCohortTagsBody,
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return build_update_user_settings_user_cohort_tags(
        UpdateUserSettingsUserCohortTagsRequest(
            user_id=user_id,
            tag_slugs=tuple(body.tag_slugs),
            model_key=model_key,
            view_name="user-settings-update-user-cohort-tags",
        )
    )
