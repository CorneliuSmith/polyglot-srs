"""Contributor router — language specialists author grammar explanations.

Authorization is enforced here (app layer): role reads run on the user's RLS
connection; content writes run on a privileged connection only after the
caller's role is verified for the target language.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.contributor import (
    add_drill,
    approve_explanation,
    can_contribute,
    create_grammar_point,
    delete_drill,
    get_point_language,
    get_point_language_and_code,
    get_roles,
    grant_role,
    is_admin,
    list_drills,
    list_grammar_points,
    save_explanation,
)
from backend.repositories.pool import privileged_connection, rls_connection
from backend.services.drills import validate_drill

router = APIRouter()


class ReferenceLink(BaseModel):
    title: str
    url: str


class ExplanationUpdate(BaseModel):
    explanation: str = Field(min_length=1)
    culture_note: str = ""
    references: list[ReferenceLink] = Field(default_factory=list)


class NewGrammarPoint(BaseModel):
    language_id: str
    title: str = Field(min_length=1, max_length=200)
    level: str | None = None
    explanation: str = ""
    culture_note: str = ""
    references: list[ReferenceLink] = Field(default_factory=list)


class NewDrill(BaseModel):
    sentence: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=200)
    translation: str = ""
    hint: str = ""


class RoleGrant(BaseModel):
    user_id: str
    language_id: str | None = None
    role: str


@router.get("/roles")
async def my_roles(user: dict = Depends(get_current_user)):
    """Return the caller's contributor roles (drives the contributor UI)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    return {"roles": roles, "is_admin": is_admin(roles)}


@router.get("/grammar")
async def grammar_for_language(
    language_id: str,
    user: dict = Depends(get_current_user),
):
    """List a language's grammar points for editing (role-gated)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        if not can_contribute(roles, language_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have a contributor role for this language",
            )
        points = await list_grammar_points(conn, language_id)
    return {"points": points, "is_admin": is_admin(roles)}


@router.put("/grammar/{point_id}")
async def update_grammar(
    point_id: str,
    body: ExplanationUpdate,
    user: dict = Depends(get_current_user),
):
    """Save a contributor explanation for a grammar point (pending review)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        language_id = await get_point_language(conn, point_id)
    if language_id is None:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    if not can_contribute(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    async with privileged_connection() as conn:
        await save_explanation(
            conn, point_id, body.explanation, body.culture_note, user["id"],
            references=[r.model_dump() for r in body.references],
        )
    return {"saved": True, "reviewed": False}


@router.post("/grammar")
async def create_point(
    body: NewGrammarPoint,
    user: dict = Depends(get_current_user),
):
    """Create a new grammar point (contributor for the language; pending review)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not can_contribute(roles, body.language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    async with privileged_connection() as conn:
        point_id = await create_grammar_point(
            conn, body.language_id, body.title, body.level,
            body.explanation or None, body.culture_note or None,
            [r.model_dump() for r in body.references], user["id"],
        )
    if point_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A grammar point with that title already exists",
        )
    return {"id": point_id}


@router.get("/grammar/{point_id}/drills")
async def get_drills(
    point_id: str,
    user: dict = Depends(get_current_user),
):
    """List a grammar point's drill sentences (role-gated)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        info = await get_point_language_and_code(conn, point_id)
        if info is None:
            raise HTTPException(status_code=404, detail="Grammar point not found")
        if not can_contribute(roles, info[0]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have a contributor role for this language",
            )
        drills = await list_drills(conn, point_id)
    return {"drills": drills}


@router.post("/grammar/{point_id}/drills")
async def create_drill(
    point_id: str,
    body: NewDrill,
    user: dict = Depends(get_current_user),
):
    """Add a drill sentence — NLP-validated so it's guaranteed answerable."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        info = await get_point_language_and_code(conn, point_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    language_id, language_code = info
    if not can_contribute(roles, language_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    if not await validate_drill(language_code, body.sentence, body.answer):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The sentence must contain the {{answer}} blank and the answer "
                "must validate in this language."
            ),
        )
    async with privileged_connection() as conn:
        drill_id = await add_drill(
            conn, point_id, body.sentence, body.answer,
            body.translation, body.hint,
        )
    return {"id": drill_id}


@router.delete("/grammar/{point_id}/drills/{drill_id}")
async def remove_drill(
    point_id: str,
    drill_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a drill sentence (role-gated by the point's language)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
        info = await get_point_language_and_code(conn, point_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    if not can_contribute(roles, info[0]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have a contributor role for this language",
        )
    async with privileged_connection() as conn:
        await delete_drill(conn, drill_id)
    return {"deleted": True}


@router.post("/grammar/{point_id}/approve")
async def approve_grammar(
    point_id: str,
    user: dict = Depends(get_current_user),
):
    """Approve a grammar explanation (admin-only)."""
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not is_admin(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can approve content",
        )
    async with privileged_connection() as conn:
        ok = await approve_explanation(conn, point_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Grammar point not found")
    return {"approved": True}


@router.post("/roles")
async def grant_contributor_role(
    body: RoleGrant,
    user: dict = Depends(get_current_user),
):
    """Grant a contributor/admin role to a user (admin-only)."""
    if body.role not in ("contributor", "admin"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="role must be 'contributor' or 'admin'",
        )
    async with rls_connection(user["id"]) as conn:
        roles = await get_roles(conn, user["id"])
    if not is_admin(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can grant roles",
        )
    async with privileged_connection() as conn:
        await grant_role(conn, body.user_id, body.language_id, body.role)
    return {"granted": True}
