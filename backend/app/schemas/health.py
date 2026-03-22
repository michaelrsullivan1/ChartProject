from pydantic import BaseModel


class DatabaseHealthResponse(BaseModel):
    connected: bool
    status: str
    detail: str


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    database: DatabaseHealthResponse
