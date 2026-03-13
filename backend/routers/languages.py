"""Languages router — public language list."""

from __future__ import annotations

from fastapi import APIRouter

from backend.repositories.languages import get_all_languages
from backend.repositories.pool import get_pool

router = APIRouter()


@router.get("/")
async def list_languages():
    """Return all available languages. No auth required."""
    return await get_all_languages(get_pool())
