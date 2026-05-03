from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(OperationalError)
def handle_database_operational_error(
    request: Request,
    exc: OperationalError,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Database unavailable. Confirm the local Postgres service is running on "
                "localhost:5433 (for example via ./scripts/dev.sh or ./scripts/setup-db.sh)."
            ),
            "path": str(request.url.path),
        },
    )


app.include_router(api_router, prefix="/api")
