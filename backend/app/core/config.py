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

    # Running the code here instead of on Judge0. The public instance takes
    # the best part of half a minute a run and drops connections, so a local
    # compiler is used when there is one. Judge0 stays as the fallback.
    judge_prefer_local: bool = True
    local_cxx_path: str = ""
    local_timeout_seconds: float = 15.0

    # Where the catalogue is read from: `auto` uses Supabase when it is
    # configured and the JSON seed otherwise. `supabase` or `json` forces one.
    resolve_catalogue: str = "auto"

    # Where the practice state is kept. `auto` uses Supabase when it is
    # configured and the JSON file otherwise. The file store is also what the
    # test suite uses, so tests never touch the network.
    practice_store: str = "auto"
    state_file: str = "data/state.json"

    # Trust the user id the client sends when Supabase is not configured.
    # This is a local development convenience: with no backend .env there is
    # nothing to verify a token against. Set it to false when Supabase is set
    # up, so an anonymous caller cannot claim somebody else's id.
    trust_client_user_id: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key and self.supabase_service_role_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
