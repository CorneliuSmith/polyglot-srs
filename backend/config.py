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
    # Cheaper model for the off-the-hot-path session summarizer / memory extractor.
    tutor_summary_model: str = "claude-sonnet-5"
    # Optional Redis for distributed rate limiting across workers. Empty = the
    # in-memory per-process limiter (fine for a single worker / dev).
    redis_url: str = ""
    # Dev-only: when true, the tutor returns canned responses with no API key
    # and no Claude API calls — for testing the full flow (chat, entitlement,
    # memory, session summary) before wiring up real billing. Never enable in
    # production. Try `/remember global native_language English` in the chat to
    # exercise the remember→persist path.
    tutor_dev_mock: bool = False
    # Development convenience: grant tutor access to everyone until the
    # billing pipeline (Stripe) writes tutor_entitlements rows. Set False in
    # production so entitlements actually govern access.
    tutor_free_access: bool = True

    # Stripe billing for the tutor add-on. Empty secret disables checkout.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""          # the tutor subscription Price id
    # Dev-only: "buy" the tutor with no Stripe key — /checkout grants the
    # entitlement directly so the gated → unlocked flow is testable. Never
    # enable in production.
    stripe_dev_mock: bool = False
    # Base URL the user is sent back to after Stripe Checkout.
    app_base_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
