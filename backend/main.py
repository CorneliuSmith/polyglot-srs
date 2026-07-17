"""PolyglotSRS FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.repositories.pool import close_pool, init_pool
from backend.routers.audio import router as audio_router
from backend.routers.auth import router as auth_router
from backend.routers.billing import router as billing_router
from backend.routers.contribute import router as contribute_router
from backend.routers.curriculum import router as curriculum_router
from backend.routers.dashboard import router as dashboard_router
from backend.routers.languages import router as languages_router
from backend.routers.notes import router as notes_router
from backend.routers.onboarding import router as onboarding_router
from backend.routers.review import router as review_router
from backend.routers.tutor import router as tutor_router
from backend.services.nlp import init_nlp_backends


def _init_sentry(settings) -> None:
    """Error telemetry (WP19d) — a no-op until SENTRY_DSN is set.

    Errors only (no tracing) and no PII: beta bugs should arrive as stack
    traces instead of screenshots, not as a surveillance feed.
    """
    dsn = getattr(settings, "sentry_dsn", "")
    if not dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        environment=getattr(settings, "environment", "production"),
        traces_sample_rate=0.0,
        send_default_pii=False,
    )


def create_app() -> FastAPI:
    """Application factory — defers settings access until called."""
    _init_sentry(get_settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_settings()
        await init_pool(settings.database_url)
        # Initialize NLP backends — wrapped in try/except so the app can start
        # even when NLP libraries are not yet installed (dev convenience).
        try:
            init_nlp_backends()
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger(__name__).warning(
                "init_nlp_backends() failed — NLP answer validation unavailable"
            )
        yield
        await close_pool()

    _app = FastAPI(title="PolyglotSRS", lifespan=lifespan)

    _app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    _app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
    _app.include_router(languages_router, prefix="/api/languages", tags=["languages"])
    _app.include_router(curriculum_router, prefix="/api/curriculum", tags=["curriculum"])
    _app.include_router(review_router, prefix="/api/review", tags=["review"])
    _app.include_router(notes_router, prefix="/api/notes", tags=["notes"])
    _app.include_router(onboarding_router, prefix="/api/onboarding", tags=["onboarding"])
    _app.include_router(tutor_router, prefix="/api/tutor", tags=["tutor"])
    _app.include_router(contribute_router, prefix="/api/contribute", tags=["contribute"])
    _app.include_router(billing_router, prefix="/api/billing", tags=["billing"])
    _app.include_router(audio_router, prefix="/api/audio", tags=["audio"])

    @_app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return _app


def _add_cors(app: FastAPI) -> None:
    """Add CORS middleware. Called at startup when settings are available."""
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Module-level app for uvicorn. CORS is added here only if settings
# can be loaded (i.e., env vars are set). In tests, use create_app() directly.
app = create_app()
try:
    _add_cors(app)
except Exception:
    pass  # Settings not available (e.g., during import tests)
