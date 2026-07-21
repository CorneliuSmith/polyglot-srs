"""Personal decks router — name and organize your own cards (owner request).

Decks are per-user folders over personal cloze cards (Tutor/Reader mints).
Organization only: no learner-authored cards yet.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.personal_decks import (
    create_deck,
    delete_deck,
    file_card,
    list_decks,
    list_personal_cards,
    rename_deck,
)
from backend.repositories.pool import rls_connection

router = APIRouter()


class DeckCreate(BaseModel):
    language_id: str
    name: str = Field(min_length=1, max_length=60)


class DeckRename(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class CardFile(BaseModel):
    deck_id: str | None = None


@router.get("")
async def decks(language_id: str, user: dict = Depends(get_current_user)):
    async with rls_connection(user["id"]) as conn:
        return await list_decks(conn, language_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create(body: DeckCreate, user: dict = Depends(get_current_user)):
    async with rls_connection(user["id"]) as conn:
        deck_id = await create_deck(conn, user["id"], body.language_id, body.name.strip())
    return {"id": deck_id}


@router.patch("/{deck_id}")
async def rename(deck_id: str, body: DeckRename, user: dict = Depends(get_current_user)):
    async with rls_connection(user["id"]) as conn:
        if not await rename_deck(conn, deck_id, body.name.strip()):
            raise HTTPException(status_code=404, detail="Deck not found")
    return {"ok": True}


@router.delete("/{deck_id}")
async def remove(deck_id: str, user: dict = Depends(get_current_user)):
    """Cards are never deleted with the deck — they fall back to unfiled."""
    async with rls_connection(user["id"]) as conn:
        if not await delete_deck(conn, deck_id):
            raise HTTPException(status_code=404, detail="Deck not found")
    return {"ok": True}


@router.get("/cards")
async def cards(language_id: str, user: dict = Depends(get_current_user)):
    async with rls_connection(user["id"]) as conn:
        return await list_personal_cards(conn, language_id)


@router.patch("/cards/{card_id}")
async def move_card(card_id: str, body: CardFile, user: dict = Depends(get_current_user)):
    async with rls_connection(user["id"]) as conn:
        if not await file_card(conn, card_id, body.deck_id):
            raise HTTPException(status_code=404, detail="Card or deck not found")
    return {"ok": True}
