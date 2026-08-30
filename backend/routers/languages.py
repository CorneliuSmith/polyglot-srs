"""Languages router — public language list."""

from __future__ import annotations

from fastapi import APIRouter

from backend.repositories.languages import get_all_languages
from backend.repositories.pool import get_pool
from backend.services.tts import voice_for

router = APIRouter()


@router.get("/")
async def list_languages():
    """Return all available languages. No auth required.

    has_tts says whether a neural voice exists for the language — the UI
    uses it to show the "we're collecting real recordings" note on
    languages (Jamaican Patois) where no synthetic voice can exist.
    """
    languages = await get_all_languages(get_pool())
    for lang in languages:
        lang["has_tts"] = voice_for(lang["code"]) is not None
    return languages
