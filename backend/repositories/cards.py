"""User cards repository — RLS-protected queries."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import re
import unicodedata
from datetime import UTC, datetime

import asyncpg

from backend.repositories.curriculum import get_read_ref_keys, resolve_related
from backend.repositories.explicit_gate import fetch_explicit_gated
from backend.repositories.gym import get_gym_progress
from backend.services.auto_translate import (
    note_missing_content,
    table_present,
)
from backend.services.cell_glosses import cell_gloss
from backend.services.extract import ANSWER_MARKER, make_cloze
from backend.services.gym_manifest import nonstandard_point_titles
from backend.services.gym_weight import drill_weight
from backend.services.locale_guard import mark_locale_mismatches
from backend.services.readings import sentence_phonetics, sentence_reading
from backend.services.references import clean_references
from backend.services.srs_stages import stage_for

logger = logging.getLogger(__name__)


async def _effective_locale(
    conn: asyncpg.Connection, language_id: str, support_locale: str | None
) -> str:
    """The locale card content should render in.

    Every course honours the learner's support locale — a learner studying
    Turkish FROM Arabic wants Arabic glosses and Arabic drill translations
    just as much as an English-from-Spanish learner wants Spanish ones.
    Each localized field COALESCEs back to the authored English wherever
    the overlay row hasn't been filled yet (the auto-translate loop fills
    them on demand), so a missing translation degrades to English, never
    to a blank card.

    (conn/language_id are kept in the signature for call-site stability;
    the old rule needed the course code, this one doesn't.)
    """
    del conn, language_id
    if support_locale and support_locale != "en":
        return support_locale
    return "en"


# Per-process cache: whether an overlay table's migration has landed. Read
# paths that join a new table must degrade to the un-joined query until the
# owner applies the migration (the missing-migrations rule); to_regclass is
# one cheap catalog lookup that NEVER raises — which matters, because these
# reads run inside one transaction and a thrown UndefinedTableError would
# abort it and every query after it. Only presence is cached: a migration
# applied while the app runs is picked up on the next probe, no restart.
_TABLE_EXISTS: dict[str, bool] = {}


async def _table_exists(conn: asyncpg.Connection, table: str) -> bool:
    if _TABLE_EXISTS.get(table):
        return True
    present = bool(
        await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", table)
    )
    if present:
        _TABLE_EXISTS[table] = True
    return present


def _gpt_sql(has_gpt: bool, locale_param: str) -> dict[str, str]:
    """SQL fragments for the grammar_point_translations overlay: a join and
    per-field COALESCEs, collapsing to the plain columns until the table
    exists."""
    if has_gpt:
        return {
            "join": "LEFT JOIN grammar_point_translations gpt "
                    f"ON gpt.grammar_point_id = gp.id AND gpt.locale = {locale_param}",
            "title": "COALESCE(gpt.title, gp.title)",
            "culture_note": "COALESCE(gpt.culture_note, gp.culture_note)",
            "function_note": "COALESCE(gpt.function_note, gp.function_note)",
        }
    return {"join": "", "title": "gp.title", "culture_note": "gp.culture_note",
            "function_note": "gp.function_note"}


async def get_due_cards(
    conn: asyncpg.Connection,
    language_id: str,
    limit: int = 20,
    support_locale: str | None = None,
    card_type: str | None = None,
) -> list[dict]:
    """Return due cards for the authenticated user with full card content.

    Performs two queries (one for vocabulary, one for grammar) merged in Python
    and sorted by next_review ASC.  RLS automatically filters to the
    connection's user context.

    Vocabulary cards — type-the-word mode:
      sentence = definition text (no {{answer}} marker)
      correct_answer = vocabulary.word

    Grammar cards — fill-in-the-blank mode:
      sentence = drill sentence with {{answer}} marker
      correct_answer = grammar_points.title (placeholder for Phase 4)

    *support_locale* localizes card content on every course: definitions,
    drill hints/translations and explanations prefer that locale's overlay
    row and fall back per field to the authored English; example sentences
    prefer the row whose translation is in that locale, falling back per
    sentence to the English-translated row.

    *card_type* scopes the session ("Grammar Only" / "Vocab Only" reviews):
    'grammar' returns grammar drills alone; 'vocabulary' returns vocabulary
    plus personal cloze cards (the learner's own words live with vocab).
    """
    eff_locale = await _effective_locale(conn, language_id, support_locale)
    gpt = _gpt_sql(await _table_exists(conn, "grammar_point_translations"), "$3")
    want_vocab = card_type in (None, "vocabulary")
    want_grammar = card_type in (None, "grammar")
    # -- Vocabulary cards ---------------------------------------------------
    # Teach the word in context: a real example sentence with the word blanked
    # out (cloze), with its translation as a hint. All of the word's sentences
    # are fetched and each APPEARANCE shows one at random — never the sentence
    # shown last time (review_log.prompt_sentence) — so the learner practices
    # the word, not one memorized string. Falls back to the plain
    # definition -> type-the-word prompt when no sentence works.
    vocab_rows = [] if not want_vocab else await conn.fetch(
        """
        SELECT
            uc.id,
            uc.user_id,
            uc.language_id,
            uc.card_type,
            uc.card_id,
            v.word                          AS word,
            v.part_of_speech                AS part_of_speech,
            COALESCE(t.definition, t_en.definition) AS definition,
            ex.translation_locales          AS example_translation_locales,
            ex.sentences                    AS example_sentences,
            ex.translations                 AS example_translations,
            ex.glosses                      AS example_glosses,
            ex.transliterations             AS example_transliterations,
            lp.prompt_sentence              AS last_prompt,
            v.morphology                    AS morphology,
            v.alternatives                  AS alternatives,
            l.code                          AS language_code,
            uc.ease_factor,
            uc.interval,
            uc.repetitions,
            uc.streak,
            uc.lapses,
            uc.next_review
        FROM user_cards uc
        JOIN vocabulary v       ON uc.card_id = v.id
        JOIN languages l        ON uc.language_id = l.id
        LEFT JOIN translations t
               ON v.id = t.vocabulary_id AND t.locale = $3
        LEFT JOIN translations t_en
               ON v.id = t_en.vocabulary_id AND t_en.locale = 'en'
        LEFT JOIN LATERAL (
            SELECT
                array_agg(pes.sentence
                          ORDER BY pes.difficulty_rank ASC NULLS LAST, pes.id) AS sentences,
                array_agg(pes.translation
                          ORDER BY pes.difficulty_rank ASC NULLS LAST, pes.id) AS translations,
                array_agg(pes.gloss
                          ORDER BY pes.difficulty_rank ASC NULLS LAST, pes.id) AS glosses,
                array_agg(pes.transliteration
                          ORDER BY pes.difficulty_rank ASC NULLS LAST, pes.id) AS transliterations,
                -- Which language the chosen translation is ACTUALLY in. The
                -- row above may be the English fallback rather than the
                -- learner's locale, and without this the card cannot tell
                -- the difference — so it presented one as the other.
                array_agg(pes.translation_locale
                          ORDER BY pes.difficulty_rank ASC NULLS LAST, pes.id) AS translation_locales
            FROM (
                -- One row per sentence: prefer the learner's-locale
                -- translation, fall back to the English row when no locale
                -- rendering exists yet. Never a third, random language.
                SELECT DISTINCT ON (es.sentence)
                       es.sentence,
                       CASE WHEN es.translation_locale IN ($3, 'en')
                            THEN es.translation END AS translation,
                       es.gloss,
                       es.transliteration, es.difficulty_rank, es.id,
                       CASE WHEN es.translation_locale IN ($3, 'en')
                            THEN es.translation_locale END AS translation_locale
                FROM example_sentences es
                WHERE es.vocabulary_id = v.id
                  AND (es.translation_locale IN ($3, 'en')
                       -- ...or the sentence is ALREADY in the language the
                       -- learner reads, and needs no translation at all. The
                       -- English course is the one bank with zero 'en'
                       -- translation rows — every row translates English INTO
                       -- something else — so an en-locale learner of English
                       -- matched nothing and saw no examples anywhere. That is
                       -- the default locale, so it was most of them. Take any
                       -- row for them; the CASE above drops the foreign
                       -- translation, so no Turkish gloss appears under an
                       -- English sentence.
                       OR es.language_id IN (
                           SELECT id FROM languages WHERE code = $3))
                  -- Learners see reviewed content; a language whose policy is
                  -- 'ai_ok' (admin toggle) also serves verified AI content
                  -- without waiting for human sign-off. (Column is historically
                  -- named for grammar; it now governs all AI content.)
                  AND (es.reviewed
                       OR es.language_id IN (
                           SELECT id FROM languages
                            WHERE grammar_review_policy IN ('ai_ok', 'all')))
                ORDER BY es.sentence, (es.translation_locale = $3) DESC,
                         (es.translation_locale = 'en') DESC, es.id
            ) pes
        ) ex ON true
        LEFT JOIN LATERAL (
            SELECT rl.prompt_sentence
            FROM review_log rl
            WHERE rl.card_id = uc.id AND rl.prompt_sentence IS NOT NULL
            ORDER BY rl.created_at DESC
            LIMIT 1
        ) lp ON true
        WHERE uc.language_id = $1
          AND uc.card_type = 'vocabulary'
          AND uc.next_review <= now()
          AND uc.is_suspended = false
        ORDER BY uc.next_review ASC
        LIMIT $2
        """,
        language_id,
        limit,
        eff_locale,
    )

    # -- Grammar cards -------------------------------------------------------
    # Fill-in-the-blank drills. All of a point's drills are fetched and each
    # appearance shows one at random, never the last-shown (same as vocab).
    grammar_rows = [] if not want_grammar else await conn.fetch(
        f"""
        SELECT
            uc.id,
            uc.user_id,
            uc.language_id,
            uc.card_type,
            uc.card_id,
            {gpt["title"]}                  AS title,
            d.sentences                     AS drill_sentences,
            d.answers                       AS drill_answers,
            d.hints                         AS drill_hints,
            d.translations                  AS drill_translations,
            d.glosses                       AS drill_glosses,
            d.transliterations              AS drill_transliterations,
            lp.prompt_sentence              AS last_prompt,
            l.code                          AS language_code,
            uc.ease_factor,
            uc.interval,
            uc.repetitions,
            uc.streak,
            uc.lapses,
            uc.next_review
        FROM user_cards uc
        JOIN grammar_points gp  ON uc.card_id = gp.id
        JOIN languages l        ON uc.language_id = l.id
        {gpt["join"]}
        LEFT JOIN LATERAL (
            -- WP17: hint + translation prefer the learner's locale row
            -- (drill_hint_translations) and fall back to the authored
            -- English — same COALESCE rule as vocabulary definitions.
            SELECT
                array_agg(ds.sentence    ORDER BY ds.display_order, ds.id) AS sentences,
                array_agg(ds.answer      ORDER BY ds.display_order, ds.id) AS answers,
                array_agg(COALESCE(dht.hint, ds.hint)
                          ORDER BY ds.display_order, ds.id) AS hints,
                array_agg(COALESCE(dht.translation, ds.translation)
                          ORDER BY ds.display_order, ds.id) AS translations,
                array_agg(ds.gloss       ORDER BY ds.display_order, ds.id) AS glosses,
                array_agg(ds.transliteration ORDER BY ds.display_order, ds.id) AS transliterations
            FROM drill_sentences ds
            LEFT JOIN drill_hint_translations dht
                   ON dht.drill_id = ds.id AND dht.locale = $3
            WHERE ds.grammar_point_id = gp.id
              AND (ds.reviewed
                   OR gp.language_id IN (
                       SELECT id FROM languages
                        WHERE grammar_review_policy IN ('ai_ok', 'all')))
        ) d ON true
        LEFT JOIN LATERAL (
            SELECT rl.prompt_sentence
            FROM review_log rl
            WHERE rl.card_id = uc.id AND rl.prompt_sentence IS NOT NULL
            ORDER BY rl.created_at DESC
            LIMIT 1
        ) lp ON true
        WHERE uc.language_id = $1
          AND uc.card_type = 'grammar'
          AND uc.next_review <= now()
          AND uc.is_suspended = false
        ORDER BY uc.next_review ASC
        LIMIT $2
        """,
        language_id,
        limit,
        eff_locale,
    )

    # -- Personal cloze cards (learner's own text) --------------------------
    # Guarded: the locale-overlay migration (20260917) may not have landed,
    # and this is the review hot path — an unguarded read against a missing
    # table aborts the whole pooled transaction, taking every other card
    # down with it, not just the personal ones.
    personal_sql = """
        SELECT
            uc.id,
            uc.user_id,
            uc.language_id,
            uc.card_type,
            uc.card_id,
            cc.sentence                     AS sentence,
            cc.answer                       AS correct_answer,
            -- The final hint dot reveals the word itself — personal cards
            -- store no authored cue, and one translation-only dot left the
            -- card unanswerable when the sentence had many candidates.
            cc.answer                       AS hint,
            -- The learner's own locale rendering when they've asked for one
            -- (filled on demand from their allowance — the background loop
            -- never sweeps private content), else the language the card was
            -- minted in. LEFT JOIN, so a missing overlay is just a fallback.
            COALESCE(cct.translation, cc.translation) AS translation,
            NULL::jsonb                     AS morphology,
            NULL::text[]                    AS alternatives,
            l.code                          AS language_code,
            uc.ease_factor,
            uc.interval,
            uc.repetitions,
            uc.streak,
            uc.lapses,
            uc.next_review
        FROM user_cards uc
        JOIN user_cloze_cards cc ON uc.card_id = cc.id
        JOIN languages l         ON uc.language_id = l.id
        LEFT JOIN user_cloze_card_translations cct
               ON cct.cloze_id = cc.id AND cct.locale = $3
        WHERE uc.language_id = $1
          AND uc.card_type = 'personal'
          AND uc.next_review <= now()
          AND uc.is_suspended = false
        ORDER BY uc.next_review ASC
        LIMIT $2
    """
    # Pre-migration form: the card's minted-language translation, no overlay.
    # Spelled out rather than patched out of the string above — SQL surgery
    # breaks silently the moment either query is reformatted.
    personal_sql_no_overlay = """
        SELECT
            uc.id, uc.user_id, uc.language_id, uc.card_type, uc.card_id,
            cc.sentence AS sentence,
            cc.answer   AS correct_answer,
            cc.answer   AS hint,
            cc.translation AS translation,
            NULL::jsonb  AS morphology,
            NULL::text[] AS alternatives,
            l.code       AS language_code,
            uc.ease_factor, uc.interval, uc.repetitions,
            uc.streak, uc.lapses, uc.next_review
        FROM user_cards uc
        JOIN user_cloze_cards cc ON uc.card_id = cc.id
        JOIN languages l         ON uc.language_id = l.id
        WHERE uc.language_id = $1
          AND uc.card_type = 'personal'
          AND uc.next_review <= now()
          AND uc.is_suspended = false
        ORDER BY uc.next_review ASC
        LIMIT $2
    """
    personal_rows = []
    if want_vocab:
        # PROBED, never caught. A query naming a missing table doesn't just
        # fail itself — the pooled connection runs one transaction, so the
        # throw aborts it and every later query in the request dies with it,
        # fallback included. Catching the error here took the whole review
        # session down: the due-cards request 500'd and the page sat on
        # "Loading cards…" forever. to_regclass never raises.
        overlay = await table_present(conn, "user_cloze_card_translations")
        personal_rows = await conn.fetch(
            *( (personal_sql, language_id, limit, eff_locale) if overlay
               else (personal_sql_no_overlay, language_id, limit) )
        )

    # Per-sentence history for the gap-hunting rotation (one query for the
    # whole batch).
    stats = await _sentence_stats(
        conn, [str(r["id"]) for r in [*vocab_rows, *grammar_rows]]
    )

    # Anything this session serves with an English fallback becomes demand:
    # the auto-translate loop wakes and fills it before its ordered sweep.
    await note_missing_content(
        conn, eff_locale,
        vocab_ids=[r["card_id"] for r in vocab_rows],
        grammar_ids=[r["card_id"] for r in grammar_rows],
    )

    # Merge and sort by next_review
    combined = (
        [_vocab_card(r, stats.get(str(r["id"]), {}), eff_locale)
         for r in vocab_rows]
        + [_grammar_card(r, stats.get(str(r["id"]), {})) for r in grammar_rows]
        + [dict(r) for r in personal_rows]
    )
    combined.sort(key=lambda r: r["next_review"])
    return [mark_locale_mismatches(c, eff_locale) for c in combined[:limit]]


def _srs_fields(r: asyncpg.Record) -> dict:
    return {
        "id": r["id"],
        "user_id": r["user_id"],
        "language_id": r["language_id"],
        "card_type": r["card_type"],
        "card_id": r["card_id"],
        "language_code": r["language_code"],
        "ease_factor": r["ease_factor"],
        "interval": r["interval"],
        "repetitions": r["repetitions"],
        "streak": r["streak"],
        "lapses": r["lapses"],
        "next_review": r["next_review"],
    }


def _stable_pick(n: int, key: str) -> int:
    """Deterministic index in [0, n): same card state -> same pick.

    Sentences rotate per APPEARANCE, not per page load: the key folds in the
    card's review counters and the last-shown prompt, so a reload mid-review
    shows the same sentence, while an actual recorded review advances the
    rotation (counters and last_prompt change).
    """
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % n


def _rotation_key(r: asyncpg.Record) -> str:
    return f"{r['id']}:{r['repetitions']}:{r['lapses']}:{r['last_prompt'] or ''}"


async def _sentence_stats(
    conn: asyncpg.Connection, card_ids: list[str]
) -> dict[str, dict[str, tuple[int, int]]]:
    """Per-sentence (times shown, times missed) for each card, from the log.

    This is what makes a paradigm point behave like N questions instead of
    one: the rotation below uses it to hunt the sentences — and therefore the
    paradigm cells — the learner hasn't seen or keeps missing.
    """
    if not card_ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT card_id, prompt_sentence,
               count(*) AS seen,
               count(*) FILTER (WHERE answer_result IN ('wrong', 'wrong_form'))
                   AS misses
        FROM review_log
        WHERE card_id = ANY($1::uuid[]) AND prompt_sentence IS NOT NULL
        GROUP BY card_id, prompt_sentence
        """,
        card_ids,
    )
    out: dict[str, dict[str, tuple[int, int]]] = {}
    for r in rows:
        out.setdefault(str(r["card_id"]), {})[r["prompt_sentence"]] = (
            int(r["seen"]), int(r["misses"]),
        )
    return out


def _pick_index(
    prompts: list[str],
    last_prompt: str | None,
    stats: dict[str, tuple[int, int]],
    key: str,
) -> int:
    """Gap-hunting rotation: unseen first, then most-missed, else uniform.

    Never repeats the last-shown prompt (when there's a choice), and every
    branch resolves via the same deterministic hash, so reloads mid-review
    stay stable and the pick only advances when a review is recorded.
    """
    idxs = [i for i, p in enumerate(prompts) if p != last_prompt] or list(
        range(len(prompts))
    )
    unseen = [i for i in idxs if prompts[i] not in stats]
    if unseen:
        pool = unseen
    else:
        missed = [i for i in idxs if stats[prompts[i]][1] > 0]
        if missed:
            def miss_rate(i: int) -> float:
                seen, misses = stats[prompts[i]]
                return misses / seen

            worst = max(miss_rate(i) for i in missed)
            pool = [i for i in missed if miss_rate(i) == worst]
        else:
            pool = idxs
    return pool[_stable_pick(len(pool), key)]


def _vocab_card(r: asyncpg.Record, stats: dict[str, tuple[int, int]],
                eff_locale: str = "en") -> dict:
    """Shape a vocabulary row into a card, preferring a cloze example sentence.

    The sentence changes on every APPEARANCE of the card (Bunpro-style): a
    deterministic, gap-hunting pick among the word's sentences — stable
    across page reloads — that prefers sentences never shown, then the ones
    the learner keeps missing, and never repeats the one shown last time
    (review_log.prompt_sentence). Sentences where the word is inflected
    beyond a whole-word match are skipped by make_cloze. Falls back to the
    definition -> type-the-word prompt when nothing clozes.
    """
    word = r["word"]
    sentences = r["example_sentences"] or []
    translations = r["example_translations"] or []
    glosses = r["example_glosses"] or []
    translits = r["example_transliterations"] or []
    locales = r.get("example_translation_locales") or []
    candidates = []
    for i, raw in enumerate(sentences):
        cloze = make_cloze(raw, word)
        if cloze:
            candidates.append((
                cloze,
                translations[i] if i < len(translations) else None,
                glosses[i] if i < len(glosses) else None,
                translits[i] if i < len(translits) else None,
                locales[i] if i < len(locales) else None,
            ))
    sentence, translation, hint = (r["definition"] or word), None, None
    gloss, transliteration, translation_locale = None, None, None
    phonetics = None
    if candidates:
        idx = _pick_index(
            [c[0] for c in candidates], r["last_prompt"], stats, _rotation_key(r)
        )
        (sentence, translation, gloss, transliteration,
         translation_locale) = candidates[idx]
        hint = r["definition"]
        # The stored column is empty for most of the non-Latin corpus — ru, hi,
        # el, ko and th have no sentence romanisation at all, and he/fa have it
        # on ~5% of rows. `sentence_reading` could have covered ru and hi the
        # whole time, but its only caller was the grammar page, so the same
        # sentence showed a reading there and bare Cyrillic on the review card.
        # Computed from the CLOZE, never the raw sentence: romanising the raw
        # text spells the hidden word in Latin letters, which is exactly the
        # answer leak that put 926 rows on the board (CHECKS.md §11).
        if not (transliteration or "").strip():
            transliteration = sentence_reading(sentence, r["language_code"])
        # ...and the pronunciation line beneath it, from the CLOZE for the same
        # reason: phonetics of the raw sentence would spell the hidden word.
        phonetics = sentence_phonetics(sentence, r["language_code"])
    return {
        **_srs_fields(r),
        "sentence": sentence,
        "correct_answer": word,
        "hint": hint,
        "translation": translation,
        # The language the translation above is actually written in, and a
        # flag the card can act on. A learner asking for Spanish who is
        # handed the English fallback (or nothing) should be told the
        # translation is on its way — not shown another language under a
        # "TRADUCCIÓN" label, which is exactly what used to happen.
        "translation_locale": translation_locale,
        "translation_pending": bool(
            translation and translation_locale
            and translation_locale != eff_locale
        ),
        "gloss": gloss,
        "transliteration": transliteration,
        "phonetics": phonetics,
        "morphology": r["morphology"],
        "alternatives": r["alternatives"],
        # 'letter' marks an alphabet-deck card; the input surfaces switch to
        # letter mode (no ㅇ-seat for a lone Korean vowel, no Thai อ carrier).
        "part_of_speech": r["part_of_speech"],
    }


def _grammar_card(r: asyncpg.Record, stats: dict[str, tuple[int, int]]) -> dict:
    """Shape a grammar row into a fill-in-the-blank card, rotating drills.

    The drill changes on every APPEARANCE (deterministic, stable across page
    reloads, never the last-shown), gap-hunting across the point's drills:
    a paradigm point (subject pronouns, a conjugation table) is really N
    questions wearing one card, so unseen cells come first and missed cells
    come back until they stick. Points without drills fall back to a
    type-the-title card for legacy rows only — new learns are gated on having
    drills, so this shouldn't be reachable for fresh content.
    """
    drills = r["drill_sentences"] or []
    gloss, transliteration = None, None
    if drills:
        idx = _pick_index(list(drills), r["last_prompt"], stats, _rotation_key(r))
        sentence = drills[idx]
        answer = (r["drill_answers"] or [None])[idx]
        hint = (r["drill_hints"] or [None] * len(drills))[idx]
        translation = (r["drill_translations"] or [None] * len(drills))[idx]
        gloss = (r["drill_glosses"] or [None] * len(drills))[idx]
        transliteration = (r["drill_transliterations"] or [None] * len(drills))[idx]
    else:
        sentence, answer, hint, translation = r["title"], r["title"], None, None
    return {
        **_srs_fields(r),
        "sentence": sentence,
        "correct_answer": answer,
        "hint": hint,
        "translation": translation,
        "gloss": gloss,
        "transliteration": transliteration,
        "morphology": None,
        "alternatives": None,
    }


def _interleave_typed(
    grammar_ids: list, vocab_ids: list, limit: int
) -> list[tuple[str, object]]:
    """Round-robin a grammar and a vocab candidate list into one ordered list
    of (card_type, id), grammar first each round. When one type runs out the
    other keeps filling, so a lopsided queue still reaches *limit* if it can."""
    out: list[tuple[str, object]] = []
    i = 0
    while len(out) < limit and (i < len(grammar_ids) or i < len(vocab_ids)):
        if i < len(grammar_ids):
            out.append(("grammar", grammar_ids[i]))
            if len(out) >= limit:
                break
        if i < len(vocab_ids):
            out.append(("vocabulary", vocab_ids[i]))
            if len(out) >= limit:
                break
        i += 1
    return out


async def _select_vocab_candidate_ids(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int,
    level: str | None,
) -> list:
    """Vocabulary the user hasn't started, ranked round-robin across the queued
    level decks (Nth of every level before the (N+1)th; frequency within a
    level). DISTINCT guards against a word matching several subscribed lists.
    With *level* set, it's just that deck in frequency order.

    Explicit words are excluded unless the learner opted in. The preference
    is read inside the query rather than passed down, so every caller of
    every learn-batch variant gets the filter without threading a flag
    through five signatures — and no future caller can forget it.
    """
    try:
        return await _vocab_candidates(
            conn, user_id, language_id, batch_size, level, explicit_filter=True
        )
    except asyncpg.exceptions.UndefinedColumnError:
        # Migration 20260910 hasn't landed. Serve vocabulary rather than
        # fail the session; nothing is marked explicit yet either, so the
        # filter would have been a no-op regardless.
        return await _vocab_candidates(
            conn, user_id, language_id, batch_size, level, explicit_filter=False
        )


async def _vocab_candidates(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int,
    level: str | None,
    *,
    explicit_filter: bool,
) -> list:
    explicit_clause = (
        """
              -- Slurs and strong profanity are frequent (Spanish *puta* is
              -- rank 505) and therefore reach beginners early. Hidden unless
              -- the learner asked for them.
              AND (NOT v.is_explicit
                   OR EXISTS (SELECT 1 FROM user_profiles up
                               WHERE up.id = $1
                                 AND up.allow_explicit_content))
        """
        if explicit_filter
        else ""
    )
    rows = await conn.fetch(
        """
        WITH candidates AS (
            SELECT DISTINCT v.id AS id, v.level AS level,
                            v.frequency_rank AS frequency_rank
            FROM vocabulary v
            JOIN content_lists cl
                   ON v.language_id = cl.language_id
                  AND cl.list_type = 'vocabulary'
                  AND (cl.level IS NULL OR cl.level = v.level)
            JOIN user_content_subscriptions ucs
                   ON cl.id = ucs.content_list_id
                  AND ucs.user_id = $1
            WHERE v.language_id = $2
              AND ($4::text IS NULL OR v.level = $4)
              -- A provisional AI-estimated level stays out of the learnable
              -- pool until a reviewer confirms it — unless the language's
              -- policy is 'ai_ok' (same gate as generated drills/examples).
              AND (v.level_source <> 'ai'
                   OR EXISTS (SELECT 1 FROM languages lp
                               WHERE lp.id = v.language_id
                                 AND lp.grammar_review_policy IN ('ai_ok', 'all')))
              -- exclude items already in the deck, EXCEPT suspended
              -- never-reviewed ones: abandoned walkthroughs to be re-taught
              AND v.id NOT IN (
                  SELECT card_id FROM user_cards
                  WHERE user_id = $1 AND card_type = 'vocabulary'
                    AND NOT (is_suspended AND repetitions = 0)
              )
              {explicit_clause}
        ),
        ranked AS (
            SELECT id, level,
                   row_number() OVER (
                       PARTITION BY level
                       ORDER BY frequency_rank ASC NULLS LAST, id
                   ) AS rn
            FROM candidates
        )
        SELECT id
        FROM ranked
        ORDER BY rn ASC, level ASC NULLS LAST
        LIMIT $3
        """.replace("{explicit_clause}", explicit_clause),
        user_id,
        language_id,
        batch_size,
        level,
    )
    return [r["id"] for r in rows]


async def _select_grammar_candidate_ids(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int,
    level: str | None,
) -> list:
    """Grammar points the user hasn't started, ranked round-robin across the
    queued level decks (display_order within a level), honoring the review
    policy and skipping points with no drills."""
    rows = await conn.fetch(
        """
        WITH candidates AS (
            SELECT DISTINCT gp.id AS id, gp.level AS level,
                            gp.display_order AS display_order
            FROM grammar_points gp
            JOIN languages l ON gp.language_id = l.id
            JOIN content_lists cl
                   ON gp.language_id = cl.language_id
                  AND cl.list_type = 'grammar'
                  AND (cl.level IS NULL OR cl.level = gp.level)
            JOIN user_content_subscriptions ucs
                   ON cl.id = ucs.content_list_id
                  AND ucs.user_id = $1
            WHERE gp.language_id = $2
              -- review policy: strict = reviewed only; ai_ok = also AI-passed
              AND (CASE l.grammar_review_policy
                    WHEN 'all'  THEN true
                    WHEN 'both' THEN (gp.reviewed AND gp.ai_check_status = 'pass')
                    WHEN 'ai_ok' THEN (gp.reviewed OR gp.ai_check_status = 'pass')
                    ELSE gp.reviewed END)
              -- a point with no drills has nothing to quiz — never learnable
              AND EXISTS (
                  SELECT 1 FROM drill_sentences ds WHERE ds.grammar_point_id = gp.id
              )
              AND ($4::text IS NULL OR gp.level = $4)
              AND gp.id NOT IN (
                  SELECT card_id FROM user_cards
                  WHERE user_id = $1 AND card_type = 'grammar'
                    AND NOT (is_suspended AND repetitions = 0)
              )
        ),
        ranked AS (
            SELECT id, level,
                   row_number() OVER (
                       PARTITION BY level
                       ORDER BY display_order ASC, id
                   ) AS rn
            FROM candidates
        )
        SELECT id
        FROM ranked
        ORDER BY rn ASC, level ASC NULLS LAST
        LIMIT $3
        """,
        user_id,
        language_id,
        batch_size,
        level,
    )
    return [r["id"] for r in rows]


async def _insert_learn_cards(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    typed_ids: list[tuple[str, object]],
) -> dict:
    """Insert new user_cards SUSPENDED, in the given order — they enter the
    review queue only when the learner finishes the lesson walkthrough
    (confirm_learn_batch), so an abandoned page leaks nothing.

    ON CONFLICT: two learn calls racing (e.g. React StrictMode double-firing)
    can both select the same candidates; the WHERE keeps the update to
    re-teachable rows so an active card is never re-suspended. *typed_ids* is
    a list of (card_type, card_id) so a mixed grammar+vocab batch keeps its
    interleaved order."""
    inserted_ids: list[str] = []
    for card_type, card_id in typed_ids:
        row = await conn.fetchrow(
            """
            INSERT INTO user_cards
                (user_id, language_id, card_type, card_id,
                 ease_factor, interval, repetitions, streak, lapses,
                 next_review, is_suspended)
            VALUES
                ($1, $2, $4, $3, 2.5, 0, 0, 0, 0, now(), true)
            ON CONFLICT (user_id, card_type, card_id) DO UPDATE
                SET is_suspended = true
                WHERE user_cards.is_suspended AND user_cards.repetitions = 0
            RETURNING id
            """,
            user_id,
            language_id,
            card_id,
            card_type,
        )
        if row is not None:
            inserted_ids.append(str(row["id"]))
    return {"added": len(inserted_ids), "items": inserted_ids}


# How far ahead of the learner the translations run: when a learn session
# starts, this session's content PLUS the next few sessions' worth is queued
# for translation — so by the time those cards are learned (and long before
# they come up for review) the locale overlays already exist.
LEARN_LOOKAHEAD_SESSIONS = 3


# A brand-new (course, locale) pair has NOTHING translated, so the first
# session is the one most likely to stall. Queue a whole level's worth then,
# rather than the usual few sessions.
FIRST_RUN_SESSIONS = 10
# When the learner's own queue is nearly spent, they're about to move up a
# level — pull the next one in so the step up isn't a fresh English wall.
NEXT_LEVEL_SESSIONS = 4
_CEFR = ("A0", "A1", "A2", "B1", "B2", "C1", "C2")


async def _next_level_ids(
    conn: asyncpg.Connection, user_id: str, language_id: str, span: int,
) -> tuple[list, list]:
    """Candidates from the level ABOVE whatever the learner is working on.

    Deliberately ignores subscriptions: the point is the level they haven't
    reached yet, which by definition isn't queued. Queuing costs nothing on
    its own — the loop's per-cycle budget is what caps spend — so this only
    changes the ORDER work happens in, never the amount.
    """
    current = await conn.fetchval(
        """
        SELECT max(array_position($3::text[], cl.level))
        FROM user_content_subscriptions ucs
        JOIN content_lists cl ON cl.id = ucs.content_list_id
        WHERE ucs.user_id = $1 AND cl.language_id = $2 AND cl.level IS NOT NULL
        """,
        user_id, language_id, list(_CEFR),
    )
    if not current or current >= len(_CEFR):
        return [], []
    nxt = _CEFR[current]  # array_position is 1-based, so this IS the next one
    vocab = await conn.fetch(
        """SELECT id FROM vocabulary
            WHERE language_id = $1 AND level = $2
            ORDER BY frequency_rank NULLS LAST LIMIT $3""",
        language_id, nxt, span,
    )
    grammar = await conn.fetch(
        """SELECT id FROM grammar_points
            WHERE language_id = $1 AND level = $2
            ORDER BY display_order NULLS LAST LIMIT $3""",
        language_id, nxt, span,
    )
    return [r["id"] for r in vocab], [r["id"] for r in grammar]


async def start_batch_ids(
    conn: asyncpg.Connection, user_id: str, language_id: str,
    batch_size: int = 10,
) -> tuple[list, list]:
    """The ids of the learn batch a waiting learner is about to meet —
    what the inline fill translates first. Same selectors readiness
    scores, so the fill and the gate are looking at the same cards."""
    batch = max(batch_size, 1)
    vocab = await _select_vocab_candidate_ids(
        conn, user_id, language_id, batch, None)
    grammar = await _select_grammar_candidate_ids(
        conn, user_id, language_id, batch, None)
    return vocab, grammar


async def due_batch_ids(
    conn: asyncpg.Connection, user_id: str, language_id: str,
    batch_size: int = 10,
) -> tuple[list, list]:
    """The ids of the REVIEW queue a waiting learner is about to meet.

    The learn batch and the review queue are different cards — the learn
    selector returns vocabulary the learner has NOT started, which is by
    definition everything the review queue is not. The wait screen scores
    them separately and the review session gates on its own half, so the
    inline fill has to be able to aim at this half too. Filling the learn
    batch on behalf of a stalled review session translated words the
    learner wasn't waiting on, and the gate it was meant to open never
    moved: the wait sat at 0 of 3 while the match game beside it filled up
    with the learn batch's freshly translated words, which is what the
    owner was looking at.
    """
    batch = max(batch_size, 1)
    due = await conn.fetch(
        """SELECT card_type, card_id FROM user_cards
            WHERE user_id = $1 AND language_id = $2
              AND next_review <= now() AND is_suspended = false
            ORDER BY next_review LIMIT $3""",
        user_id, language_id, batch,
    )
    return (
        [r["card_id"] for r in due if r["card_type"] == "vocabulary"],
        [r["card_id"] for r in due if r["card_type"] == "grammar"],
    )


async def pretranslate_upcoming(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int = 10,
    level: str | None = None,
) -> None:
    """Queue translation demand for the content this learner is ABOUT to
    meet, ahead of any card rendering. Runs at learn-session start and when
    a learner picks a course + support locale.

    Three tiers of lookahead, all of which only REORDER the loop's work
    (the per-cycle budget caps spend either way):
      - the usual few sessions of their own queue;
      - a whole level's worth on a pair with nothing translated yet, since
        that first session is the one that would otherwise stall;
      - the next CEFR level once their own queue runs low, so moving up a
        level doesn't land them on a fresh wall of English.

    Never raises — pre-warming must not break the session it warms.
    """
    try:
        locale = await conn.fetchval(
            "SELECT COALESCE(support_locale, NULLIF(ui_language, 'en')) "
            "FROM user_profiles WHERE id = $1", user_id
        )
        if not locale or locale == "en":
            return
        batch = max(batch_size, 1)
        first_run = not await conn.fetchval(
            """SELECT EXISTS (SELECT 1 FROM translations t
                               JOIN vocabulary v ON v.id = t.vocabulary_id
                              WHERE v.language_id = $1 AND t.locale = $2)""",
            language_id, locale,
        )
        sessions = FIRST_RUN_SESSIONS if first_run else 1 + LEARN_LOOKAHEAD_SESSIONS
        span = batch * sessions
        vocab = await _select_vocab_candidate_ids(
            conn, user_id, language_id, span, level
        )
        grammar = await _select_grammar_candidate_ids(
            conn, user_id, language_id, span, level
        )
        # Their own queue is nearly spent → they're about to move up.
        if level is None and (len(vocab) < span or len(grammar) < span):
            up_v, up_g = await _next_level_ids(
                conn, user_id, language_id, batch * NEXT_LEVEL_SESSIONS
            )
            vocab, grammar = vocab + up_v, grammar + up_g
        # ...and the cards already due. Every selector above returns work
        # the learner has NOT started, so on a fresh support locale the
        # review queue — the half a returning learner actually opens — had
        # no demand recorded for it at all.
        if level is None:
            due_v, due_g = await due_batch_ids(conn, user_id, language_id, span)
            vocab, grammar = vocab + due_v, grammar + due_g
        await note_missing_content(conn, locale,
                                   vocab_ids=vocab, grammar_ids=grammar)
    except Exception as exc:  # noqa: BLE001 — never break the learn flow
        logger.debug("pretranslate lookahead skipped: %s", exc)


# How much of a session must already read in the learner's language before
# it's worth starting. Not 100%: the rest fills while they work through the
# early cards, so holding out for a perfect session wastes their time.
READY_ENOUGH = 0.6

# ...but the percentage is not the only way in, and on its own it was the
# wrong gate. It measures the WHOLE batch, glosses and example sentences
# together, so a learner could sit at 5% with three perfectly good cards
# already waiting for them and no way to begin. A session only needs enough
# cards to start on; the rest lands while they work, and the learn loop
# re-serves its lessons on every advance so it appears without a restart.
#
# A card counts here when the thing you read FIRST is in your language — a
# word's gloss, a grammar point's explanation. Example sentences are most
# of what a vocabulary card shows and they still drive the percentage, but
# they must never be what keeps someone out of a session.
START_CARDS = 3


async def session_readiness(
    conn: asyncpg.Connection, user_id: str, language_id: str,
    batch_size: int = 10,
) -> dict:
    """How much of what this learner is about to see already reads in their
    language — for the "you're first here" wait screen.

    Reports the next LEARN batch and the due REVIEW queue separately, since
    a learner can be ready for one and not the other. `ready_enough` is the
    signal the UI actually acts on: start now, or offer to wait.
    """
    locale = await conn.fetchval(
        "SELECT COALESCE(support_locale, NULLIF(ui_language, 'en')) "
            "FROM user_profiles WHERE id = $1", user_id
    )
    out: dict = {"locale": locale, "threshold": READY_ENOUGH}
    if not locale or locale == "en":
        # Nothing to translate: English IS the content.
        for key in ("learn", "review"):
            out[key] = {"total": 0, "ready": 0, "pct": 1.0, "ready_enough": True}
        return out

    # Learning a language THROUGH itself: the loop deliberately never
    # renders example sentences, because doing so reproduces the drill
    # sentence with the blank filled in (auto_translate.self_pair). Scoring
    # those points anyway capped readiness below the start threshold
    # forever — the wait screen could never advance on its own.
    course_code = await conn.fetchval(
        "SELECT code FROM languages WHERE id = $1", language_id)
    scores_examples = course_code != locale

    batch = max(batch_size, 1)
    learn_v = await _select_vocab_candidate_ids(
        conn, user_id, language_id, batch, None)
    learn_g = await _select_grammar_candidate_ids(
        conn, user_id, language_id, batch, None)
    review_v, review_g = await due_batch_ids(conn, user_id, language_id, batch)

    for key, vocab_ids, grammar_ids in (
        ("learn", learn_v, learn_g), ("review", review_v, review_g),
    ):
        # A word counts twice — its gloss AND its example meaning lines —
        # because the sentences are most of what a learner READS on a
        # vocabulary card, and scoring only glosses reported "ready" while
        # every example was still English. Except on the self-pair, where
        # the second point is for work that will never happen.
        per_word = 2 if scores_examples else 1
        total = len(vocab_ids) * per_word + len(grammar_ids)
        ready = 0
        # Cards a learner could start on right now, counted separately from
        # the percentage: this is what decides whether they are let in.
        cards_ready = 0
        if vocab_ids:
            glossed = int(await conn.fetchval(
                """SELECT count(*) FROM translations
                    WHERE vocabulary_id = ANY($1::uuid[]) AND locale = $2""",
                list(vocab_ids), locale) or 0)
            ready += glossed
            cards_ready += glossed
            # Words with nothing left to translate — phrased as "no reviewed
            # English example is missing its locale sibling" so a word that
            # simply HAS no examples counts as done, rather than holding the
            # score below 100% forever. Mirrors the demand detector exactly.
            ready += 0 if not scores_examples else int(await conn.fetchval(
                """SELECT count(*) FROM unnest($1::uuid[]) AS w(id)
                    WHERE NOT EXISTS (
                        SELECT 1 FROM example_sentences es
                         WHERE es.vocabulary_id = w.id
                           AND es.translation_locale = 'en' AND es.reviewed
                           AND es.translation IS NOT NULL AND es.translation <> ''
                           AND NOT EXISTS (
                               SELECT 1 FROM example_sentences es2
                                WHERE es2.vocabulary_id = es.vocabulary_id
                                  AND es2.sentence = es.sentence
                                  AND es2.translation_locale = $2))""",
                list(vocab_ids), locale) or 0)
        if grammar_ids:
            # A grammar card's body is its explanation; that's what a
            # learner reads first and what takes longest to render.
            explained = int(await conn.fetchval(
                """SELECT count(*) FROM explanation_translations
                    WHERE grammar_point_id = ANY($1::uuid[]) AND locale = $2""",
                list(grammar_ids), locale) or 0)
            ready += explained
            cards_ready += explained
        pct = 1.0 if total == 0 else ready / total
        cards = len(vocab_ids) + len(grammar_ids)
        # Either way in: a few cards ready to work through, or a batch far
        # enough along overall. The card count is what rescues someone from
        # a low percentage they can do nothing about — glosses land before
        # sentences, so three usable cards routinely exist at 20%.
        enough_cards = cards > 0 and cards_ready >= min(START_CARDS, cards)
        out[key] = {
            "total": total, "ready": ready, "pct": round(pct, 3),
            "cards": cards, "cards_ready": cards_ready,
            "start_cards": min(START_CARDS, cards),
            "ready_enough": total == 0 or enough_cards or pct >= READY_ENOUGH,
        }

    # The wait-screen game plays the words of the SESSION being waited for —
    # whatever slice of it has already landed in the learner's language. The
    # pool grows as the loop fills, so the game gets richer while they wait,
    # and every match is a word they meet for real minutes later.
    # A pair is only playable if the right-hand side is a GLOSS. Some stored
    # definitions are not: a Russian learner of English was shown "it" against
    # "И что?", "be" against "У тебя это есть?", and "dogs" against a Spanish
    # sentence — the wait screen faithfully displaying rows that are wrong on
    # the card too. Fixing those rows is content work; refusing to build a
    # matching game out of them is this query's job, because a word paired
    # with a sentence is unplayable even after the sentence is corrected.
    #
    # The test is deliberately blunt — a gloss is short and does not end like
    # a sentence — since anything subtler would need to know the language.
    out["pairs"] = [
        {"word": r["word"], "gloss": r["definition"]}
        for r in await conn.fetch(
            r"""SELECT v.word, t.definition FROM vocabulary v
                JOIN translations t ON t.vocabulary_id = v.id
                WHERE v.id = ANY($1::uuid[]) AND t.locale = $2
                  AND btrim(t.definition) <> ''
                  AND btrim(t.definition) !~ '[.!?…]$'
                  AND array_length(
                        regexp_split_to_array(btrim(t.definition), '\s+'), 1
                      ) <= 4
                LIMIT 12""",
            list(learn_v), locale)
        if r["definition"]
    ] if learn_v else []
    return out


async def add_learn_batch(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int,
    level: str | None = None,
) -> dict:
    """Add a batch of new vocabulary cards to user_cards from subscribed lists.

    Selects vocabulary the user has not yet learned (round-robin across the
    queued level decks), inserts each suspended, due now. When *level* is
    given, the batch draws only from that CEFR level (a specific deck).

    Returns:
        {"added": int, "items": list[str]}  — count and list of new user_card IDs
    """
    await pretranslate_upcoming(conn, user_id, language_id, batch_size, level)
    ids = await _select_vocab_candidate_ids(
        conn, user_id, language_id, batch_size, level
    )
    return await _insert_learn_cards(
        conn, user_id, language_id, [("vocabulary", i) for i in ids]
    )


async def add_grammar_learn_batch(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int,
    level: str | None = None,
) -> dict:
    """Add a batch of new grammar cards from the user's subscribed grammar lists.

    Mirrors add_learn_batch but for grammar_points: round-robin across the
    queued level decks (display_order within a level), inserted suspended and
    due. When *level* is given, only that deck's points qualify.
    """
    await pretranslate_upcoming(conn, user_id, language_id, batch_size, level)
    ids = await _select_grammar_candidate_ids(
        conn, user_id, language_id, batch_size, level
    )
    return await _insert_learn_cards(
        conn, user_id, language_id, [("grammar", i) for i in ids]
    )


async def add_mixed_learn_batch(
    conn: asyncpg.Connection,
    user_id: str,
    language_id: str,
    batch_size: int,
) -> dict:
    """Add a batch that INTERLEAVES new grammar and vocabulary (owner request:
    when both are queued, teach them together rather than one type per
    session). Each type is ranked round-robin across its own queued level
    decks; the two lists are then interleaved grammar-first per round to
    batch_size total. If only one type has anything queued this degrades to
    that type's normal batch, so it is always safe to call unscoped.
    """
    await pretranslate_upcoming(conn, user_id, language_id, batch_size)
    grammar_ids = await _select_grammar_candidate_ids(
        conn, user_id, language_id, batch_size, None
    )
    vocab_ids = await _select_vocab_candidate_ids(
        conn, user_id, language_id, batch_size, None
    )
    typed = _interleave_typed(grammar_ids, vocab_ids, batch_size)
    return await _insert_learn_cards(conn, user_id, language_id, typed)


async def confirm_learn_batch(
    conn: asyncpg.Connection, user_id: str, card_ids: list[str]
) -> int:
    """Activate learned cards after the lesson walkthrough is completed.

    Cards are created suspended by the learn batch; this flips them into the
    review queue, due immediately. Only never-reviewed cards qualify — a card
    with history can't be re-activated through the learn flow.

    This is also the moment the card was LEARNED, so it is stamped here.
    created_at cannot answer that question: a walkthrough left unfinished is
    re-taught from the same row weeks later, and the row remembers the day it
    was first offered. A learner who finished five lessons, four of them
    re-taught, was credited with one.
    """
    if not card_ids:
        return 0
    try:
        result = await conn.execute(
            """
            UPDATE user_cards
            SET is_suspended = false, next_review = now(), learned_at = now()
            WHERE id = ANY($1::uuid[])
              AND user_id = $2
              AND is_suspended
              AND repetitions = 0
            """,
            card_ids,
            user_id,
        )
    except asyncpg.exceptions.UndefinedColumnError:
        # Migration 20260928 hasn't landed. Activate the cards anyway — the
        # daily counter falls back to created_at (see get_dashboard_stats),
        # which is the behaviour this replaces, not a broken one.
        result = await conn.execute(
            """
            UPDATE user_cards
            SET is_suspended = false, next_review = now()
            WHERE id = ANY($1::uuid[])
              AND user_id = $2
              AND is_suspended
              AND repetitions = 0
            """,
            card_ids,
            user_id,
        )
    return int(result.split(" ")[-1])


async def get_learn_decks(
    conn: asyncpg.Connection, user_id: str, language_id: str
) -> list[dict]:
    """Return the language's learn decks (content lists) with progress.

    One row per content list (Bunpro-style deck): what it is, how many items
    it holds (only learnable ones — visible grammar with drills, all vocab),
    how many the user has started, and whether they're subscribed. The learned
    counts intentionally ignore subscription: progress shows even on decks the
    user hasn't queued yet.
    """
    rows = await conn.fetch(
        """
        SELECT
            cl.id,
            cl.list_type,
            cl.level,
            cl.title,
            (ucs.user_id IS NOT NULL) AS subscribed,
            CASE WHEN cl.list_type = 'grammar' THEN (
                SELECT COUNT(*)
                FROM grammar_points gp
                JOIN languages l ON gp.language_id = l.id
                WHERE gp.language_id = cl.language_id
                  AND (cl.level IS NULL OR gp.level = cl.level)
                  AND (CASE l.grammar_review_policy
                    WHEN 'all'  THEN true
                    WHEN 'both' THEN (gp.reviewed AND gp.ai_check_status = 'pass')
                    WHEN 'ai_ok' THEN (gp.reviewed OR gp.ai_check_status = 'pass')
                    ELSE gp.reviewed END)
                  AND EXISTS (
                      SELECT 1 FROM drill_sentences ds
                      WHERE ds.grammar_point_id = gp.id
                  )
            ) ELSE (
                SELECT COUNT(*)
                FROM vocabulary v
                WHERE v.language_id = cl.language_id
                  AND (cl.level IS NULL OR v.level = cl.level)
                  AND (v.level_source <> 'ai'
                       OR EXISTS (SELECT 1 FROM languages lp
                                   WHERE lp.id = v.language_id
                                     AND lp.grammar_review_policy IN ('ai_ok', 'all')))
            ) END AS total,
            CASE WHEN cl.list_type = 'grammar' THEN (
                SELECT COUNT(*)
                FROM user_cards uc
                JOIN grammar_points gp
                     ON uc.card_id = gp.id AND uc.card_type = 'grammar'
                WHERE uc.user_id = $1
                  AND gp.language_id = cl.language_id
                  AND (cl.level IS NULL OR gp.level = cl.level)
                  -- unconfirmed walkthroughs don't count as learned
                  AND NOT (uc.is_suspended AND uc.repetitions = 0)
            ) ELSE (
                SELECT COUNT(*)
                FROM user_cards uc
                JOIN vocabulary v
                     ON uc.card_id = v.id AND uc.card_type = 'vocabulary'
                WHERE uc.user_id = $1
                  AND v.language_id = cl.language_id
                  AND (cl.level IS NULL OR v.level = cl.level)
                  AND NOT (uc.is_suspended AND uc.repetitions = 0)
            ) END AS learned
        FROM content_lists cl
        LEFT JOIN user_content_subscriptions ucs
               ON ucs.content_list_id = cl.id AND ucs.user_id = $1
        WHERE cl.language_id = $2
          AND cl.list_type IN ('grammar', 'vocabulary')
        ORDER BY cl.list_type ASC, cl.level ASC NULLS LAST
        """,
        user_id,
        language_id,
    )
    return [
        {
            "id": str(r["id"]),
            "list_type": r["list_type"],
            "level": r["level"],
            "title": r["title"],
            "subscribed": r["subscribed"],
            "total": int(r["total"]),
            "learned": int(r["learned"]),
        }
        for r in rows
    ]


async def update_card_srs(
    conn: asyncpg.Connection, card_id: str, srs_update: dict
) -> None:
    """Update a card's FSRS fields after review."""
    await conn.execute(
        """
        UPDATE user_cards
        SET stability = $1,
            difficulty = $2,
            state = $3,
            interval = $4,
            repetitions = $5,
            streak = $6,
            lapses = $7,
            next_review = $8,
            last_review = now()
        WHERE id = $9
        """,
        srs_update["stability"],
        srs_update["difficulty"],
        srs_update["state"],
        srs_update["interval"],
        srs_update["repetitions"],
        srs_update["streak"],
        srs_update["lapses"],
        srs_update["next_review"],
        card_id,
    )


# The explicit-content gate lives in explicit_gate.py (curriculum.py needs
# it too, and this module already imports from curriculum — the neutral
# module breaks the cycle). The examples-only alias predates the
# generalisation and means the same thing.
_fetch_examples = fetch_explicit_gated


async def get_card_details_bulk(
    conn: asyncpg.Connection, card_ids: list[str], support_locale: str | None = None
) -> dict[str, dict]:
    """Return {user_card_id: detail} for many cards in a few bulk queries.

    Same payload shape as get_card_detail, but batched: the learn endpoint
    builds a lesson per new card, and doing that one card at a time is an
    N+1 that hurts badly over a pooled (high-latency) database connection.
    Personal cards fall back to the single-card path (never produced by the
    learn flow). *support_locale* localizes English cards (see get_due_cards).
    """
    if not card_ids:
        return {}
    cards = await conn.fetch(
        "SELECT id, card_type, card_id FROM user_cards WHERE id = ANY($1::uuid[])",
        card_ids,
    )
    vocab_ids = [c["card_id"] for c in cards if c["card_type"] == "vocabulary"]
    grammar_ids = [c["card_id"] for c in cards if c["card_type"] == "grammar"]

    # Every course localizes by the support locale (per-field fallback to
    # the authored English wherever an overlay row hasn't been filled yet):
    # definitions and explanations COALESCE, drill hints/translations go
    # via drill_hint_translations (WP17), example sentences prefer the
    # locale-translated row per sentence.
    eff_locale = (
        support_locale if support_locale and support_locale != "en" else "en"
    )

    vocab_by_id: dict = {}
    vocab_examples: dict = {}
    vocab_quiz: dict = {}
    if vocab_ids:
        for v in await conn.fetch(
            """
            SELECT v.id, v.word, v.reading, v.part_of_speech, v.usage_note,
                   v.morphology, v.alternatives,
                   COALESCE(t.definition, t_en.definition) AS definition
            FROM vocabulary v
            LEFT JOIN translations t
                   ON v.id = t.vocabulary_id AND t.locale = $2
            LEFT JOIN translations t_en
                   ON v.id = t_en.vocabulary_id AND t_en.locale = 'en'
            WHERE v.id = ANY($1::uuid[])
            """,
            vocab_ids,
            eff_locale,
        ):
            vocab_by_id[v["id"]] = v
        for e in await _fetch_examples(
            conn,
            """
            SELECT vocabulary_id, sentence, translation, gloss, transliteration
            FROM (
                -- Prefer the learner's-locale translation of each sentence,
                -- falling back to the English row — never a third language.
                SELECT DISTINCT ON (es.vocabulary_id, es.sentence)
                       es.vocabulary_id, es.sentence,
                       CASE WHEN es.translation_locale IN ($2, 'en')
                            THEN es.translation END AS translation,
                       es.gloss, es.transliteration, es.difficulty_rank
                FROM example_sentences es
                WHERE es.vocabulary_id = ANY($1::uuid[])
                  AND (es.translation_locale IN ($2, 'en')
                       -- ...or the sentence already reads in the learner's own
                       -- language and needs no translation — the English
                       -- course, whose bank holds no 'en' rows at all. The
                       -- translation is nulled above, so no third language is
                       -- shown as if it were theirs.
                       OR es.language_id IN (
                           SELECT id FROM languages WHERE code = $2))
                  AND es.reviewed
                  {explicit}
                ORDER BY es.vocabulary_id, es.sentence,
                         (es.translation_locale = $2) DESC,
                         (es.translation_locale = 'en') DESC, es.id
            ) pes
            ORDER BY difficulty_rank ASC NULLS LAST
            """,
            vocab_ids,
            eff_locale,
            alias="es",
        ):
            bucket = vocab_examples.setdefault(e["vocabulary_id"], [])
            if len(bucket) < 5:
                bucket.append(
                    {"sentence": e["sentence"], "translation": e["translation"], "hint": None}
                )
            # First-check quiz: the first sentence where the word clozes.
            v = vocab_by_id.get(e["vocabulary_id"])
            if v is not None and e["vocabulary_id"] not in vocab_quiz:
                cloze = make_cloze(e["sentence"], v["word"])
                if cloze:
                    vocab_quiz[e["vocabulary_id"]] = {
                        "sentence": cloze,
                        "translation": e["translation"],
                        "gloss": e["gloss"],
                        "transliteration": e["transliteration"],
                        "hint": v["definition"],
                    }

    grammar_by_id: dict = {}
    grammar_examples: dict = {}
    grammar_quiz: dict = {}
    if grammar_ids:
        gpt = _gpt_sql(
            await _table_exists(conn, "grammar_point_translations"), "$2"
        )
        for gp in await conn.fetch(
            f"""
            SELECT gp.id, {gpt["title"]} AS title,
                   {gpt["function_note"]} AS function_note,
                   COALESCE(et.explanation, gp.explanation) AS explanation,
                   {gpt["culture_note"]} AS culture_note,
                   gp.reference_links, gp.reviewed
            FROM grammar_points gp
            LEFT JOIN explanation_translations et
                   ON et.grammar_point_id = gp.id AND et.locale = $2
            {gpt["join"]}
            WHERE gp.id = ANY($1::uuid[])
            """,
            grammar_ids,
            eff_locale,
        ):
            grammar_by_id[gp["id"]] = gp
        for e in await conn.fetch(
            """
            SELECT ds.grammar_point_id, ds.sentence, ds.answer,
                   COALESCE(dht.translation, ds.translation) AS translation,
                   COALESCE(dht.hint, ds.hint) AS hint,
                   ds.gloss, ds.transliteration
            FROM drill_sentences ds
            LEFT JOIN drill_hint_translations dht
                   ON dht.drill_id = ds.id AND dht.locale = $2
            WHERE ds.grammar_point_id = ANY($1::uuid[])
              AND (ds.reviewed
                   OR EXISTS (SELECT 1 FROM grammar_points gp2
                               WHERE gp2.id = ds.grammar_point_id
                                 AND gp2.language_id IN (
                                     SELECT id FROM languages
                                      WHERE grammar_review_policy IN ('ai_ok', 'all'))))
            ORDER BY ds.display_order ASC
            """,
            grammar_ids,
            eff_locale,
        ):
            grammar_examples.setdefault(e["grammar_point_id"], []).append({
                # Lesson views show the COMPLETED sentence, not the blank
                "sentence": e["sentence"].replace(ANSWER_MARKER, e["answer"]),
                "translation": e["translation"],
                "hint": e["hint"],
            })
            # First-check quiz: the point's first drill, blank kept.
            if e["grammar_point_id"] not in grammar_quiz:
                grammar_quiz[e["grammar_point_id"]] = {
                    "sentence": e["sentence"],
                    "answer": e["answer"],
                    "translation": e["translation"],
                    "gloss": e["gloss"],
                    "transliteration": e["transliteration"],
                    "hint": e["hint"],
                }
        # The "in context" block shows 5 of the point's drills — but sampled
        # across the WHOLE list, not the head. Seed drills open with the
        # paradigm row (six "pronoun + ser + noun" lines) and only vary
        # further in, so first-5 showed a learner one frame six ways (the
        # owner's screenshot). An even stride keeps it deterministic while
        # reaching the varied sentences.
        for gp_id, bucket in grammar_examples.items():
            n = len(bucket)
            if n > 5:
                grammar_examples[gp_id] = [
                    bucket[(i * n) // 5] for i in range(5)
                ]

    # Whatever this Learn batch had to serve in English becomes demand for
    # the auto-translate loop.
    await note_missing_content(conn, eff_locale,
                               vocab_ids=vocab_ids, grammar_ids=grammar_ids)

    details: dict[str, dict] = {}
    for c in cards:
        if c["card_type"] == "vocabulary":
            v = vocab_by_id.get(c["card_id"])
            if v is None:
                continue
            # The learner must answer this before the card enters reviews
            # (teach → check → queue). Falls back to the type-the-word
            # prompt when no example sentence clozes.
            quiz = vocab_quiz.get(c["card_id"]) or {
                "sentence": v["definition"] or v["word"],
                "translation": None,
                "gloss": None,
                "transliteration": None,
                "hint": v["definition"],
            }
            details[str(c["id"])] = {
                "card_type": "vocabulary",
                "title": v["word"],
                "reading": v["reading"],
                "part_of_speech": v["part_of_speech"],
                "definition": v["definition"],
                "usage_note": v["usage_note"],
                "morphology": v["morphology"],
                "explanation": None,
                "culture_note": None,
                "reviewed": True,
                "references": [],
                "examples": vocab_examples.get(c["card_id"], []),
                "quiz": {
                    **quiz,
                    "answer": v["word"],
                    "morphology": v["morphology"],
                    "alternatives": v["alternatives"] or [],
                },
            }
        elif c["card_type"] == "grammar":
            gp = grammar_by_id.get(c["card_id"])
            if gp is None:
                continue
            references = []
            if gp["reference_links"]:
                raw = gp["reference_links"]
                if isinstance(raw, str):
                    try:
                        raw = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        raw = []
                references = clean_references(raw)
            quiz = grammar_quiz.get(c["card_id"])
            details[str(c["id"])] = {
                "card_type": "grammar",
                "title": gp["title"],
                "function_note": gp["function_note"],
                "reading": None,
                "part_of_speech": None,
                "definition": None,
                "usage_note": None,
                "morphology": None,
                "explanation": gp["explanation"],
                "culture_note": gp["culture_note"],
                "reviewed": gp["reviewed"],
                "references": references,
                "examples": grammar_examples.get(c["card_id"], []),
                "quiz": (
                    {**quiz, "morphology": None, "alternatives": []}
                    if quiz else None
                ),
            }
        else:
            detail = await get_card_detail(conn, str(c["id"]))
            if detail:
                details[str(c["id"])] = detail
    # A lesson's own quiz is a card like any other, and its translation
    # falls back to English the same way — so the flag has to reach the
    # nested quiz, not just the lesson wrapper.
    for detail in details.values():
        mark_locale_mismatches(detail, support_locale)
        quiz = detail.get("quiz")
        if isinstance(quiz, dict):
            mark_locale_mismatches(quiz, support_locale)
    return details


async def get_card_detail(
    conn: asyncpg.Connection, card_id: str, support_locale: str | None = None
) -> dict | None:
    """Return the rich "review this card" content for the optional panel.

    The shape differs by card type (vocab vs grammar sets review differently):
      - vocabulary: word, definition, usage note, morphology, and graded
        example sentences (word seen in context).
      - grammar: title, broad explanation, culture note, and the point's
        drill sentences with translations.

    *card_id* is a user_cards id; RLS on the connection scopes it to the
    authenticated user, so a card the user doesn't own returns None.
    *support_locale* localizes English cards (see get_due_cards).
    """
    card = await conn.fetchrow(
        """
        SELECT card_type, card_id, language_id, repetitions, streak, lapses,
               next_review, created_at, stability, state
        FROM user_cards WHERE id = $1
        """,
        card_id,
    )
    if card is None:
        return None

    # The learner's history with this card: named stage + accuracy from the
    # actual review log (RLS scopes the log to this user).
    log = await conn.fetchrow(
        """
        SELECT count(*) AS n,
               count(*) FILTER (WHERE answer_result IN ('correct', 'correct_sloppy')) AS ok,
               min(created_at) AS first_studied
        FROM review_log WHERE card_id = $1
        """,
        card_id,
    )
    first = (log["first_studied"] if log else None) or card["created_at"]
    progress = {
        "stage": stage_for(card["card_type"], card["state"], card["stability"]),
        "first_studied": first.isoformat() if first else None,
        "times_studied": int(log["n"]) if log else 0,
        "accuracy": (int(log["ok"]) / int(log["n"])) if log and log["n"] else None,
        "streak": card["streak"],
        "misses": card["lapses"],
        "next_review": card["next_review"].isoformat() if card["next_review"] else None,
    }

    if card["card_type"] == "personal":
        # Provenance columns arrived in separate owner-applied migrations
        # (personal_deck_id: 20260811, source: 20261005) — probe, never
        # catch, or the pooled transaction dies (see get_due_cards).
        has_deck = await table_present(conn, "personal_decks")
        has_source = bool(await conn.fetchval(
            "SELECT 1 FROM information_schema.columns"
            " WHERE table_schema = 'public'"
            "   AND table_name = 'user_cloze_cards' AND column_name = 'source'"
        ))
        deck_join = (
            "LEFT JOIN personal_decks pd ON cc.personal_deck_id = pd.id"
            if has_deck else ""
        )
        cc = await conn.fetchrow(
            f"""
            SELECT cc.answer, cc.translation, cc.sentence, cc.created_at,
                   {"cc.source" if has_source else "NULL"} AS source,
                   {"pd.name" if has_deck else "NULL"} AS deck_name,
                   n.title AS note_title
            FROM user_cloze_cards cc
            LEFT JOIN user_notes n ON cc.note_id = n.id
            {deck_join}
            WHERE cc.id = $1
            """,
            card["card_id"],
        )
        # Show the word back in its original sentence — the "seen in context"
        # payoff of learning from your own text.
        examples = []
        if cc and cc["sentence"]:
            full = cc["sentence"].replace(ANSWER_MARKER, cc["answer"] or "")
            examples = [{
                "sentence": full,
                "translation": cc["translation"],
                "hint": None,
            }]
        usage = (
            f"From your note: {cc['note_title']}"
            if cc and cc["note_title"] else None
        )
        # Structured provenance, localized CLIENT-side (usage_note above is
        # composed English and kept only for old clients). source None means
        # the card predates tracking — displayed as that, never guessed.
        provenance = {
            "source": cc["source"] if cc else None,
            "created_at": (
                cc["created_at"].isoformat() if cc and cc["created_at"] else None
            ),
            "note_title": cc["note_title"] if cc else None,
            "deck_name": cc["deck_name"] if cc else None,
        } if cc else None
        return {
            "card_type": "personal",
            "title": cc["answer"] if cc else None,
            "reading": None,
            "part_of_speech": None,
            "definition": cc["translation"] if cc else None,
            "usage_note": usage,
            "morphology": None,
            "explanation": None,
            "culture_note": None,
            "reviewed": True,
            "references": [],
            "examples": examples,
            "progress": progress,
            "provenance": provenance,
        }

    if card["card_type"] == "vocabulary":
        eff_locale = await _effective_locale(
            conn, card["language_id"], support_locale
        )
        v = await conn.fetchrow(
            """
            SELECT v.word, v.reading, v.part_of_speech, v.usage_note, v.morphology,
                   COALESCE(t.definition, t_en.definition) AS definition
            FROM vocabulary v
            LEFT JOIN translations t
                   ON v.id = t.vocabulary_id AND t.locale = $2
            LEFT JOIN translations t_en
                   ON v.id = t_en.vocabulary_id AND t_en.locale = 'en'
            WHERE v.id = $1
            """,
            card["card_id"],
            eff_locale,
        )
        examples = await _fetch_examples(
            conn,
            """
            SELECT sentence, translation
            FROM (
                -- Prefer the learner's-locale translation per sentence,
                -- falling back to the English row — never a third language.
                SELECT DISTINCT ON (es.sentence)
                       es.sentence,
                       CASE WHEN es.translation_locale IN ($2, 'en')
                            THEN es.translation END AS translation,
                       es.difficulty_rank
                FROM example_sentences es
                WHERE es.vocabulary_id = $1
                  AND (es.translation_locale IN ($2, 'en')
                       -- ...or the sentence already reads in the learner's own
                       -- language and needs no translation — the English
                       -- course, whose bank holds no 'en' rows at all. The
                       -- translation is nulled above, so no third language is
                       -- shown as if it were theirs.
                       OR es.language_id IN (
                           SELECT id FROM languages WHERE code = $2))
                  AND es.reviewed
                  {explicit}
                ORDER BY es.sentence, (es.translation_locale = $2) DESC,
                         (es.translation_locale = 'en') DESC, es.id
            ) pes
            ORDER BY difficulty_rank ASC NULLS LAST
            LIMIT 5
            """,
            card["card_id"],
            eff_locale,
            alias="es",
        )
        await note_missing_content(conn, eff_locale,
                                   vocab_ids=[card["card_id"]])
        # The learner's OWN sentences with this word (from notes → cloze
        # cards), shown under Examples — RLS scopes them to this user.
        own = []
        if v and v["word"]:
            own = await conn.fetch(
                """
                SELECT sentence, answer, translation
                FROM user_cloze_cards
                WHERE language_id = $1 AND lower(answer) = lower($2)
                ORDER BY created_at ASC
                LIMIT 5
                """,
                card["language_id"],
                v["word"],
            )
        return {
            "card_type": "vocabulary",
            "title": v["word"] if v else None,
            "reading": v["reading"] if v else None,
            "part_of_speech": v["part_of_speech"] if v else None,
            "definition": v["definition"] if v else None,
            "usage_note": v["usage_note"] if v else None,
            "morphology": v["morphology"] if v else None,
            # Which language the hints/definitions are rendered in — the
            # learner's support locale when set (any course), else 'en'.
            "hint_locale": eff_locale,
            "explanation": None,
            "culture_note": None,
            "reviewed": True,  # vocabulary has no review gate
            "references": [],
            "examples": [
                {"sentence": e["sentence"], "translation": e["translation"], "hint": None}
                for e in examples
            ],
            "your_sentences": [
                {
                    "sentence": o["sentence"].replace(ANSWER_MARKER, o["answer"] or ""),
                    "translation": o["translation"],
                }
                for o in own
            ],
            "progress": progress,
        }

    # grammar
    # WP17/WP22: hint, translation, AND the explanation itself render in
    # the learner's locale on any course (same COALESCE rule as vocabulary
    # definitions — English wherever the overlay hasn't been filled yet).
    eff_locale = await _effective_locale(conn, card["language_id"], support_locale)
    gpt = _gpt_sql(await _table_exists(conn, "grammar_point_translations"), "$2")
    gp = await conn.fetchrow(
        f"""
        SELECT {gpt["title"]} AS title, {gpt["function_note"]} AS function_note,
               COALESCE(et.explanation, gp.explanation) AS explanation,
               {gpt["culture_note"]} AS culture_note,
               gp.explanation_source, gp.reference_links,
               gp.related, gp.reviewed
        FROM grammar_points gp
        LEFT JOIN explanation_translations et
               ON et.grammar_point_id = gp.id AND et.locale = $2
        {gpt["join"]}
        WHERE gp.id = $1
        """,
        card["card_id"],
        eff_locale,
    )
    await note_missing_content(conn, eff_locale, grammar_ids=[card["card_id"]])
    related = (
        await resolve_related(conn, card["language_id"], gp["related"]) if gp else []
    )
    read_refs = await get_read_ref_keys(conn, str(card["card_id"]))
    examples = await conn.fetch(
        """
        SELECT ds.sentence, ds.answer,
               COALESCE(dht.translation, ds.translation) AS translation,
               COALESCE(dht.hint, ds.hint) AS hint
        FROM drill_sentences ds
        LEFT JOIN drill_hint_translations dht
               ON dht.drill_id = ds.id AND dht.locale = $2
        WHERE ds.grammar_point_id = $1
          AND (ds.reviewed
               OR EXISTS (SELECT 1 FROM grammar_points gp2
                           WHERE gp2.id = ds.grammar_point_id
                             AND gp2.language_id IN (
                                 SELECT id FROM languages
                                  WHERE grammar_review_policy IN ('ai_ok', 'all'))))
        ORDER BY ds.display_order ASC
        LIMIT 5
        """,
        card["card_id"],
        eff_locale,
    )
    references = []
    if gp and gp["reference_links"]:
        raw = gp["reference_links"]
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = []
        references = clean_references(raw)
    return {
        "card_type": "grammar",
        "point_id": str(card["card_id"]),
        "title": gp["title"] if gp else None,
        "function_note": gp["function_note"] if gp else None,
        "reading": None,
        "part_of_speech": None,
        "definition": None,
        "usage_note": None,
        "morphology": None,
        "explanation": gp["explanation"] if gp else None,
        "culture_note": gp["culture_note"] if gp else None,
        "reviewed": gp["reviewed"] if gp else True,
        "references": references,
        "read_refs": read_refs,
        "related": related,
        "progress": progress,
        "examples": [
            {
                # Detail/lesson views show the COMPLETED sentence, not the blank
                "sentence": e["sentence"].replace(ANSWER_MARKER, e["answer"]),
                "translation": e["translation"],
                "hint": e["hint"],
            }
            for e in examples
        ],
    }


async def get_generation_context(
    conn: asyncpg.Connection, point_id: str
) -> dict | None:
    """A grammar point's context for the drill generator (Part C / Gym): its
    title, explanation, language, and a few existing drills as style examples.
    None if the point doesn't exist."""
    row = await conn.fetchrow(
        """
        SELECT gp.title, gp.explanation, gp.language_id,
               l.code AS language_code, l.name AS language_name
        FROM grammar_points gp
        JOIN languages l ON gp.language_id = l.id
        WHERE gp.id = $1
        """,
        point_id,
    )
    if row is None:
        return None
    drills = await conn.fetch(
        "SELECT sentence FROM drill_sentences WHERE grammar_point_id = $1 "
        "ORDER BY display_order ASC LIMIT 6",
        point_id,
    )
    # Per-cell drill counts drive BALANCED thickening — generate for the cells
    # that are thin, not the ones already covered. Empty for non-paradigm points.
    cell_rows = await conn.fetch(
        "SELECT cell, count(*) AS n FROM drill_sentences "
        "WHERE grammar_point_id = $1 AND cell IS NOT NULL GROUP BY cell",
        point_id,
    )
    return {
        "point_id": str(point_id),
        "title": row["title"],
        "explanation": row["explanation"],
        "language_id": str(row["language_id"]),
        "language_code": row["language_code"],
        "language_name": row["language_name"],
        "examples": [d["sentence"] for d in drills],
        "cell_counts": {r["cell"]: r["n"] for r in cell_rows},
    }


async def get_cram_cards(
    conn: asyncpg.Connection,
    point_ids: list[str],
    per_point: int = 3,
    support_locale: str | None = None,
    count: int | None = None,
    user_id: str | None = None,
) -> list[dict]:
    """Ungraded practice cards for a set of grammar points (WP13f Quick-Cram).

    Built straight from the content tables — no user_cards row is read or
    written, card ids are synthetic, and nothing here is submittable to
    /review/submit. Visibility follows the same review policy as the
    curriculum. Drill choice is seeded per (point, day): a reload mid-cram
    keeps the same set, tomorrow's cram varies.

    The Gym is a fixed BASELINE practice: the drill HINT/cue is always the
    authored text (English for the English course) and never swapped to a
    reference-locale translation — even when the learner has picked one. Those
    machine hints ("to speak" → "пользоваться языком") were low quality, and the
    owner's rule is that choosing a reference language must not change the gym
    baseline. The sentence *translation* still shows in the learner's locale
    (it's the meaning aid, and the only sensible language for it). Localized
    hints still apply in the graded Learn/Review flow, just not here.
    """
    # gp.title stays the authored English (the manifest join key for the
    # irregular-forms boost below); title_l10n is what the card displays.
    gpt = _gpt_sql(await _table_exists(conn, "grammar_point_translations"), "$2")
    rows = await conn.fetch(
        f"""
        SELECT
            gp.id    AS point_id,
            gp.title AS title,
            {gpt["title"]} AS title_l10n,
            l.code   AS language_code,
            d.drill_ids,
            d.sentences, d.answers, d.hints, d.translations,
            d.glosses, d.transliterations, d.cells, d.lemmas
        FROM grammar_points gp
        JOIN languages l ON gp.language_id = l.id
        {gpt["join"]}
        LEFT JOIN LATERAL (
            SELECT
                array_agg(ds.id          ORDER BY ds.display_order, ds.id) AS drill_ids,
                array_agg(ds.sentence    ORDER BY ds.display_order, ds.id) AS sentences,
                array_agg(ds.answer      ORDER BY ds.display_order, ds.id) AS answers,
                -- Gym baseline: the authored hint, never the reference-locale one.
                array_agg(ds.hint
                          ORDER BY ds.display_order, ds.id) AS hints,
                array_agg(COALESCE(dht.translation, ds.translation)
                          ORDER BY ds.display_order, ds.id) AS translations,
                array_agg(ds.gloss       ORDER BY ds.display_order, ds.id) AS glosses,
                array_agg(ds.transliteration ORDER BY ds.display_order, ds.id) AS transliterations,
                array_agg(ds.cell        ORDER BY ds.display_order, ds.id) AS cells,
                array_agg(ds.lemma       ORDER BY ds.display_order, ds.id) AS lemmas
            FROM drill_sentences ds
            LEFT JOIN drill_hint_translations dht
                   ON dht.drill_id = ds.id AND dht.locale = $2
            WHERE ds.grammar_point_id = gp.id
              -- Gym: reviewed drills are shared corpus; a learner also gets the
              -- drills they generated on demand (created_by = them), private to
              -- them until a reviewer approves them for all. A language whose
              -- policy is 'ai_ok' serves verified AI drills to everyone.
              AND (ds.reviewed OR ds.created_by = auth.uid()
                   OR gp.language_id IN (
                       SELECT id FROM languages
                        WHERE grammar_review_policy IN ('ai_ok', 'all')))
        ) d ON true
        WHERE gp.id = ANY($1::uuid[])
          AND (CASE l.grammar_review_policy
                    WHEN 'all'  THEN true
                    WHEN 'both' THEN (gp.reviewed AND gp.ai_check_status = 'pass')
                    WHEN 'ai_ok' THEN (gp.reviewed OR gp.ai_check_status = 'pass')
                    ELSE gp.reviewed END)
        """,
        point_ids,
        support_locale or "en",
    )
    await note_missing_content(
        conn, support_locale if support_locale and support_locale != "en" else None,
        grammar_ids=list(point_ids),
    )
    today = datetime.now(UTC).date().isoformat()
    now = datetime.now(UTC)

    # Adaptive weighting (WP): score each candidate drill from the learner's
    # per-drill history so struggled / unseen / long-unseen drills surface and
    # cleanly-mastered ones fade. Deterministic within a day (a mid-cram reload
    # keeps the same set); adapts across sessions as the history grows. With no
    # user_id, every drill scores as unseen → uniform selection (old behaviour).
    all_drill_ids = [
        str(did) for r in rows for did in (r["drill_ids"] or []) if did is not None
    ]
    progress = (
        await get_gym_progress(conn, user_id, all_drill_ids)
        if user_id and all_drill_ids
        else {}
    )
    rng = random.Random(f"{user_id}:{today}")

    def _priority(r: asyncpg.Record, i: int) -> float:
        drill_ids = r["drill_ids"] or []
        did = str(drill_ids[i]) if i < len(drill_ids) and drill_ids[i] else None
        # A point the manifest marks non-standard is an irregular form category
        # (verbs of motion, etc.) — its drills get the irregular boost so they
        # surface more, and float back up when the learner keeps failing them.
        irregular = r["title"] in nonstandard_point_titles(r["language_code"])
        weight = drill_weight(
            progress.get(did) if did else None, is_irregular=irregular
        )
        # Efraimidis–Spirakis weighted sampling without replacement: a higher
        # weight makes a higher key more likely, so top-k favours heavy drills
        # while keeping variety.
        return rng.random() ** (1.0 / max(weight, 1e-6))

    # Choose the (point, drill) pairs. With an explicit *count* the whole set is
    # weight-ranked across the chosen forms and drawn up to every one authored —
    # a real Gym set isn't capped at three per form. Without count, keep the
    # per_point cap, weight-ranked within each form.
    selected: list[tuple] = []  # (row, drill index)
    if count is not None:
        target = max(1, min(count, 100))
        candidates = [
            (r, i) for r in rows for i in range(len(r["sentences"] or []))
        ]
        candidates.sort(key=lambda ri: _priority(ri[0], ri[1]), reverse=True)
        selected = candidates[:target]
    else:
        for r in rows:
            idxs = list(range(len(r["sentences"] or [])))
            idxs.sort(key=lambda i: _priority(r, i), reverse=True)
            selected.extend((r, i) for i in idxs[: min(per_point, len(idxs))])

    cards: list[dict] = []
    for r, i in selected:
        sentences = r["sentences"]
        cards.append({
                "id": f"cram-{r['point_id']}-{i}",
                # Real drill row id — lets the Gym record per-drill practice
                # history (adaptive weighting). None only for legacy rows.
                "drill_id": str(r["drill_ids"][i]) if r["drill_ids"] else None,
                "card_type": "grammar",
                "card_id": str(r["point_id"]),
                "title": r["title_l10n"] if "title_l10n" in r.keys() else r["title"],
                "sentence": sentences[i],
                "correct_answer": r["answers"][i],
                "hint": r["hints"][i],
                "translation": r["translations"][i],
                "gloss": r["glosses"][i],
                "transliteration": r["transliterations"][i],
                # Paradigm cell + authored dictionary form — the raw material
                # for the standardized baseline built after chart attach.
                "cell": r["cells"][i] if r["cells"] else None,
                "lemma": r["lemmas"][i] if r["lemmas"] else None,
                "morphology": None,
                "alternatives": None,
                "language_code": r["language_code"],
                # Neutral SRS fields so the payload matches the DueCard shape
                # the session UI consumes; none of this is ever persisted.
                "ease_factor": 2.5,
                "interval": 0,
                "repetitions": 0,
                "streak": 0,
                "lapses": 0,
                "next_review": now,
            })
    # Interleave points instead of drilling one point three times in a row.
    random.Random(today).shuffle(cards)
    await attach_cram_charts(conn, cards)
    # Standardized baseline, built AFTER charts so it can use the chart word's
    # native-language gloss. The frontend still leak-guards it via safePrompt.
    for card in cards:
        card["baseline"] = _gym_baseline(card)
    # Same guard the review path applies: a Gym card's translation and
    # baseline fall back to English exactly as a review card's do, and the
    # learner is told just as confidently that it is their language.
    return [mark_locale_mismatches(c, support_locale) for c in cards]


# Mirror of the frontend's safePrompt recipe detection (hintLayers.ts): a
# dash-tail that spells out the answer's construction is stripped from the
# baseline word part.
_RECIPE_TAIL = re.compile(
    r"\b(add|drop|changes?|becomes?|remove)\b|→|->|(?:^|\s)[-–][^\s-]",
    re.IGNORECASE,
)
_HINT_DASH = re.compile(r"^(.*?)\s+[—–-]\s+(.+)$")


def _split_hint(hint: str | None) -> tuple[str, str]:
    """An authored hint's (word part, form tail). Strips a trailing spelling
    recipe ("to watch — add -es" → "to watch"), then splits legacy
    "lemma, person" authoring ("preparar, tú" → ("preparar", "tú"))."""
    base = (hint or "").strip()
    m = _HINT_DASH.match(base)
    if m and _RECIPE_TAIL.search(m.group(2)):
        base = m.group(1).strip()
    word, _, tail = base.partition(",")
    return word.strip(), tail.strip()


def _gym_baseline(card: dict) -> str:
    """The standardized Gym baseline: "base (form; gloss)".

    The Gym is PRACTICE, not recall — the learner is HANDED the word and asked
    to produce the form, so the base stays in the TARGET language and the form
    label carries the native-language explanation:

        preparar (tú; you, singular)
        дом (m.sg; masculine singular)

      base: the drill's stored lemma, else the chart word, else the authored
            hint's word part (legacy rows).
      form: the drill's paradigm cell, else the hint's comma tail
            ("preparar, tú" authoring). Glossed via cell_glosses when the
            label is explainable; unexplainable cells (articles, particles,
            suffixes) render as plain "base (form)".

    Description-style hints with no word ("indefinite article") pass through
    unchanged — they ARE the baseline. The frontend still runs the result
    through safePrompt, so a baseline can never leak the answer.
    """
    hint_word, hint_tail = _split_hint(card.get("hint"))
    base = (
        (card.get("lemma") or "").strip()
        or (card.get("chart_word") or "").strip()
        or hint_word
    )
    form = (card.get("cell") or "").strip() or hint_tail
    if not base:
        return ""
    if not form:
        return base
    gloss = cell_gloss(card.get("language_code"), form)
    return f"{base} ({form}; {gloss})" if gloss else f"{base} ({form})"


def _chartable(morphology) -> object | None:
    """Return *morphology* only if it carries at least one chart table.

    The Gym's collapsed panel is specifically the conjugation/declension
    CHART — words with only chips (gender, aspect…) get no toggle.
    """
    parsed = morphology
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(parsed, dict) or not parsed.get("charts"):
        return None
    return morphology


def _form_key(word: str) -> str:
    """Comparison key for a word form: lowercase, letters only, combining
    marks dropped. The charts carry stress marks the drills don't ("жи́ли" vs
    "жили"), so a raw string compare misses."""
    decomposed = unicodedata.normalize("NFD", word.lower())
    return "".join(
        ch for ch in decomposed
        if not unicodedata.combining(ch) and (ch.isalpha() or ch == "'")
    )


def _word_tokens(text: str) -> list[str]:
    """Word tokens with combining marks removed BEFORE splitting. Python's
    \\w excludes combining marks, so a stressed chart form like "жи́ли" would
    otherwise split into "жи" + "ли" and never match anything."""
    stripped = "".join(
        ch for ch in unicodedata.normalize("NFD", text or "")
        if not unicodedata.combining(ch)
    )
    return re.findall(r"[^\W\d_]+", stripped)


def _chart_form_keys(morphology) -> set[str]:
    """Every inflected form printed inside a chart, as comparison keys."""
    parsed = morphology
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (json.JSONDecodeError, TypeError):
            return set()
    if not isinstance(parsed, dict):
        return set()
    keys: set[str] = set()
    for chart in parsed.get("charts") or []:
        if not isinstance(chart, dict):
            continue
        for row in chart.get("rows") or []:
            if not isinstance(row, list):
                continue
            for cell in row:
                for token in _word_tokens(str(cell)):
                    key = _form_key(token)
                    if len(key) > 1:
                        keys.add(key)
    return keys


# Per-language "inflected form → headword" index, built from the charts
# themselves. Bounded: the Gym is used one language at a time, and a stale
# index only costs a missed chart (never a wrong one) until the process
# recycles.
_FORM_INDEX: dict[str, dict[str, str]] = {}
_FORM_INDEX_MAX_LANGS = 3


async def _chart_form_index(
    conn: asyncpg.Connection, language_code: str
) -> dict[str, str]:
    """Map every form appearing in a language's charts to its headword.

    This is the reverse of lemmatization, and it's what makes charts work at
    all for most languages: a seeded drill stores no lemma, its hint is often
    an English gloss, and ten languages have no real lemmatizer (their
    "lemmatize" only folds accents). The charts, however, already list the
    exact inflected forms the drills use — so we look the answer up in them.
    """
    cached = _FORM_INDEX.get(language_code)
    if cached is not None:
        return cached
    rows = await conn.fetch(
        """
        SELECT v.word, v.morphology
        FROM vocabulary v
        JOIN languages l ON v.language_id = l.id
        WHERE l.code = $1 AND v.morphology IS NOT NULL
        """,
        language_code,
    )
    index: dict[str, str] = {}
    for r in rows:
        word = r.get("word")
        if not word:
            continue
        morph = r.get("morphology")
        if _chartable(morph) is None:
            continue
        # The headword itself first, then its forms; earlier words win so the
        # mapping is stable across requests.
        for key in (_form_key(word), *sorted(_chart_form_keys(morph))):
            if key and key not in index:
                index[key] = word
    if len(_FORM_INDEX) >= _FORM_INDEX_MAX_LANGS:
        _FORM_INDEX.pop(next(iter(_FORM_INDEX)), None)
    _FORM_INDEX[language_code] = index
    return index


def _reset_chart_form_index() -> None:
    """Test hook — drop the cached indexes."""
    _FORM_INDEX.clear()


async def attach_cram_charts(conn: asyncpg.Connection, cards: list[dict]) -> None:
    """WP25(c): give each Gym drill the chart of the word it exercises.

    Drills store only the surface form ("слушаю"); the charts live on the
    vocabulary row of the dictionary form ("слушать"). The language's NLP
    lemmatizer bridges the two. Best-effort by design — an answer that isn't
    a chartable vocabulary word keeps morphology None and the session UI
    simply shows no chart toggle.
    """
    from backend.services.nlp import get_nlp

    # Candidate dictionary forms per card, batched into one query per language.
    wanted: dict[str, set[str]] = {}
    plans: list[tuple[dict, list[str]]] = []
    by_language_tokens: dict[str, list[tuple[dict, list[str]]]] = {}
    for card in cards:
        if card.get("morphology") is not None:
            continue
        lang = card.get("language_code")
        if not lang:
            continue
        candidates: list[str] = []
        # The authored dictionary form (new drills store it) and the hint's
        # word part (legacy "preparar, tú" authoring) are DIRECT chart keys —
        # no lemmatizer needed, so they lead. English-gloss hints ("to live")
        # are multi-word and skipped; they'd never match target vocabulary.
        stored = (card.get("lemma") or "").strip().lower()
        if stored:
            candidates.append(stored)
        hint_word, _tail = _split_hint(card.get("hint"))
        hw = hint_word.lower()
        if hw and " " not in hw and hw not in candidates:
            candidates.append(hw)
        tokens = [
            t for t in _word_tokens(card.get("correct_answer") or "")
            if len(t) > 2
        ]
        try:
            nlp = get_nlp(lang)
        except ValueError:
            nlp = None
        for t in tokens:
            low = t.lower()
            if nlp is not None:
                try:
                    lemma = nlp.lemmatize(nlp.normalize(low))
                except Exception:  # noqa: BLE001 — charts are extra, never fail cram
                    lemma = low
                if lemma and lemma not in candidates:
                    candidates.append(lemma)
            if low not in candidates:
                candidates.append(low)
        if not candidates:
            continue
        plans.append((card, candidates))
        wanted.setdefault(lang, set()).update(candidates)
        # Remember the raw answer tokens too: if none of the candidates above
        # resolve, the reverse form index gets a turn below.
        by_language_tokens.setdefault(lang, []).append((card, tokens))

    if not wanted:
        return

    forms: dict[tuple[str, str], dict] = {}
    for lang, words in wanted.items():
        rows = await conn.fetch(
            """
            SELECT v.word, v.morphology, v.usage_note
            FROM vocabulary v
            JOIN languages l ON v.language_id = l.id
            WHERE l.code = $1
              AND lower(v.word) = ANY($2::text[])
              AND v.morphology IS NOT NULL
            """,
            lang,
            sorted(words),
        )
        for r in rows:
            word = r.get("word")
            m = _chartable(r.get("morphology"))
            if not word or m is None:
                continue
            forms.setdefault((lang, word.lower()), {
                "word": word,
                "morphology": m,
                "usage_note": r.get("usage_note"),
            })

    def _apply(card: dict, hit: dict) -> None:
        card["morphology"] = hit["morphology"]
        card["chart_word"] = hit["word"]
        card["chart_usage_note"] = hit["usage_note"]

    unresolved: dict[str, list[tuple[dict, list[str]]]] = {}
    for card, candidates in plans:
        for cand in candidates:
            hit = forms.get((card["language_code"], cand))
            if hit is not None:
                _apply(card, hit)
                break
    for lang, entries in by_language_tokens.items():
        misses = [e for e in entries if e[0].get("morphology") is None]
        if misses:
            unresolved[lang] = misses

    # Second pass: look the drill's own surface answer up in the charts. This
    # is what covers the ordinary case — no stored lemma, an English hint, and
    # a language whose lemmatizer only folds accents.
    for lang, entries in unresolved.items():
        try:
            index = await _chart_form_index(conn, lang)
        except Exception:  # noqa: BLE001 — charts are extra, never fail cram
            continue
        if not index:
            continue
        headwords = {
            index[key]
            for _card, tokens in entries
            for key in (_form_key(t) for t in tokens)
            if key in index
        }
        if not headwords:
            continue
        rows = await conn.fetch(
            """
            SELECT v.word, v.morphology, v.usage_note
            FROM vocabulary v
            JOIN languages l ON v.language_id = l.id
            WHERE l.code = $1
              AND v.word = ANY($2::text[])
              AND v.morphology IS NOT NULL
            """,
            lang,
            sorted(headwords),
        )
        found: dict[str, dict] = {}
        for r in rows:
            word = r.get("word")
            m = _chartable(r.get("morphology"))
            if word and m is not None:
                found[word] = {
                    "word": word,
                    "morphology": m,
                    "usage_note": r.get("usage_note"),
                }
        for card, tokens in entries:
            for token in tokens:
                head = index.get(_form_key(token))
                hit = found.get(head) if head else None
                if hit is not None:
                    _apply(card, hit)
                    break


async def get_deck_preview(
    conn: asyncpg.Connection, list_id: str, limit: int = 20
) -> dict | None:
    """A peek inside a deck before subscribing: its first items in order.

    Vocabulary decks list the first words by frequency with their English
    definition; grammar decks list the first points in path order with the
    can-do line. Enough to judge "do I want this deck?" at a glance.
    """
    cl = await conn.fetchrow(
        "SELECT id, language_id, list_type, level, title FROM content_lists WHERE id = $1",
        list_id,
    )
    if cl is None:
        return None
    if cl["list_type"] == "grammar":
        rows = await conn.fetch(
            """
            SELECT gp.title AS item, gp.function_note AS detail
            FROM grammar_points gp
            JOIN languages l ON gp.language_id = l.id
            WHERE gp.language_id = $1
              AND ($2::text IS NULL OR gp.level = $2)
              AND (CASE l.grammar_review_policy
                    WHEN 'all'  THEN true
                    WHEN 'both' THEN (gp.reviewed AND gp.ai_check_status = 'pass')
                    WHEN 'ai_ok' THEN (gp.reviewed OR gp.ai_check_status = 'pass')
                    ELSE gp.reviewed END)
            ORDER BY gp.display_order ASC, gp.title
            LIMIT $3
            """,
            cl["language_id"], cl["level"], limit,
        )
    else:
        rows = await fetch_explicit_gated(
            conn,
            """
            SELECT v.word AS item, t.definition AS detail
            FROM vocabulary v
            LEFT JOIN translations t
                   ON v.id = t.vocabulary_id AND t.locale = 'en'
            WHERE v.language_id = $1
              AND ($2::text IS NULL OR v.level = $2)
              AND (v.level_source <> 'ai'
                   OR EXISTS (SELECT 1 FROM languages lp
                               WHERE lp.id = v.language_id
                                 AND lp.grammar_review_policy IN ('ai_ok', 'all')))
              {explicit}
            ORDER BY v.frequency_rank ASC NULLS LAST, v.word
            LIMIT $3
            """,
            cl["language_id"], cl["level"], limit,
            alias="v",
        )
    return {
        "id": str(cl["id"]),
        "title": cl["title"],
        "list_type": cl["list_type"],
        "level": cl["level"],
        "items": [{"item": r["item"], "detail": r["detail"]} for r in rows],
    }


def _card_status(is_suspended: bool | None, repetitions: int | None) -> str:
    """Classify a (possibly absent) user_cards row for the deck browser.
    Mirrors the is_suspended/repetitions discriminators the learn-candidate
    queries and mark_card_known already rely on elsewhere in this module."""
    if repetitions is None:
        return "new"
    if is_suspended and repetitions == 0:
        return "learning"
    if is_suspended:
        return "known"
    return "active"


async def get_deck_items(
    conn: asyncpg.Connection,
    list_id: str,
    limit: int = 2500,
    support_locale: str | None = None,
) -> dict | None:
    """The deck browser's full item listing (Bunpro's deck page): every item
    in path order with its id, so each row can expand into a detail view.
    Unlike get_deck_preview this is the whole deck, id included, and grammar
    rows carry their review state so reviewers can spot drafts.

    Each item also carries the CALLER's own learner status (owner: cards
    need to be individually resettable, which means the deck browser must
    first show which ones have progress to reset):
      - "new": no user_cards row yet.
      - "learning": teach-gate pending (is_suspended AND repetitions = 0) —
        taught but not yet confirmed with a correct first-check answer.
      - "known": retired via mark_card_known (is_suspended, repetitions >= 1)
        — either explicitly retired from Review, or skipped in Learn.
      - "active": in the normal FSRS review rotation.
    No explicit user_id filter on the join — RLS (user_cards_select_own)
    already scopes it to the caller under rls_connection.
    """
    cl = await conn.fetchrow(
        "SELECT id, language_id, list_type, level, title FROM content_lists WHERE id = $1",
        list_id,
    )
    if cl is None:
        return None
    if cl["list_type"] == "grammar":
        eff = await _effective_locale(conn, str(cl["language_id"]), support_locale)
        gpt = _gpt_sql(
            await _table_exists(conn, "grammar_point_translations"), "$4"
        )
        rows = await conn.fetch(
            f"""
            SELECT gp.id, {gpt["title"]} AS item,
                   {gpt["function_note"]} AS detail,
                   gp.level, gp.reviewed, uc.id AS user_card_id,
                   uc.is_suspended, uc.repetitions
            FROM grammar_points gp
            JOIN languages l ON gp.language_id = l.id
            LEFT JOIN user_cards uc
                   ON uc.card_id = gp.id AND uc.card_type = 'grammar'
            {gpt["join"]}
            WHERE gp.language_id = $1
              AND ($2::text IS NULL OR gp.level = $2)
              AND (CASE l.grammar_review_policy
                    WHEN 'all'  THEN true
                    WHEN 'both' THEN (gp.reviewed AND gp.ai_check_status = 'pass')
                    WHEN 'ai_ok' THEN (gp.reviewed OR gp.ai_check_status = 'pass')
                    ELSE gp.reviewed END)
            ORDER BY gp.display_order ASC, gp.title
            LIMIT $3
            """,
            cl["language_id"], cl["level"], limit, eff,
        )
        await note_missing_content(conn, eff,
                                   grammar_ids=[r["id"] for r in rows])
        items = [
            {"id": str(r["id"]), "kind": "grammar", "item": r["item"],
             "detail": r["detail"], "level": r["level"],
             "reviewed": r["reviewed"],
             "user_card_id": str(r["user_card_id"]) if r["user_card_id"] else None,
             "status": _card_status(r["is_suspended"], r["repetitions"])}
            for r in rows
        ]
    else:
        # English decks browsed by a "from X" learner list definitions in X
        # (same rule as cards: the support locale only applies to English).
        eff = await _effective_locale(conn, str(cl["language_id"]), support_locale)
        rows = await fetch_explicit_gated(
            conn,
            """
            SELECT v.id, v.word AS item,
                   COALESCE(t.definition, t_en.definition) AS detail, v.level,
                   uc.id AS user_card_id, uc.is_suspended, uc.repetitions
            FROM vocabulary v
            LEFT JOIN translations t
                   ON v.id = t.vocabulary_id AND t.locale = $4
            LEFT JOIN translations t_en
                   ON v.id = t_en.vocabulary_id AND t_en.locale = 'en'
            LEFT JOIN user_cards uc
                   ON uc.card_id = v.id AND uc.card_type = 'vocabulary'
            WHERE v.language_id = $1
              AND ($2::text IS NULL OR v.level = $2)
              AND (v.level_source <> 'ai'
                   OR EXISTS (SELECT 1 FROM languages lp
                               WHERE lp.id = v.language_id
                                 AND lp.grammar_review_policy IN ('ai_ok', 'all')))
              {explicit}
            ORDER BY v.frequency_rank ASC NULLS LAST, v.word
            LIMIT $3
            """,
            cl["language_id"], cl["level"], limit, eff,
            alias="v",
        )
        await note_missing_content(conn, eff,
                                   vocab_ids=[r["id"] for r in rows])
        items = [
            {"id": str(r["id"]), "kind": "vocabulary", "item": r["item"],
             "detail": r["detail"], "level": r["level"], "reviewed": True,
             "user_card_id": str(r["user_card_id"]) if r["user_card_id"] else None,
             "status": _card_status(r["is_suspended"], r["repetitions"])}
            for r in rows
        ]
    return {
        "id": str(cl["id"]),
        "title": cl["title"],
        "list_type": cl["list_type"],
        "level": cl["level"],
        "items": items,
    }


async def get_vocab_item(
    conn: asyncpg.Connection, vocab_id: str, support_locale: str | None = None
) -> dict | None:
    """A vocabulary item's read-only detail for the deck browser: word,
    definition, morphology (the Forms panel), and a few example sentences.
    Works without the item being in the caller's reviews.
    """
    row = await conn.fetchrow(
        """
        SELECT v.id, v.word, v.reading, v.part_of_speech, v.usage_note,
               v.morphology, v.level, l.code AS language_code,
               COALESCE(t.definition, t_en.definition) AS definition
        FROM vocabulary v
        JOIN languages l ON v.language_id = l.id
        LEFT JOIN translations t
               ON v.id = t.vocabulary_id AND t.locale = $2
        LEFT JOIN translations t_en
               ON v.id = t_en.vocabulary_id AND t_en.locale = 'en'
        WHERE v.id = $1
        """,
        vocab_id, support_locale or "en",
    )
    if row is None:
        return None
    # Same rule as _effective_locale: any course prefers the support
    # locale's sentence rows, falling back per sentence to the English one.
    eff = support_locale if support_locale and support_locale != "en" else "en"
    examples = await _fetch_examples(
        conn,
        """
        SELECT sentence, translation
        FROM (
            SELECT DISTINCT ON (es.sentence)
                   es.sentence,
                   CASE WHEN es.translation_locale IN ($2, 'en')
                        THEN es.translation END AS translation,
                   es.difficulty_rank
            FROM example_sentences es
            WHERE es.vocabulary_id = $1
              AND (es.translation_locale IN ($2, 'en')
                   -- ...or the sentence already reads in the learner's own
                   -- language: the English course, whose bank has no 'en'
                   -- rows. Translation nulled above, never substituted.
                   OR es.language_id IN (
                       SELECT id FROM languages WHERE code = $2))
              AND es.reviewed
              {explicit}
            ORDER BY es.sentence, (es.translation_locale = $2) DESC,
                     (es.translation_locale = 'en') DESC, es.id
        ) pes
        ORDER BY difficulty_rank ASC NULLS LAST
        LIMIT 5
        """,
        vocab_id, eff,
        alias="es",
    )
    await note_missing_content(conn, eff, vocab_ids=[vocab_id])
    return {
        "id": str(row["id"]),
        "word": row["word"],
        "reading": row["reading"],
        "part_of_speech": row["part_of_speech"],
        "usage_note": row["usage_note"],
        "definition": row["definition"],
        "level": row["level"],
        "language_code": row["language_code"],
        "morphology": row["morphology"],
        "examples": [
            {"sentence": e["sentence"], "translation": e["translation"]}
            for e in examples
        ],
    }


async def reset_deck_progress(
    conn: asyncpg.Connection, user_id: str, list_id: str
) -> dict | None:
    """Wipe the learner's progress for one deck, review history included.

    Deletes the user_cards rows for items belonging to the deck (membership
    is level-based, mirroring the learn queries); review_log rows go with
    them via ON DELETE CASCADE. Content and deck subscriptions are untouched
    — the learner can start the deck over immediately. Returns None when the
    deck doesn't exist.
    """
    cl = await conn.fetchrow(
        "SELECT language_id, list_type, level FROM content_lists WHERE id = $1",
        list_id,
    )
    if cl is None:
        return None
    if cl["list_type"] == "grammar":
        result = await conn.execute(
            """
            DELETE FROM user_cards uc
            USING grammar_points gp
            WHERE uc.user_id = $1
              AND uc.card_type = 'grammar'
              AND uc.card_id = gp.id
              AND gp.language_id = $2
              AND ($3::text IS NULL OR gp.level = $3)
            """,
            user_id, cl["language_id"], cl["level"],
        )
    else:
        result = await conn.execute(
            """
            DELETE FROM user_cards uc
            USING vocabulary v
            WHERE uc.user_id = $1
              AND uc.card_type = 'vocabulary'
              AND uc.card_id = v.id
              AND v.language_id = $2
              AND ($3::text IS NULL OR v.level = $3)
            """,
            user_id, cl["language_id"], cl["level"],
        )
    return {"cards_deleted": int(result.split()[-1])}


async def reset_language_progress(
    conn: asyncpg.Connection, user_id: str, language_id: str | None = None
) -> dict:
    """Wipe the learner's studies — one language, or everything when None.

    Deletes every user_cards row in scope (grammar, vocabulary, AND personal
    cards' schedules); review_log cascades. User-authored content survives:
    notes, personal cloze sentences, and deck subscriptions stay, so a fresh
    start doesn't destroy anything the learner wrote themselves.
    """
    result = await conn.execute(
        """
        DELETE FROM user_cards
        WHERE user_id = $1
          AND ($2::uuid IS NULL OR language_id = $2)
        """,
        user_id, language_id,
    )
    return {"cards_deleted": int(result.split()[-1])}


async def reset_card_progress(conn: asyncpg.Connection, card_id: str) -> bool:
    """Wipe ONE card's progress — the single-card sibling of
    reset_deck_progress/reset_language_progress (owner: cards need to be
    resettable individually, not just by nuking the whole deck).

    Deletes the user_cards row outright (review_log cascades), the same
    "gone means fresh start" semantics the deck/language resets use: the
    card simply re-qualifies as a new Learn candidate next time. This is
    also how a mistaken "I already know this" (mark_card_known) gets
    undone — the card just needs to be met and taught again.

    No explicit user_id filter: RLS (user_cards_delete_own) already scopes
    the delete to the caller's own row, matching mark_card_known's style.
    Returns False when the id doesn't exist (or isn't the caller's) so the
    router can 404.
    """
    result = await conn.execute("DELETE FROM user_cards WHERE id = $1", card_id)
    return result != "DELETE 0"


async def set_deck_subscription(
    conn: asyncpg.Connection, user_id: str, list_id: str, subscribed: bool
) -> bool:
    """Add or remove a deck from the learner's queue. Returns success.

    Unsubscribing only stops NEW cards from being drawn — cards already
    learned keep their FSRS schedule (removing a deck never deletes
    progress).
    """
    exists = await conn.fetchval(
        "SELECT 1 FROM content_lists WHERE id = $1", list_id
    )
    if not exists:
        return False
    if subscribed:
        await conn.execute(
            """
            INSERT INTO user_content_subscriptions (user_id, content_list_id)
            VALUES ($1, $2) ON CONFLICT (user_id, content_list_id) DO NOTHING
            """,
            user_id, list_id,
        )
    else:
        await conn.execute(
            "DELETE FROM user_content_subscriptions "
            "WHERE user_id = $1 AND content_list_id = $2",
            user_id, list_id,
        )
    return True
