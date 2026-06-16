"""Personal notes router — learn from your own text.

A learner pastes text, sees which words are already in the dictionary (with
meanings) vs new, and turns sentences into NLP-validated cloze cards that enter
the same SRS. All RLS-scoped to the owner.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.repositories.notes import (
    create_note,
    create_personal_card,
    known_vocab,
    list_notes,
)
from backend.repositories.pool import rls_connection
from backend.services.drills import validate_drill
from backend.services.extract import classify_words, make_cloze, split_sentences, tokenize
from backend.services.nlp import get_nlp

router = APIRouter()


class NoteCreate(BaseModel):
    language_id: str
    title: str | None = None
    content: str = Field(min_length=1, max_length=20000)


class ExtractRequest(BaseModel):
    language_id: str
    language_code: str
    text: str = Field(min_length=1, max_length=20000)


class PersonalCardCreate(BaseModel):
    language_id: str
    language_code: str
    sentence: str = Field(min_length=1, max_length=1000)
    answer: str = Field(min_length=1, max_length=200)
    translation: str = ""
    note_id: str | None = None


def _nlp_or_422(language_code: str):
    try:
        return get_nlp(language_code)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported language: {language_code}",
        ) from exc


@router.post("")
async def save_note(body: NoteCreate, user: dict = Depends(get_current_user)):
    """Save a learner's pasted text."""
    async with rls_connection(user["id"]) as conn:
        note_id = await create_note(
            conn, user["id"], body.language_id, body.title, body.content
        )
    return {"id": note_id}


@router.get("")
async def get_notes(language_id: str, user: dict = Depends(get_current_user)):
    """List the learner's saved notes for a language."""
    async with rls_connection(user["id"]) as conn:
        notes = await list_notes(conn, user["id"], language_id)
    return {"notes": notes}


@router.post("/extract")
async def extract(body: ExtractRequest, user: dict = Depends(get_current_user)):
    """Split text into sentences and flag which words are known (with meaning)."""
    nlp = _nlp_or_422(body.language_code)
    sentences = split_sentences(body.text)

    # Collect distinct candidate words across the whole text for one DB lookup.
    all_tokens = [t for s in sentences for t in tokenize(s)]
    normalized = sorted({nlp.normalize(t) for t in all_tokens if nlp.normalize(t)})

    async with rls_connection(user["id"]) as conn:
        defs = await known_vocab(conn, body.language_id, normalized)
    known = set(defs)

    out = []
    for sentence in sentences:
        words = classify_words(tokenize(sentence), known, nlp.normalize)
        for w in words:
            w["definition"] = defs.get(w["normalized"])
        out.append({"sentence": sentence, "words": words})
    return {"sentences": out}


@router.post("/cards")
async def create_card(body: PersonalCardCreate, user: dict = Depends(get_current_user)):
    """Make a cloze card from one of the learner's sentences (NLP-validated)."""
    _nlp_or_422(body.language_code)
    cloze = make_cloze(body.sentence, body.answer)
    if cloze is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The answer must be a whole word in the sentence.",
        )
    if not await validate_drill(body.language_code, cloze, body.answer):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The answer doesn't validate in this language.",
        )
    async with rls_connection(user["id"]) as conn:
        card_id = await create_personal_card(
            conn, user["id"], body.language_id, cloze, body.answer,
            body.translation, body.note_id,
        )
    return {"id": card_id, "sentence": cloze}
