"""Auth router — JWT-based user info and profile management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.dependencies import get_current_user
from backend.repositories.pool import rls_connection

router = APIRouter()


class ProfileUpdate(BaseModel):
    batch_size: int | None = None
    ui_language: str | None = None
    active_language_id: str | None = None


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return current user info from JWT (no DB call needed)."""
    return user


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """Return user profile from DB."""
    async with rls_connection(user["id"]) as conn:
        row = await conn.fetchrow(
            "SELECT id, batch_size, ui_language, active_language_id, created_at, updated_at "
            "FROM user_profiles WHERE id = $1",
            user["id"],
        )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return dict(row)


@router.post("/profile")
async def upsert_profile(
    body: ProfileUpdate,
    user: dict = Depends(get_current_user),
):
    """Create or update user profile (upsert)."""
    async with rls_connection(user["id"]) as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO user_profiles (id, batch_size, ui_language, active_language_id)
            VALUES ($1, COALESCE($2, 5), COALESCE($3, 'en'), $4)
            ON CONFLICT (id) DO UPDATE SET
                batch_size = COALESCE($2, user_profiles.batch_size),
                ui_language = COALESCE($3, user_profiles.ui_language),
                active_language_id = COALESCE($4, user_profiles.active_language_id),
                updated_at = now()
            RETURNING id, batch_size, ui_language, active_language_id, created_at, updated_at
            """,
            user["id"],
            body.batch_size,
            body.ui_language,
            body.active_language_id,
        )
    return dict(row)
