from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse
from app.services.health import check_database_health


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    database = check_database_health()
    status = "ok" if database.connected else "degraded"

    return HealthResponse(
        status=status,
        app_name=settings.app_name,
        environment=settings.environment,
        database=database,
    )
