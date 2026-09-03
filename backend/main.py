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
from backend.routers.feedback import router as feedback_router
from backend.routers.gym import router as gym_router
from backend.routers.languages import router as languages_router
from backend.routers.notes import router as notes_router
from backend.routers.onboarding import router as onboarding_router
from backend.routers.personal_decks import router as personal_decks_router
from backend.routers.reader import router as reader_router
from backend.routers.recommendations import router as recommendations_router
from backend.routers.review import router as review_router
from backend.routers.speak import router as speak_router
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
        import asyncio
        import logging

        settings = get_settings()
        await init_pool(settings.database_url)

        # Load NLP backends OFF the startup path. uvicorn does not accept any
        # requests — including the platform's health check — until lifespan
        # startup returns, and loading spaCy + per-language models for ~22
        # languages takes tens of seconds and grows with each language added.
        # Blocking here pushed cold starts past DigitalOcean's health-check
        # window, so every deploy failed with "container did not respond to
        # health checks" and the old image kept serving. Loading in a worker
        # thread lets the container report healthy immediately; answer
        # validation for a language simply isn't available for the few seconds
        # until its backend finishes registering.
        async def _load_nlp() -> None:
            try:
                await asyncio.to_thread(init_nlp_backends)
            except Exception:  # noqa: BLE001
                logging.getLogger(__name__).warning(
                    "init_nlp_backends() failed — NLP answer validation unavailable"
                )

        nlp_task = asyncio.create_task(_load_nlp())

        # Schema-drift check (post-incident): a deploy whose migrations
        # weren't applied used to surface only as a bare 500 from whichever
        # endpoint touched the new column. Say it plainly at boot instead.
        # Off the startup path and never fatal — diagnostics only.
        async def _check_schema() -> None:
            log = logging.getLogger(__name__)
            try:
                from backend.repositories.pool import privileged_connection
                from backend.services.schema_check import find_schema_drift

                async with privileged_connection() as conn:
                    drift = await find_schema_drift(conn)
            except Exception as exc:  # noqa: BLE001
                log.warning("Schema check could not run: %s", exc)
                return
            if drift["ok"]:
                return
            if drift.get("error"):
                log.warning("Schema check is blind: %s", drift["error"])
                return
            if not drift["initialized"]:
                log.error(
                    "DATABASE IS EMPTY — no migrations have been applied. "
                    "Run supabase/migrations/*.sql before serving traffic."
                )
                return
            log.error(
                "SCHEMA IS BEHIND THE CODE — %d object(s) missing. Apply these "
                "migrations: %s. Endpoints touching them will fail with 500 "
                "until then. Missing: %s",
                len(drift["missing"]),
                ", ".join(drift["missing_migrations"]),
                "; ".join(drift["missing"][:20]),
            )

        schema_task = asyncio.create_task(_check_schema())

        # Opt-in email review reminders: an in-process 15-minute sweep.
        # getattr default False so test FakeSettings (which lack the flag)
        # never start the loop.
        reminder_task = None
        digest_task = None
        if getattr(settings, "email_reminders_enabled", False):
            from backend.services.reminders import reminder_loop
            reminder_task = asyncio.create_task(reminder_loop())
            # The weekly digest is a SEPARATE opt-in with its own hourly
            # sweep, but it rides the same master switch: both are email, and
            # an operator turning email off means all of it.
            from backend.services.digest import digest_loop
            digest_task = asyncio.create_task(digest_loop())
        # Demand-driven support-locale translation. Same getattr-default-False
        # trick: test FakeSettings never start it. The loop itself is inert
        # unless an admin switched a language on AND live accounts use the
        # pair — see services/auto_translate.py.
        translate_task = None
        if getattr(settings, "auto_translate_loop_enabled", False):
            from backend.services.auto_translate import auto_translate_loop
            translate_task = asyncio.create_task(auto_translate_loop())
        # Daily prune of the append-only AI tables. Same getattr-default-
        # False trick, so test FakeSettings never start it.
        retention_task = None
        if getattr(settings, "retention_sweep_enabled", False):
            from backend.services.retention import retention_loop
            retention_task = asyncio.create_task(retention_loop())
        yield
        nlp_task.cancel()
        schema_task.cancel()
        if reminder_task is not None:
            reminder_task.cancel()
        if digest_task is not None:
            digest_task.cancel()
        if translate_task is not None:
            translate_task.cancel()
        if retention_task is not None:
            retention_task.cancel()
        await close_pool()

    _app = FastAPI(title="PolyglotSRS", lifespan=lifespan)

    _app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    _app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
    _app.include_router(languages_router, prefix="/api/languages", tags=["languages"])
    _app.include_router(curriculum_router, prefix="/api/curriculum", tags=["curriculum"])
    _app.include_router(review_router, prefix="/api/review", tags=["review"])
    _app.include_router(
        recommendations_router, prefix="/api/recommendations", tags=["recommendations"]
    )
    _app.include_router(notes_router, prefix="/api/notes", tags=["notes"])
    _app.include_router(
        personal_decks_router, prefix="/api/personal-decks", tags=["personal-decks"]
    )
    _app.include_router(onboarding_router, prefix="/api/onboarding", tags=["onboarding"])
    _app.include_router(tutor_router, prefix="/api/tutor", tags=["tutor"])
    _app.include_router(contribute_router, prefix="/api/contribute", tags=["contribute"])
    _app.include_router(billing_router, prefix="/api/billing", tags=["billing"])
    _app.include_router(audio_router, prefix="/api/audio", tags=["audio"])
    _app.include_router(reader_router, prefix="/api/reader", tags=["reader"])
    _app.include_router(gym_router, prefix="/api/gym", tags=["gym"])
    _app.include_router(speak_router, prefix="/api/speak", tags=["speak"])
    _app.include_router(feedback_router, prefix="/api/feedback", tags=["feedback"])

    @_app.get("/api/health")
    async def health():
        """Liveness, plus WHAT is live.

        The bare `{"status": "ok"}` this used to return could not settle
        "is the build with X deployed yet?" — which is the question every
        "I still don't see it" report turns into. `build` names the commit
        when the platform supplied one, the image's build time, and the
        newest migration this build expects; see backend/services/build_info.
        """
        from backend.services.build_info import build_info

        return {"status": "ok", "build": build_info()}

    @_app.get("/api/health/schema")
    async def health_schema():
        """Is the database schema in step with this build?

        Answers the "why is one endpoint 500ing after a deploy" question
        directly: lists the objects the code expects but the DB lacks, and
        the migration file that adds each. Migration filenames are already
        public in the repo, so there's nothing sensitive to leak here.
        """
        from backend.repositories.pool import privileged_connection
        from backend.services.schema_check import find_schema_drift

        try:
            async with privileged_connection() as conn:
                return await find_schema_drift(conn)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    # Belt-and-suspenders: some platform health checks default to "/". The
    # API otherwise has no root route (404 reads as unhealthy). Cheap 200 so
    # the probe passes regardless of how the path is configured.
    @_app.get("/")
    async def root():
        return {"status": "ok", "service": "polyglot-srs-api"}

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
