"""Personal decks router — name, organize, write and delete your own cards.

Decks are per-user folders over personal cloze cards: mints from the Tutor
and the Reader, plus cards the learner writes by hand. Their own material,
so they can remove it too.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.notes import create_personal_card
from backend.repositories.personal_decks import (
    build_cloze,
    create_deck,
    delete_deck,
    delete_personal_card,
    file_card,
    list_decks,
    list_personal_cards,
    rename_deck,
    store_card_translations,
    untranslated_cards,
)
from backend.repositories.pool import rls_connection
from backend.repositories.tutor import log_tutor_usage
from backend.services.allowance import get_allowance, reject_if_unavailable
from backend.services.models import resolve_model
from backend.services.translate import (
    generate_sentence_translations,
    translations_available,
)

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


# Personal cards are ONE learner's private text, so the background loop
# deliberately never sweeps them — spending the operator's key on content
# nobody else will ever see doesn't scale. They're filled on request from
# the learner's OWN allowance instead, which is why there are two endpoints:
# one that only reports what it would cost, and one that spends.

class TranslateCards(BaseModel):
    language_id: str


@router.get("/translation-status")
async def translation_status(
    language_id: str, user: dict = Depends(get_current_user),
):
    """How many personal cards don't read in the learner's language yet.

    Spends nothing. This is what lets the UI say "12 of your own cards can
    be translated, it will use 1 of your daily messages" BEFORE the learner
    agrees to it.
    """
    async with rls_connection(user["id"]) as conn:
        locale = await conn.fetchval(
            "SELECT support_locale FROM user_profiles WHERE id = $1", user["id"]
        )
        pending = await untranslated_cards(conn, language_id, locale or "en")
    allowance = await get_allowance(user["id"], language_id)
    return {
        "locale": locale,
        "pending": len(pending),
        "available": translations_available(),
        "remaining": allowance.get("remaining"),
        "unlimited": allowance.get("unlimited"),
    }


@router.post("/translate")
async def translate_cards(
    body: TranslateCards, user: dict = Depends(get_current_user),
):
    """Translate the learner's own cards into their support language.

    Charged to THEIR allowance (one unit, like a tutor message), because
    this is private content translated at their request — unlike course
    material, where one fill serves every learner of the pair.
    """
    allowance = await get_allowance(user["id"], body.language_id)
    reject_if_unavailable(allowance)
    if not translations_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "translation_unavailable"},
        )

    async with rls_connection(user["id"]) as conn:
        locale = await conn.fetchval(
            "SELECT support_locale FROM user_profiles WHERE id = $1", user["id"]
        )
        pending = await untranslated_cards(conn, body.language_id, locale or "en")
        if not pending:
            return {"translated": 0, "charged": False}
        locale_name = await conn.fetchval(
            "SELECT name FROM languages WHERE code = $1", locale
        )

    items = [{"i": i, "sentence": c["translation"]}
             for i, c in enumerate(pending)]
    results = await generate_sentence_translations(locale_name or locale, items)
    pairs = [(str(pending[r["i"]]["id"]), r["translation"])
             for r in results if r.get("translation")]

    async with rls_connection(user["id"]) as conn:
        stored = await store_card_translations(conn, pairs, locale)
        # Charged only when work was actually done — a run that produced
        # nothing must not cost the learner an allowance unit.
        if stored:
            await log_tutor_usage(
                conn, user["id"], body.language_id,
                resolve_model("translate"), kind="chat",
            )
    return {"translated": stored, "charged": bool(stored), "locale": locale}


# Learner-authored cards (owner request). Decks started as organization only
# — cards could be minted from the Tutor and the Reader but not written by
# hand, and never removed. Both are now the learner's to control: it is
# their own material.

class CardCreate(BaseModel):
    language_id: str
    sentence: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=100)
    translation: str = Field(default="", max_length=500)
    deck_id: str | None = None


@router.post("/cards", status_code=status.HTTP_201_CREATED)
async def add_card(body: CardCreate, user: dict = Depends(get_current_user)):
    """Write a cloze card by hand.

    The learner types a normal sentence and the word to practise; the blank
    is worked out here rather than asking them to type {{answer}}. A card
    whose answer isn't in its sentence would render with nothing blanked —
    the answer in plain sight — so that's refused with a reason instead of
    being stored broken.
    """
    sentence = build_cloze(body.sentence.strip(), body.answer)
    if sentence is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "answer_not_in_sentence"},
        )
    async with rls_connection(user["id"]) as conn:
        card_id = await create_personal_card(
            conn, user["id"], body.language_id, sentence, body.answer.strip(),
            body.translation.strip() or None, None, body.deck_id,
        )
    return {"id": card_id}


@router.delete("/cards/{card_id}")
async def remove_card(card_id: str, user: dict = Depends(get_current_user)):
    """Delete a personal card, scheduling row included."""
    async with rls_connection(user["id"]) as conn:
        if not await delete_personal_card(conn, card_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Card not found"
            )
    return {"ok": True}
