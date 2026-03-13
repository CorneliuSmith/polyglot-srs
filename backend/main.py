"""PolyglotSRS FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.repositories.pool import close_pool, init_pool
from backend.routers.auth import router as auth_router
from backend.routers.languages import router as languages_router
from backend.routers.review import router as review_router
from backend.services.nlp import init_nlp_backends


def create_app() -> FastAPI:
    """Application factory — defers settings access until called."""

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
    _app.include_router(languages_router, prefix="/api/languages", tags=["languages"])
    _app.include_router(review_router, prefix="/api/review", tags=["review"])

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
