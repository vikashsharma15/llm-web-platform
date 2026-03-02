from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache
class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    API_PREFIX: str = "/api"
    DEBUG: bool = False
    DATABASE_URL: str
    OPENAI_API_KEY: str

    # Always keep env vars as string
    ALLOWED_ORIGINS: str = ""


    @property
    def allowed_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()