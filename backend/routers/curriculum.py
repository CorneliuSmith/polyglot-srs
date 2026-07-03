"""Curriculum router — the browsable grammar path."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.dependencies import get_current_user
from backend.repositories.curriculum import (
    get_curriculum,
    get_curriculum_point,
    learn_point,
)
from backend.repositories.pool import rls_connection

router = APIRouter()


class LearnPointRequest(BaseModel):
    grammar_point_id: str


@router.get("/{language_id}")
async def curriculum(language_id: str, user: dict = Depends(get_current_user)):
    """The ordered grammar path for a language, with the learner's status."""
    async with rls_connection(user["id"]) as conn:
        points = await get_curriculum(conn, user["id"], language_id)
    return {"points": points}


@router.get("/point/{grammar_point_id}")
async def curriculum_point(
    grammar_point_id: str, user: dict = Depends(get_current_user)
):
    """Read one grammar point outside of reviews (the lesson-page view)."""
    async with rls_connection(user["id"]) as conn:
        point = await get_curriculum_point(conn, user["id"], grammar_point_id)
    if point is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Grammar point not found"
        )
    return point


@router.post("/learn")
async def learn(
    body: LearnPointRequest,
    user: dict = Depends(get_current_user),
):
    """Add one specific grammar point from the path to the learner's reviews."""
    async with rls_connection(user["id"]) as conn:
        result = await learn_point(conn, user["id"], body.grammar_point_id)
    if not result["added"] and result.get("reason") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Grammar point not found"
        )
    return result
