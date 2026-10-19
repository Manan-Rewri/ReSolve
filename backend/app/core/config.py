"""Application settings, loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ReSolve API"
    environment: str = "development"
    debug: bool = True

    # Supabase project. Supabase is both our database and our auth provider,
    # so there is no separate auth stack to run.
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Comma separated list of allowed browser origins.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Judge0. The public community instance at ce.judge0.com needs no API key.
    # Set JUDGE0_API_KEY to route through RapidAPI instead.
    judge0_base_url: str = "https://ce.judge0.com"
    judge0_api_key: str = ""
    judge0_host: str = "judge0-ce.p.rapidapi.com"
    judge0_timeout_seconds: float = 30.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
