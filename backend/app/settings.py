from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hermes Odds"
    football_data_api_token: str | None = None
    api_football_key: str | None = None
    api_football_rapidapi_key: str | None = None
    thesportsdb_api_key: str | None = None
    cache_ttl_seconds: int = 900
    details_max_fixtures: int = 12

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


settings = Settings()
