from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine
from app.schemas.health import DatabaseHealthResponse


def check_database_health() -> DatabaseHealthResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return DatabaseHealthResponse(
            connected=False,
            status="unavailable",
            detail=str(exc.__class__.__name__),
        )

    return DatabaseHealthResponse(
        connected=True,
        status="ok",
        detail="Connection succeeded.",
    )
