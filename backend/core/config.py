from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App configuration loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ─── App ───────────────────────────────────────────
    APP_TITLE: str = "Choose Your Own Adventure API"
    APP_DESCRIPTION: str = "API to generate cool stories based on user input"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    HOST: str = "localhost"
    PORT: int = 8000
    API_PREFIX: str = "/api" 

    # ─── Database ──────────────────────────────────────
    DATABASE_URL: str

    # ─── Security ──────────────────────────────────────
    ALLOWED_ORIGINS: str = ""

    # ─── LLM ───────────────────────────────────────────
    OPENAI_API_KEY: str

    @property
    def allowed_origins_list(self) -> list[str]:
        """Converts comma-separated ALLOWED_ORIGINS string to a list."""
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Returns cached settings instance — reads .env only once."""
    return Settings()