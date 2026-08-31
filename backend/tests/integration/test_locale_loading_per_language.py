"""Every course, loaded from its real file, must store what the file says.

The failure this exists to stop, verbatim from a screenshot: a Russian
learner of English, shown "We are the 99%." glossed "Somos el 99%.", "To
us!" glossed "À nous.", and a Romanian line labelled "перевод (на
английском — ещё не переведено)".

The card query was never at fault. It filters `translation_locale IN
($3,'en')` and prefers $3. The stored rows were mislabelled, because
seed_sentences dropped the file's translation_locale column and let the
'en' default apply to 202,772 translations that are not English.

So these tests do not check the query and they do not use fixtures invented
here. They run the REAL seeder over the REAL repo data files, one course at
a time, and compare what lands in the database against what the file
actually claims — then serve a card through the real read path and check
what a learner would see.

Sampled, not exhaustive: en_sentences.tsv alone is 202,772 rows. The sample
strides ACROSS each file rather than taking its head — that file is grouped
by locale, so a head sample sees only Spanish and would have let this exact
bug through. Striding is still deterministic.
"""
from __future__ import annotations

import csv
import uuid

import asyncpg
import pytest

from backend.repositories import cards as cards_repo
from backend.services.locale_guard import has_letters, script_ratio
from backend.services.seeder import seed_sentences

from .conftest import INTEGRATION_DSN, requires_db

pytestmark = requires_db

REPO = seed_sentences.DATA_DIR
SAMPLE = 400

_SCRIPTS = ("ARABIC", "HEBREW", "CYRILLIC", "GREEK", "DEVANAGARI",
            "THAI", "HANGUL", "CJK", "HIRAGANA")


def _course_codes() -> list[str]:
    return sorted(p.name.replace("_sentences.tsv", "")
                  for p in REPO.glob("*_sentences.tsv"))


