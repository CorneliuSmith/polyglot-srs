from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    # The anon / service_role keys (and their successors, the publishable /
    # secret API keys) are NOT used by the backend: it reaches Postgres
    # directly via database_url and authenticates requests with the JWT secret
    # / JWKS. Optional so migrating to the new API-key model — and dropping the
    # legacy keys — doesn't crash startup over values nothing reads.
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    # Shared HS256 secret for legacy Supabase access tokens. Still required
    # while any HS256 tokens are issued; asymmetric (ES256/RS256) tokens are
    # verified against the project JWKS and need no secret here.
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
    # Tutor allowances — counted in MESSAGES (the unit learners understand),
    # never billed per message. Pricing is flat per tier; these caps are
    # cost protection and are shown openly in the UI.
    #   free accounts: per calendar month (a real taste of the tutor)
    #   plus accounts: per day (fair use on a flat subscription)
    tutor_free_monthly_messages: int = 20
    tutor_plus_daily_messages: int = 100

    # Stripe billing for the tutor add-on. Empty secret disables checkout.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""          # the tutor subscription Price id
    # Language plans (WP16): one Price per plan scope. Empty = plan
    # checkout unavailable (the app still records the chosen scope free).
    stripe_price_single: str = ""      # "{Language} only" subscription
    stripe_price_all: str = ""         # "All languages" subscription
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
