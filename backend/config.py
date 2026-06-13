from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    database_url: str
    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:5173"]

    # AI tutor (Claude API). Empty key disables the tutor endpoints.
    anthropic_api_key: str = ""
    tutor_model: str = "claude-opus-4-8"
    # Development convenience: grant tutor access to everyone until the
    # billing pipeline (Stripe, v2) writes tutor_entitlements rows.
    tutor_free_access: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