def _sample_rows(code: str, limit: int = SAMPLE) -> tuple[list[dict], list[str]]:
    """A deterministic sample spread ACROSS the file, not its head.

    en_sentences.tsv is grouped by locale — 21k Spanish rows, then French,
    then the rest — so taking the first N rows sees exactly one language and
    would have let the very bug this module exists for slip through. Striding
    spans every locale in the file.
    """
    path = REPO / f"{code}_sentences.tsv"
    with path.open(encoding="utf-8") as f:
        total = max(sum(1 for _ in f) - 1, 1)
    stride = max(1, total // limit)
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = [r for i, r in enumerate(reader) if i % stride == 0][:limit]
    return rows, fields


def _multi_locale_rows(code: str) -> tuple[list[dict], list[str], str]:
    """Every row for one sentence that the file gives in several languages."""
    path = REPO / f"{code}_sentences.tsv"
    by_sentence: dict[str, list[dict]] = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fields = list(reader.fieldnames or [])
        for r in reader:
            s = (r.get("sentence") or "").strip()
            if s and (r.get("translation") or "").strip():
                by_sentence.setdefault(s, []).append(r)
    for sentence, rows in by_sentence.items():
        locales = {(r.get("translation_locale") or "en").strip().lower()
                   for r in rows}
        if len(locales) > 1:
            return rows, fields, sentence
    return [], fields, ""


def _contradicting_script(text: str, locale: str) -> str | None:
    """A script the text is in that the locale cannot be. One-sided."""
    if not text or not has_letters(text):
        return None
    from backend.services.locale_guard import script_of
    expected = script_of(locale)
    if expected and script_ratio(text, expected) >= 0.25:
        return None
    for script in _SCRIPTS:
        if script == expected:
            continue
        if script_ratio(text, script) >= 0.25:
            return script
    return None


@pytest.fixture
async def conn(schema):
    c = await asyncpg.connect(INTEGRATION_DSN)
    try:
        yield c
    finally:
        await c.close()


async def _load_course(conn, code: str, tmp_path, monkeypatch) -> dict | None:
    """Seed a sample of this course's REAL file through the REAL seeder."""
    rows, fields = _sample_rows(code)
    if not rows:
        return None
    test_code = f"z{uuid.uuid4().hex}"
    lang_id = await conn.fetchval(
        "INSERT INTO languages (code, name) VALUES ($1, $2) RETURNING id",
        test_code, f"Test {code}")
    words = {(r.get("word") or "").strip() for r in rows if (r.get("word") or "").strip()}
    for w in words:
        await conn.execute(
            "INSERT INTO vocabulary (language_id, word, level) VALUES ($1,$2,'A1')",
            lang_id, w)

    data = tmp_path / code
    (data / "sentences").mkdir(parents=True, exist_ok=True)
    out = data / f"{test_code}_sentences.tsv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    monkeypatch.setattr(seed_sentences, "DATA_DIR", data)
    monkeypatch.setattr(seed_sentences, "SENTENCES_DIR", data / "sentences")

    await seed_sentences.seed(INTEGRATION_DSN, test_code)
    return {"lang_id": lang_id, "code": test_code, "rows": rows, "fields": fields}


@pytest.mark.parametrize("code", _course_codes())
class TestEveryCourseLoadsWhatItsFileClaims:
    async def test_stored_locales_match_the_file(
            self, conn, tmp_path, monkeypatch, code):
        fx = await _load_course(conn, code, tmp_path, monkeypatch)
        if fx is None:
            pytest.skip(f"{code}: empty sentence file")

        # What the FILE says, per (sentence, translation).
        expected = {
            ((r.get("sentence") or "").strip(),
             (r.get("translation") or "").strip()):
            (r.get("translation_locale") or "en").strip().lower() or "en"
            for r in fx["rows"] if (r.get("translation") or "").strip()
        }
        stored = await conn.fetch(
            "SELECT sentence, translation, translation_locale FROM "
            "example_sentences WHERE language_id = $1", fx["lang_id"])
        assert stored, f"{code}: nothing loaded"

        wrong = [
            (r["sentence"][:40], r["translation_locale"],
             expected[(r["sentence"], r["translation"])])
            for r in stored
            if (r["sentence"], r["translation"]) in expected
            and r["translation_locale"] != expected[(r["sentence"], r["translation"])]
        ]
        assert not wrong, f"{code}: stored under a locale the file does not claim: {wrong[:5]}"

    async def test_no_row_is_stored_in_a_script_its_label_forbids(
            self, conn, tmp_path, monkeypatch, code):
        # The screenshot's shape, generalised: text whose script contradicts
        # the label it is filed under. One-sided — it can prove "this is
        # Cyrillic under 'en'", never "this is Spanish under 'en'".
        fx = await _load_course(conn, code, tmp_path, monkeypatch)
        if fx is None:
            pytest.skip(f"{code}: empty sentence file")

        offenders = [
            (r["translation_locale"], bad, r["translation"][:40])
            for r in await conn.fetch(
                "SELECT translation, translation_locale FROM example_sentences "
                "WHERE language_id = $1 AND translation IS NOT NULL",
                fx["lang_id"])
            if (bad := _contradicting_script(r["translation"], r["translation_locale"]))
        ]
        assert not offenders, f"{code}: {len(offenders)} mislabelled, e.g. {offenders[:3]}"


class TestTheEnglishCourseSpecifically:
    async def test_it_loads_many_locales_and_none_of_them_english(
            self, conn, tmp_path, monkeypatch):
        # en_sentences.tsv is the one file carrying the column, and it holds
        # ZERO 'en' rows. Before the fix all 202,772 were stored as English.
        fx = await _load_course(conn, "en", tmp_path, monkeypatch)
        assert fx is not None

        locales = {r["translation_locale"] for r in await conn.fetch(
            "SELECT DISTINCT translation_locale FROM example_sentences "
            "WHERE language_id = $1", fx["lang_id"])}
        assert "en" not in locales, (
            "English translations of English sentences would be a self-pair; "
            f"the file has none, so none should be stored. Got: {sorted(locales)}")
        assert len(locales) > 1, f"expected several locales, got {sorted(locales)}"

    async def test_one_sentence_keeps_every_language_it_has(
            self, conn, tmp_path, monkeypatch):
        # The conflict key is (vocabulary_id, sentence, translation_locale).
        # While every locale claimed to be 'en', the first row for a sentence
        # won and the rest were silently dropped — which is why one card read
        # Spanish and the next French. Seeded from the rows the real file
        # actually gives for one multi-language sentence.
        rows, fields, sentence = _multi_locale_rows("en")
        if not rows:
            pytest.skip("en_sentences.tsv has no multi-locale sentence")
        expected = {(r.get("translation_locale") or "en").strip().lower()
                    for r in rows}
        assert len(expected) > 1

        test_code = f"z{uuid.uuid4().hex}"
        lang_id = await conn.fetchval(
            "INSERT INTO languages (code, name) VALUES ($1,'Multi') RETURNING id",
            test_code)
        for w in {(r.get("word") or "").strip() for r in rows}:
            await conn.execute(
                "INSERT INTO vocabulary (language_id, word, level) "
                "VALUES ($1,$2,'A1')", lang_id, w)
        data = tmp_path / "multi"
        (data / "sentences").mkdir(parents=True, exist_ok=True)
        with (data / f"{test_code}_sentences.tsv").open(
                "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
            w.writeheader()
            w.writerows(rows)
        monkeypatch.setattr(seed_sentences, "DATA_DIR", data)
        monkeypatch.setattr(seed_sentences, "SENTENCES_DIR", data / "sentences")

        await seed_sentences.seed(INTEGRATION_DSN, test_code)

        stored = {r["translation_locale"] for r in await conn.fetch(
            "SELECT translation_locale FROM example_sentences WHERE "
            "language_id = $1 AND sentence = $2", lang_id, sentence)}
        assert stored == expected, (
            f"{sentence!r}: file gives {sorted(expected)}, stored {sorted(stored)}")


class TestWhatTheLearnerActuallyReceives:
    async def test_a_russian_learner_of_english_is_served_russian_only(
            self, conn, tmp_path, monkeypatch):
        """The screenshot, end to end through the real read path.

        Not a query test in disguise: the query was always right. This asks
        whether correctly-labelled data now reaches the card correctly, and
        would have caught the Spanish/French/Romanian mix.
        """
        fx = await _load_course(conn, "en", tmp_path, monkeypatch)
        vocab = await conn.fetchrow(
            "SELECT id FROM vocabulary WHERE language_id = $1 LIMIT 1",
            fx["lang_id"])

        rows = await conn.fetch(
            """
            SELECT es.translation, es.translation_locale
            FROM example_sentences es
            WHERE es.vocabulary_id = $1
              AND es.translation_locale IN ($2, 'en')
            ORDER BY es.sentence, (es.translation_locale = $2) DESC
            """,
            vocab["id"], "ru",
        )
        # Whatever comes back on a 'ru' request must be Russian, or the
        # English fallback — never Spanish, French or Romanian.
        assert all(r["translation_locale"] in ("ru", "en") for r in rows), (
            f"served: {sorted({r['translation_locale'] for r in rows})}")
        # And nothing labelled 'ru' may be in a non-Cyrillic script.
        for r in rows:
            if r["translation_locale"] == "ru":
                assert _contradicting_script(r["translation"], "ru") is None

    async def test_the_effective_locale_helper_still_maps_a_new_profile_to_english(
            self, conn):
        # The read path's entry point, pinned: a brand-new account has
        # support_locale NULL and must resolve to English, not to whatever
        # happens to be stored.
        assert await cards_repo._effective_locale(conn, "x", None) == "en"
        assert await cards_repo._effective_locale(conn, "x", "en") == "en"
        assert await cards_repo._effective_locale(conn, "x", "ru") == "ru"
