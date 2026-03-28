from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ChartProject API"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/chartproject"
    twitterapi_base_url: str = "https://api.twitterapi.io"
    twitterapi_api_key: str = ""
    twelvedata_api_key: str = ""
    frontend_origin: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CHART_",
        extra="ignore",
    )


settings = Settings()
