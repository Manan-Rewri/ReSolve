from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Resolve - DSA Revision System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = "resolve-super-secret-jwt-key-change-in-production-123456789"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    DATABASE_URL: str = "sqlite:///./resolve.db"

    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""  # Never expose to the frontend.

    JUDGE0_BASE_URL: str = "https://ce.judge0.com"
    JUDGE0_API_KEY: str = ""
    JUDGE0_API_HOST: str = ""
    MAX_SOURCE_CODE_LENGTH: int = 20000
    MAX_STDIN_LENGTH: int = 10000
    DEFAULT_CPU_TIME_LIMIT: float = 3.0
    DEFAULT_MEMORY_LIMIT_KB: int = 128000
    REQUEST_TIMEOUT_SECONDS: float = 20.0

    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()