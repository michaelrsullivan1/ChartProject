from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.services.author_registry import (
    SyncManagedAuthorViewRequest,
    UpdateManagedAuthorViewRequest,
    build_admin_author_registry,
    build_public_author_registry,
    build_update_managed_author_view,
    sync_managed_author_view_for_username,
)


router = APIRouter(prefix="/author-registry")


class UpdateManagedAuthorViewBody(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=128)
    published: bool | None = None
    sort_order: int | None = None
    enable_overview: bool | None = None
    enable_moods: bool | None = None
    enable_heatmap: bool | None = None
    enable_bitcoin_mentions: bool | None = None
    overview_analysis_start: str | None = None
    mood_analysis_start: str | None = None
    heatmap_analysis_start: str | None = None


@router.get("")
def author_registry() -> dict[str, object]:
    return build_public_author_registry()


@router.get("/admin")
def author_registry_admin() -> dict[str, object]:
    return build_admin_author_registry()


@router.put("/{user_id}")
def update_author_registry_entry(
    user_id: int,
    body: UpdateManagedAuthorViewBody,
) -> dict[str, object]:
    return build_update_managed_author_view(
        UpdateManagedAuthorViewRequest(
            user_id=user_id,
            slug=body.slug,
            published=body.published,
            sort_order=body.sort_order,
            enable_overview=body.enable_overview,
            enable_moods=body.enable_moods,
            enable_heatmap=body.enable_heatmap,
            enable_bitcoin_mentions=body.enable_bitcoin_mentions,
            overview_analysis_start=body.overview_analysis_start,
            mood_analysis_start=body.mood_analysis_start,
            heatmap_analysis_start=body.heatmap_analysis_start,
        )
    )


@router.post("/sync/{username}")
def sync_author_registry_entry(
    username: str,
    published: bool = Query(default=True),
    tracked: bool = Query(default=True),
    ensure_analysis_starts: bool = Query(default=True),
) -> dict[str, object]:
    return sync_managed_author_view_for_username(
        SyncManagedAuthorViewRequest(
            username=username,
            published=published,
            tracked=tracked,
            ensure_analysis_starts=ensure_analysis_starts,
        )
    )
