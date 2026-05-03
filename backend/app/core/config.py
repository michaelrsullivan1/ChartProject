from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Sentiment Analysis API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://chartproject:chartproject@localhost:5433/chartproject"
    twitterapi_base_url: str = "https://api.twitterapi.io"
    twitterapi_api_key: str = ""
    twelvedata_api_key: str = ""
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_prefix="CHART_",
        extra="ignore",
    )


settings = Settings()
