from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FITFINDER_", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./fitfinder.db"
    # Comma separated API keys. Empty = auth disabled (local dev only).
    api_keys: str = ""
    seed_demo_data: bool = True
    cors_origins: str = "*"  # tighten for production (web app + browser extension origins)

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
