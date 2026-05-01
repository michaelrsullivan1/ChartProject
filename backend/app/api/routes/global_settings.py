from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.managed_narratives import (
    CreateManagedNarrativeRequest,
    ManagedNarrativesRequest,
    UpdateManagedNarrativeRequest,
    build_create_managed_narrative,
    build_managed_narratives,
    build_update_managed_narrative,
)


router = APIRouter(prefix="/global-settings")


class ManagedNarrativeBody(BaseModel):
    phrase: str = Field(min_length=1, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)


@router.get("/narratives")
def global_settings_narratives() -> dict[str, object]:
    return build_managed_narratives(
        ManagedNarrativesRequest(
            view_name="global-settings-narratives",
        )
    )


@router.post("/narratives")
def create_global_settings_narrative(body: ManagedNarrativeBody) -> dict[str, object]:
    return build_create_managed_narrative(
        CreateManagedNarrativeRequest(
            phrase=body.phrase,
            name=body.name,
            view_name="global-settings-create-narrative",
        )
    )


@router.put("/narratives/{narrative_id}")
def update_global_settings_narrative(
    narrative_id: int,
    body: ManagedNarrativeBody,
) -> dict[str, object]:
    return build_update_managed_narrative(
        UpdateManagedNarrativeRequest(
            narrative_id=narrative_id,
            phrase=body.phrase,
            name=body.name,
            view_name="global-settings-update-narrative",
        )
    )
