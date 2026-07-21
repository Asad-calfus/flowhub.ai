"""App configuration, loaded from environment variables (see .env.example)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "FlowHub Feedback Intelligence API"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+psycopg://flowhub:flowhub@localhost:5433/flowhub"

    # Comma-separated origins, e.g. "http://localhost:3000,http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:3000"

    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 200
    DEFAULT_TOP_K: int = 5
    MAX_TOP_K: int = 20

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
