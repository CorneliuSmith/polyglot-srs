"""Data sourcing pipeline for vocabulary frequency lists and example sentences.

Builds the merged TSVs the language seeders consume (data/{code}_frequency.tsv)
and example-sentence TSVs (data/{code}_sentences.tsv) from openly licensed
datasets — no scraping involved:

Frequency (how common a word is — drives ordering and CEFR levels):
  - Turkish: HermitDave FrequencyWords (OpenSubtitles 2018), CC-BY-SA-4.0.
  - Swahili: no OpenSubtitles list exists; counts are derived from the
    public-domain Swahili New Testament in christos-c/bible-corpus, with
    conjugated verbs folded onto their stems via SwahiliNLP. Re-run against
    a Leipzig Corpora or An Crúbadán list for production if you can fetch
    them (their hosts are blocked from some environments).

Translations (word -> English gloss + part of speech):
  - Preferred: kaikki.org Wiktionary extracts (CC-BY-SA-3.0) — biggest
    coverage, commerce-friendly with attribution. Large downloads, so they
    are opt-in via --source kaikki.
  - Fallback: FreeDict TEI dictionaries on GitHub (GPL-2.0-or-later) —
    small but instantly fetchable. Fine for server-side use; prefer kaikki
    before distributing the data.

Example sentences (graded by progression):
  - Tatoeba per-language exports (CC-BY-2.0-FR). Each sentence gets a
    difficulty_rank = the frequency rank of its rarest known word, so the
    app can serve i+1 sentences: examples where everything is within the
    learner's vocabulary except the card being studied.

Yoruba:
  - Frequency: contemporary diacritized corpora (TheYorubaBlog + Iroyin
    news) from Niger-Volta-LTI/yoruba-text (GPL-3.0), fetched via sparse
    git clone — the full repo is 500MB; we take ~1MB.
  - Translations: kaikki.org Yoruba extract only (no FreeDict dictionary
    exists). Tone-stripped fallback matching links corpus tokens whose
    tone marks differ from the Wiktionary headword.

Usage:
    python -m backend.services.seeder.source_data --language tr
    python -m backend.services.seeder.source_data --language sw
    python -m backend.services.seeder.source_data --language yo --source kaikki
    python -m backend.services.seeder.source_data --language tr --source kaikki
    python -m backend.services.seeder.source_data --language tr --sentences
"""
from __future__ import annotations

import argparse
import bz2
import csv
import json
import logging
import re
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import httpx

from backend.services.nlp.arabic import ArabicNLP
from backend.services.nlp.hausa import HausaNLP, normalize_hausa
from backend.services.nlp.latin_base import (
    CatalanNLP,
    FrenchNLP,
    GermanNLP,
    GreekNLP,
    ItalianNLP,
    MaoriNLP,
    RomanianNLP,
    SpanishNLP,
)
from backend.services.nlp.russian import RussianNLP
from backend.services.nlp.swahili import SwahiliNLP
from backend.services.nlp.turkish import TurkishNLP, turkish_lower
from backend.services.nlp.xhosa import XhosaNLP
from backend.services.nlp.yoruba import YorubaNLP, strip_tones
from backend.services.seeder.base import DATA_DIR

# Languages sourced generically from a HermitDave frequency list
# (OpenSubtitles) + a kaikki Wiktionary dictionary. The path is
# script-agnostic — ro/el/ar ride the same rails as the Latin five; it just
# needs a frequency list, a kaikki extract, and a lemmatizer.
FREQUENCYWORDS_LANGS = {"es", "it", "fr", "de", "ca", "ro", "el", "ar", "ru"}
LATIN_NLP = {
    "es": SpanishNLP, "it": ItalianNLP, "fr": FrenchNLP,
    "de": GermanNLP, "ca": CatalanNLP, "mi": MaoriNLP,
}
# Lemmatizers for the generic path (superset of LATIN_NLP). Russian's
# pymorphy3 normal_form folds OpenSubtitles inflections onto kaikki
# headwords — the OpenRussian download host no longer resolves, so Russian
# rides these rails too.
FREQ_NLP = {
    **LATIN_NLP,
    "ro": RomanianNLP, "el": GreekNLP, "ar": ArabicNLP, "ru": RussianNLP,
}

logger = logging.getLogger("source_data")

TEI_NS = "{http://www.tei-c.org/ns/1.0}"

SOURCES = {
    "tr_frequency": (
        "https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
        "master/content/2018/tr/tr_50k.txt"
    ),
    "tr_freedict": (
        "https://raw.githubusercontent.com/freedict/fd-dictionaries/"
        "master/tur-eng/tur-eng.tei"
    ),
    "sw_freedict": (
        "https://raw.githubusercontent.com/freedict/fd-dictionaries/"
        "master/swh-eng/swh-eng.tei"
    ),
    "sw_corpus": (
        "https://raw.githubusercontent.com/christos-c/bible-corpus/"
        "master/bibles/Swahili-NT.xml"
    ),
    "tr_kaikki": "https://kaikki.org/dictionary/Turkish/kaikki.org-dictionary-Turkish.jsonl",
    "sw_kaikki": "https://kaikki.org/dictionary/Swahili/kaikki.org-dictionary-Swahili.jsonl",
    "yo_kaikki": "https://kaikki.org/dictionary/Yoruba/kaikki.org-dictionary-Yoruba.jsonl",
    "xh_kaikki": "https://kaikki.org/dictionary/Xhosa/kaikki.org-dictionary-Xhosa.jsonl",
    "ha_kaikki": "https://kaikki.org/dictionary/Hausa/kaikki.org-dictionary-Hausa.jsonl",
    "es_kaikki": "https://kaikki.org/dictionary/Spanish/kaikki.org-dictionary-Spanish.jsonl",
    "it_kaikki": "https://kaikki.org/dictionary/Italian/kaikki.org-dictionary-Italian.jsonl",
    "fr_kaikki": "https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl",
    "de_kaikki": "https://kaikki.org/dictionary/German/kaikki.org-dictionary-German.jsonl",
    "ca_kaikki": "https://kaikki.org/dictionary/Catalan/kaikki.org-dictionary-Catalan.jsonl",
    "mi_kaikki": "https://kaikki.org/dictionary/Maori/kaikki.org-dictionary-Maori.jsonl",
    "ro_kaikki": "https://kaikki.org/dictionary/Romanian/kaikki.org-dictionary-Romanian.jsonl",
    "el_kaikki": "https://kaikki.org/dictionary/Greek/kaikki.org-dictionary-Greek.jsonl",
    "ar_kaikki": "https://kaikki.org/dictionary/Arabic/kaikki.org-dictionary-Arabic.jsonl",
    "ru_kaikki": "https://kaikki.org/dictionary/Russian/kaikki.org-dictionary-Russian.jsonl",
    # HermitDave FrequencyWords (OpenSubtitles 2018), per ISO code.
    "frequencywords": (
        "https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
        "master/content/2018/{code}/{code}_50k.txt"
    ),
    "yo_corpus_repo": "https://github.com/Niger-Volta-LTI/yoruba-text.git",
    # Public-domain bible corpus — frequency bootstrap for Xhosa (no
    # OpenSubtitles list exists). Prefer a CC-BY Leipzig/Wikipedia list for
    # production register coverage.
    "xh_corpus": (
        "https://raw.githubusercontent.com/christos-c/bible-corpus/"
        "master/bibles/Xhosa.xml"
    ),
    # Tatoeba ISO-639-3 codes: tur = Turkish, swh = coastal Swahili
    "tatoeba_sentences": "https://downloads.tatoeba.org/exports/per_language/{iso3}/{iso3}_sentences.tsv.bz2",
    "tatoeba_links": "https://downloads.tatoeba.org/exports/per_language/{iso3}/{iso3}-eng_links.tsv.bz2",
    "tatoeba_eng": "https://downloads.tatoeba.org/exports/per_language/eng/eng_sentences.tsv.bz2",
    # English Wiktionary extract (gzipped, ~475MB): the only kaikki file whose
    # entries carry per-language TRANSLATION arrays — one download localizes
    # English vocabulary into every support language at once.
    "en_kaikki_gz": (
        "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl.gz"
    ),
}

# Support locales for English-as-target study ("I'm learning English from
# Spanish"): locale code -> Tatoeba ISO-639-3, for building English example
# sentences whose translations are in the LEARNER's language. These reuse
# the same cached Tatoeba files the per-language sentence builds download.
ENGLISH_SUPPORT_ISO3 = {
    "es": "spa", "fr": "fra", "de": "deu", "it": "ita", "ru": "rus",
    "tr": "tur", "ar": "ara", "el": "ell", "ro": "ron", "ca": "cat",
    "sw": "swh",
}

TATOEBA_ISO3 = {
    "tr": "tur", "sw": "swh", "yo": "yor", "ha": "hau", "xh": "xho",
    # European tier + ru/ar (well-covered on Tatoeba)
    "es": "spa", "fr": "fra", "de": "deu", "it": "ita", "ca": "cat",
    "ro": "ron", "el": "ell", "ru": "rus", "ar": "ara",
}

# Hausa has no reachable public-domain corpus in this pipeline; the user drops
# commercially-usable plain-text (Hausa Wikipedia CC-BY-SA, Leipzig CC-BY, or
# OPUS news) here and the pipeline counts it.
HAUSA_CORPUS_DIRNAME = "hausa_corpus"

# Contemporary, openly licensed sub-corpora of Niger-Volta-LTI/yoruba-text.
# Deliberately excludes JW300 (jw.org terms are restrictive) and keeps the
# religious texts out of the frequency model (register skew).
YORUBA_CORPUS_DIRS = ("TheYorubaBlog", "Iroyin", "Owe/yo")


def download(url: str, dest: Path, timeout: float = 300.0) -> Path:
    """Download *url* to *dest* (skips when the file already exists)."""
    if dest.exists() and dest.stat().st_size > 0:
        logger.info("Using cached %s", dest.name)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s", url)
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
    return dest


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_hermitdave(path: Path) -> list[tuple[int, str, int]]:
    """Parse a FrequencyWords list ("word count" per line) -> [(rank, word, count)]."""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 2 or not parts[1].isdigit():
                continue
            out.append((len(out) + 1, parts[0], int(parts[1])))
    return out


def parse_freedict_tei(path: Path) -> dict[str, dict]:
    """Parse a FreeDict TEI dictionary -> {headword: {pos, gloss, plural}}.

    Senses carry either <def> text or <cit type="trans"><quote> translations;
    multiple senses are joined with "; ". Swahili entries may carry an
    <xr type="plural-form"> cross-reference, captured as "plural".
    """
    entries: dict[str, dict] = {}
    tree = ET.parse(path)
    for entry in tree.iter(f"{TEI_NS}entry"):
        orth = entry.find(f"{TEI_NS}form/{TEI_NS}orth")
        if orth is None or not (orth.text or "").strip():
            continue
        word = orth.text.strip()

        pos_el = entry.find(f"{TEI_NS}gramGrp/{TEI_NS}pos")
        pos = (pos_el.text or "").strip() if pos_el is not None else None

        glosses: list[str] = []
        for sense in entry.findall(f"{TEI_NS}sense"):
            d = sense.find(f"{TEI_NS}def")
            if d is not None and (d.text or "").strip():
                glosses.append(d.text.strip())
                continue
            for quote in sense.findall(f"{TEI_NS}cit/{TEI_NS}quote"):
                if (quote.text or "").strip():
                    glosses.append(quote.text.strip())
        if not glosses:
            continue

        plural = None
        for xr in entry.findall(f"{TEI_NS}xr"):
            if xr.get("type") == "plural-form":
                ref = xr.find(f"{TEI_NS}ref")
                if ref is not None and (ref.text or "").strip():
                    plural = ref.text.strip()

        entries[word.lower()] = {
            "pos": pos,
            "gloss": "; ".join(dict.fromkeys(glosses)),
            "plural": plural,
        }
    return entries


def parse_kaikki_jsonl(path: Path, wanted: set[str] | None = None) -> dict[str, dict]:
    """Stream a kaikki.org Wiktionary extract -> {word: {pos, gloss, plural}}.

    Keeps the first (most common) entry per word. Pass *wanted* to filter to
    a known word set and keep memory flat on the large dumps.
    """
    entries: dict[str, dict] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            word = (obj.get("word") or "").strip().lower()
            if not word or word in entries:
                continue
            if wanted is not None and word not in wanted:
                continue
            glosses = [
                g
                for sense in obj.get("senses") or []
                for g in sense.get("glosses") or []
            ]
            if not glosses:
                continue
            entries[word] = {
                "pos": obj.get("pos"),
                "gloss": "; ".join(dict.fromkeys(glosses[:3])),
                "plural": None,
            }
    return entries


_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def corpus_word_counts(xml_path: Path) -> Counter:
    """Count word tokens in a bible-corpus XML file (verse <seg> elements)."""
    counts: Counter = Counter()
    for _, elem in ET.iterparse(xml_path):
        if elem.tag == "seg" and elem.text:
            for token in _WORD_RE.findall(elem.text.lower()):
                counts[token] += 1
        elem.clear()
    return counts


# ---------------------------------------------------------------------------
# Builders — merge frequency + dictionary into the seeder TSV format
# ---------------------------------------------------------------------------

def write_frequency_tsv(rows: list[dict], out_path: Path) -> int:
    """Write merged rows to the rank/word/pos/en TSV the seeders consume."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["rank", "word", "pos", "en"])
        for i, row in enumerate(rows, start=1):
            writer.writerow([i, row["word"], row.get("pos") or "", row["gloss"]])
    return len(rows)


def build_turkish_rows(
    freq: list[tuple[int, str, int]],
    dictionary: dict[str, dict],
    max_words: int = 10000,
) -> list[dict]:
    """Merge the Turkish frequency list with a dictionary.

    Surface forms are matched to dictionary headwords directly, then via
    suffix-stripped lemmas, and counts aggregate onto the headword so
    "evde"/"evler" all boost "ev". Output is ordered by aggregated count.
    """
    nlp = TurkishNLP()
    agg: dict[str, int] = {}
    for _rank, form, count in freq:
        form = turkish_lower(form)
        headword = None
        if form in dictionary:
            headword = form
        else:
            lemma = nlp.lemmatize(form)
            if lemma in dictionary:
                headword = lemma
        if headword:
            agg[headword] = agg.get(headword, 0) + count

    ordered = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:max_words]
    return [
        {"word": w, "pos": dictionary[w].get("pos"), "gloss": dictionary[w]["gloss"]}
        for w, _count in ordered
    ]


def build_swahili_rows(
    counts: Counter,
    dictionary: dict[str, dict],
    max_words: int = 10000,
) -> list[dict]:
    """Merge Swahili corpus counts with a dictionary.

    Conjugated verb tokens (akasema, ninasoma...) fold onto their stems via
    SwahiliNLP before headword matching, so verb frequency reflects all of a
    verb's conjugations rather than one surface form.
    """
    nlp = SwahiliNLP()
    agg: dict[str, int] = {}
    for token, count in counts.items():
        headword = None
        if token in dictionary:
            headword = token
        else:
            stem = nlp.lemmatize(token)
            if stem != token and stem in dictionary:
                headword = stem
        if headword:
            agg[headword] = agg.get(headword, 0) + count

    ordered = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:max_words]
    return [
        {"word": w, "pos": dictionary[w].get("pos"), "gloss": dictionary[w]["gloss"]}
        for w, _count in ordered
    ]


def fetch_yoruba_corpus(cache_dir: Path) -> Path:
    """Sparse-clone the diacritized Yoruba corpora (~1-12MB of a 500MB repo)."""
    repo_dir = cache_dir / "yoruba-text"
    if repo_dir.exists() and any(repo_dir.glob("*/")):
        logger.info("Using cached yoruba-text checkout")
        return repo_dir
    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
         SOURCES["yo_corpus_repo"], str(repo_dir)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_dir), "sparse-checkout", "set", *YORUBA_CORPUS_DIRS],
        check=True, capture_output=True,
    )
    return repo_dir


def yoruba_corpus_counts(repo_dir: Path) -> Counter:
    """Count NFC-normalized word tokens across the checked-out corpora."""
    counts: Counter = Counter()
    for sub in YORUBA_CORPUS_DIRS:
        base = repo_dir / sub
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.txt")):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            text = unicodedata.normalize("NFC", text.lower())
            for token in _WORD_RE.findall(text):
                counts[token] += 1
    return counts


def build_yoruba_rows(
    counts: Counter,
    dictionary: dict[str, dict],
    max_words: int = 10000,
) -> list[dict]:
    """Merge Yoruba corpus counts with a (diacritized) dictionary.

    Corpus tokens match headwords directly first; otherwise the tone-stripped
    token is looked up against a tone-stripped headword index, so corpus text
    with inconsistent tone marking still folds onto the right Wiktionary
    entry. Counts aggregate onto the fully diacritized headword.
    """
    toneless_index: dict[str, str] = {}
    for headword in dictionary:
        toneless_index.setdefault(strip_tones(headword), headword)

    agg: dict[str, int] = {}
    for token, count in counts.items():
        token = unicodedata.normalize("NFC", token)
        headword = None
        if token in dictionary:
            headword = token
        else:
            headword = toneless_index.get(strip_tones(token))
        if headword:
            agg[headword] = agg.get(headword, 0) + count

    ordered = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:max_words]
    return [
        {"word": w, "pos": dictionary[w].get("pos"), "gloss": dictionary[w]["gloss"]}
        for w, _count in ordered
    ]


def plaintext_dir_counts(directory: Path) -> Counter:
    """Count lowercased word tokens across every .txt file under *directory*."""
    counts: Counter = Counter()
    if not directory.exists():
        return counts
    for path in sorted(directory.rglob("*.txt")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token in _WORD_RE.findall(text.lower()):
            counts[token] += 1
    return counts


def _rows_from_counts(
    counts: Counter,
    dictionary: dict[str, dict],
    lemmatize,
    max_words: int,
) -> list[dict]:
    """Aggregate corpus counts onto dictionary headwords (direct, then lemma)."""
    agg: dict[str, int] = {}
    for token, count in counts.items():
        headword = None
        if token in dictionary:
            headword = token
        else:
            lemma = lemmatize(token)
            if lemma != token and lemma in dictionary:
                headword = lemma
        if headword:
            agg[headword] = agg.get(headword, 0) + count
    ordered = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:max_words]
    return [
        {"word": w, "pos": dictionary[w].get("pos"), "gloss": dictionary[w]["gloss"]}
        for w, _count in ordered
    ]


def build_frequency_rows(
    freq: list[tuple[int, str, int]],
    dictionary: dict[str, dict],
    lemmatize,
    max_words: int = 10000,
) -> list[dict]:
    """Merge a HermitDave frequency list with a dictionary (direct then lemma)."""
    agg: dict[str, int] = {}
    for _rank, form, count in freq:
        form = form.strip().lower()
        headword = None
        if form in dictionary:
            headword = form
        else:
            lemma = lemmatize(form)
            if lemma != form and lemma in dictionary:
                headword = lemma
        if headword:
            agg[headword] = agg.get(headword, 0) + count
    ordered = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:max_words]
    return [
        {"word": w, "pos": dictionary[w].get("pos"), "gloss": dictionary[w]["gloss"]}
        for w, _count in ordered
    ]


def build_xhosa_rows(counts, dictionary, max_words=10000):
    """Merge Xhosa bible-corpus counts with a dictionary (Nguni lemmatizer)."""
    return _rows_from_counts(counts, dictionary, XhosaNLP().lemmatize, max_words)


def build_hausa_rows(counts, dictionary, max_words=10000):
    """Merge Hausa corpus counts with a dictionary (apostrophe-normalized)."""
    return _rows_from_counts(counts, dictionary, normalize_hausa, max_words)


# ---------------------------------------------------------------------------
# Example sentences (Tatoeba) — graded by progression
# ---------------------------------------------------------------------------

def parse_tatoeba_sentences(path: Path) -> dict[int, str]:
    """Parse a Tatoeba sentences export (id<TAB>lang<TAB>text) -> {id: text}."""
    opener = bz2.open if path.suffix == ".bz2" else open
    out: dict[int, str] = {}
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 3:
                out[int(parts[0])] = parts[2]
    return out


def parse_tatoeba_links(path: Path) -> list[tuple[int, int]]:
    """Parse a Tatoeba links export (source_id<TAB>target_id)."""
    opener = bz2.open if path.suffix == ".bz2" else open
    out = []
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2:
                out.append((int(parts[0]), int(parts[1])))
    return out


def sentence_difficulty(
    sentence: str,
    rank_by_word: dict[str, int],
    lemmatize,
    unknown_penalty: int = 99999,
) -> int:
    """Score a sentence by its rarest word: max frequency rank over tokens.

    This is the progression metric — a sentence is only as easy as its
    hardest word. Tokens missing from the vocabulary get *unknown_penalty*
    so sentences with out-of-list words sort to the end.
    """
    ranks = []
    for token in _WORD_RE.findall(sentence.lower()):
        rank = rank_by_word.get(token)
        if rank is None:
            rank = rank_by_word.get(lemmatize(token), unknown_penalty)
        ranks.append(rank)
    return max(ranks) if ranks else unknown_penalty


def build_sentence_rows(
    target_sentences: dict[int, str],
    eng_sentences: dict[int, str],
    links: list[tuple[int, int]],
    rank_by_word: dict[str, int],
    lemmatize,
    per_word: int = 3,
    max_difficulty: int = 20000,
) -> list[dict]:
    """Pick up to *per_word* easiest example sentences for each vocab word.

    For every translated Tatoeba sentence, each known (possibly lemmatized)
    token nominates the sentence as an example for that word; the easiest
    sentences win, so early learners see examples made of early vocabulary.
    """
    scored: list[tuple[int, str, str, set[str]]] = []
    for src_id, tgt_id in links:
        sentence = target_sentences.get(src_id)
        translation = eng_sentences.get(tgt_id)
        if not sentence or not translation:
            continue
        difficulty = sentence_difficulty(sentence, rank_by_word, lemmatize)
        if difficulty > max_difficulty:
            continue
        words = set()
        for token in _WORD_RE.findall(sentence.lower()):
            if token in rank_by_word:
                words.add(token)
            else:
                lemma = lemmatize(token)
                if lemma in rank_by_word:
                    words.add(lemma)
        if words:
            scored.append((difficulty, sentence, translation, words))

    scored.sort(key=lambda t: t[0])
    rows: list[dict] = []
    taken: dict[str, int] = {}
    seen_sentences: set[str] = set()
    for difficulty, sentence, translation, words in scored:
        target_words = [w for w in words if taken.get(w, 0) < per_word]
        if not target_words or sentence in seen_sentences:
            continue
        seen_sentences.add(sentence)
        for word in target_words:
            taken[word] = taken.get(word, 0) + 1
            rows.append({
                "word": word,
                "sentence": sentence,
                "translation": translation,
                "difficulty_rank": difficulty,
            })
    return rows


def write_sentences_tsv(rows: list[dict], out_path: Path, locale_column: bool = False) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        header = ["word", "sentence", "translation", "difficulty_rank"]
        if locale_column:
            header.append("translation_locale")
        writer.writerow(header)
        for row in rows:
            out = [row["word"], row["sentence"], row["translation"],
                   row["difficulty_rank"]]
            if locale_column:
                out.append(row.get("translation_locale") or "en")
            writer.writerow(out)
    return len(rows)


async def load_example_sentences(db_url: str, language_code: str, tsv_path: Path) -> int:
    """Load a sentences TSV into example_sentences, linking by vocabulary word."""
    import asyncpg

    conn = await asyncpg.connect(db_url)
    try:
        language_id = await conn.fetchval(
            "SELECT id FROM languages WHERE code = $1", language_code
        )
        if not language_id:
            raise ValueError(f"Language '{language_code}' not found in DB")

        with open(tsv_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f, delimiter="\t"))

        # Chunked UNNEST inserts: sentence TSVs run to six figures of rows,
        # and one round trip per row over a pooled connection is hours.
        chunk_size = 5000
        count = 0
        for start in range(0, len(rows), chunk_size):
            chunk = rows[start:start + chunk_size]
            inserted_rows = await conn.fetch(
                """
                INSERT INTO example_sentences
                    (language_id, vocabulary_id, sentence, translation,
                     difficulty_rank, translation_locale)
                SELECT $1, v.id, u.sentence, u.translation, u.rank, u.locale
                FROM UNNEST($2::text[], $3::text[], $4::text[], $5::int[],
                            $6::text[])
                     AS u(word, sentence, translation, rank, locale)
                JOIN vocabulary v
                     ON v.language_id = $1 AND v.word = u.word
                ON CONFLICT (vocabulary_id, sentence, translation_locale)
                    DO NOTHING
                RETURNING id
                """,
                language_id,
                [r["word"] for r in chunk],
                [r["sentence"] for r in chunk],
                [(r["translation"] or None) for r in chunk],
                [int(r["difficulty_rank"]) for r in chunk],
                [
                    (r.get("translation_locale") or "en").strip() or "en"
                    for r in chunk
                ],
            )
            count += len(inserted_rows)
        return count
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_dictionary(language: str, source: str, cache_dir: Path, wanted=None) -> dict:
    if source == "kaikki":
        path = download(SOURCES[f"{language}_kaikki"], cache_dir / f"{language}_kaikki.jsonl")
        return parse_kaikki_jsonl(path, wanted)
    path = download(SOURCES[f"{language}_freedict"], cache_dir / f"{language}_freedict.tei")
    return parse_freedict_tei(path)


def build_language(language: str, source: str, max_words: int, cache_dir: Path) -> Path:
    """Build data/{language}_frequency.tsv. Returns the output path."""
    if language == "tr":
        freq_path = download(SOURCES["tr_frequency"], cache_dir / "tr_50k.txt")
        freq = parse_hermitdave(freq_path)
        wanted = None
        if source == "kaikki":
            nlp = TurkishNLP()
            wanted = {turkish_lower(w) for _, w, _ in freq}
            wanted |= {nlp.lemmatize(w) for w in wanted}
        dictionary = _build_dictionary("tr", source, cache_dir, wanted)
        rows = build_turkish_rows(freq, dictionary, max_words)
    elif language == "sw":
        corpus_path = download(SOURCES["sw_corpus"], cache_dir / "sw_nt.xml")
        counts = corpus_word_counts(corpus_path)
        wanted = None
        if source == "kaikki":
            nlp = SwahiliNLP()
            wanted = set(counts) | {nlp.lemmatize(w) for w in counts}
        dictionary = _build_dictionary("sw", source, cache_dir, wanted)
        rows = build_swahili_rows(counts, dictionary, max_words)
    elif language == "yo":
        if source != "kaikki":
            raise ValueError(
                "Yoruba has no FreeDict dictionary — run with --source kaikki"
            )
        repo_dir = fetch_yoruba_corpus(cache_dir)
        counts = yoruba_corpus_counts(repo_dir)
        # No 'wanted' filter: tone-stripped fallback matching needs the full
        # headword set, and the Yoruba kaikki extract is small (~10k entries).
        dictionary = _build_dictionary("yo", source, cache_dir, None)
        rows = build_yoruba_rows(counts, dictionary, max_words)
    elif language == "xh":
        if source != "kaikki":
            raise ValueError(
                "Xhosa has no FreeDict dictionary — run with --source kaikki"
            )
        corpus_path = download(SOURCES["xh_corpus"], cache_dir / "xh_bible.xml")
        counts = corpus_word_counts(corpus_path)
        dictionary = _build_dictionary("xh", source, cache_dir, None)
        rows = build_xhosa_rows(counts, dictionary, max_words)
    elif language == "ha":
        if source != "kaikki":
            raise ValueError(
                "Hausa has no FreeDict dictionary — run with --source kaikki"
            )
        corpus_dir = cache_dir / HAUSA_CORPUS_DIRNAME
        counts = plaintext_dir_counts(corpus_dir)
        if not counts:
            raise FileNotFoundError(
                f"No Hausa corpus text found under {corpus_dir}. Drop "
                "commercially-usable plain-text there (Hausa Wikipedia "
                "CC-BY-SA, Leipzig CC-BY, or OPUS news) — see data/README.md."
            )
        dictionary = _build_dictionary("ha", source, cache_dir, None)
        rows = build_hausa_rows(counts, dictionary, max_words)
    elif language == "en":
        # English keeps its bundled frequency list; what it needs from the
        # internet is per-locale word translations (see ENGLISH_SUPPORT_ISO3).
        return build_english_translations(cache_dir)
    elif language in FREQUENCYWORDS_LANGS:
        if source != "kaikki":
            raise ValueError(
                f"{language} has no FreeDict dictionary — run with --source kaikki"
            )
        freq_path = download(
            SOURCES["frequencywords"].format(code=language),
            cache_dir / f"{language}_50k.txt",
        )
        freq = parse_hermitdave(freq_path)
        dictionary = _build_dictionary(language, source, cache_dir, None)
        rows = build_frequency_rows(
            freq, dictionary, FREQ_NLP[language]().lemmatize, max_words
        )
    else:
        raise ValueError(f"Unsupported language: {language}")

    out_path = DATA_DIR / f"{language}_frequency.tsv"
    n = write_frequency_tsv(rows, out_path)
    logger.info("Wrote %d words to %s", n, out_path)
    return out_path


def _read_rank_by_word(freq_tsv: Path) -> dict[str, int]:
    rank_by_word: dict[str, int] = {}
    with open(freq_tsv, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rank_by_word[row["word"]] = int(row["rank"])
    return rank_by_word


def build_english_sentences(cache_dir: Path, per_word: int = 3) -> Path:
    """Build data/en_sentences.tsv: English sentences with per-locale translations.

    English is the reverse of every other language here: the sentence is
    English and the TRANSLATION is in the learner's support language. Each
    Tatoeba {locale}-eng link is simply read backwards, reusing the exact
    files the per-language sentence builds already cache. One row per
    (word, sentence, locale); per_word applies per locale so every support
    language gets its own rotation.
    """
    from backend.services.nlp.english import EnglishNLP

    freq_tsv = DATA_DIR / "en_frequency.tsv"
    if not freq_tsv.exists():
        raise FileNotFoundError(f"Missing {freq_tsv} — bundle the English frequency list first")
    rank_by_word = _read_rank_by_word(freq_tsv)
    lemmatize = EnglishNLP().lemmatize

    eng = parse_tatoeba_sentences(
        download(SOURCES["tatoeba_eng"], cache_dir / "eng_sentences.tsv.bz2")
    )

    all_rows: list[dict] = []
    for locale, iso3 in ENGLISH_SUPPORT_ISO3.items():
        try:
            tgt = download(
                SOURCES["tatoeba_sentences"].format(iso3=iso3),
                cache_dir / f"{iso3}_sentences.tsv.bz2",
            )
            links_path = download(
                SOURCES["tatoeba_links"].format(iso3=iso3),
                cache_dir / f"{iso3}-eng_links.tsv.bz2",
            )
        except Exception as exc:  # 404 / network — skip the locale, keep going
            logger.warning("en sentences: skipping locale %s (%s)", locale, exc)
            continue
        # {iso3}-eng links are (locale_id, eng_id); English-as-target wants
        # (eng_id, locale_id) so the English side is the sentence.
        reversed_links = [(e, s) for (s, e) in parse_tatoeba_links(links_path)]
        rows = build_sentence_rows(
            eng,
            parse_tatoeba_sentences(tgt),
            reversed_links,
            rank_by_word,
            lemmatize,
            per_word=per_word,
        )
        for r in rows:
            r["translation_locale"] = locale
        logger.info("en sentences: %d rows for locale %s", len(rows), locale)
        all_rows.extend(rows)

    out_path = DATA_DIR / "en_sentences.tsv"
    n = write_sentences_tsv(all_rows, out_path, locale_column=True)
    logger.info("Wrote %d example sentences to %s", n, out_path)
    return out_path


def parse_english_kaikki_translations(
    path: Path, wanted: set[str], locales: set[str]
) -> dict[str, dict[str, str]]:
    """word -> {locale: translation} from the English Wiktionary extract.

    Streams the (gzipped) JSONL; collects each entry's translation arrays
    (top-level and per-sense). First translation per (word, locale) wins —
    senses are ordered by prominence in Wiktionary.
    """
    import gzip

    out: dict[str, dict[str, str]] = {}
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            word = (entry.get("word") or "").strip().lower()
            if word not in wanted:
                continue
            translations = list(entry.get("translations") or [])
            for sense in entry.get("senses") or []:
                translations.extend(sense.get("translations") or [])
            if not translations:
                continue
            slot = out.setdefault(word, {})
            for t in translations:
                code = t.get("code") or t.get("lang_code")
                tw = (t.get("word") or "").strip()
                if code in locales and tw and code not in slot:
                    slot[code] = tw
    return out


def build_english_translations(cache_dir: Path) -> Path:
    """Build data/en_translations.tsv (word/locale/translation) from kaikki."""
    freq_tsv = DATA_DIR / "en_frequency.tsv"
    if not freq_tsv.exists():
        raise FileNotFoundError(f"Missing {freq_tsv}")
    wanted = set(_read_rank_by_word(freq_tsv))

    path = download(SOURCES["en_kaikki_gz"], cache_dir / "en_kaikki.jsonl.gz")
    by_word = parse_english_kaikki_translations(
        path, wanted, set(ENGLISH_SUPPORT_ISO3)
    )

    out_path = DATA_DIR / "en_translations.tsv"
    n = 0
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["word", "locale", "translation"])
        for word in sorted(by_word):
            for locale in sorted(by_word[word]):
                writer.writerow([word, locale, by_word[word][locale]])
                n += 1
    logger.info(
        "Wrote %d translations (%d words) to %s", n, len(by_word), out_path
    )
    return out_path


def build_sentences(language: str, cache_dir: Path, per_word: int = 3) -> Path:
    """Build data/{language}_sentences.tsv from Tatoeba (needs tatoeba.org access)."""
    if language == "en":
        return build_english_sentences(cache_dir, per_word=per_word)
    if language not in TATOEBA_ISO3:
        raise ValueError(
            f"No Tatoeba sentence pipeline for '{language}' yet "
            f"(supported: {', '.join(sorted(TATOEBA_ISO3))})"
        )
    iso3 = TATOEBA_ISO3[language]
    tgt = download(
        SOURCES["tatoeba_sentences"].format(iso3=iso3),
        cache_dir / f"{iso3}_sentences.tsv.bz2",
    )
    links = download(
        SOURCES["tatoeba_links"].format(iso3=iso3),
        cache_dir / f"{iso3}-eng_links.tsv.bz2",
    )
    eng = download(SOURCES["tatoeba_eng"], cache_dir / "eng_sentences.tsv.bz2")

    freq_tsv = DATA_DIR / f"{language}_frequency.tsv"
    if not freq_tsv.exists():
        raise FileNotFoundError(f"Run the frequency build first: missing {freq_tsv}")
    rank_by_word: dict[str, int] = {}
    with open(freq_tsv, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rank_by_word[row["word"]] = int(row["rank"])

    nlp_by_lang = {
        "tr": TurkishNLP, "sw": SwahiliNLP, "yo": YorubaNLP,
        "xh": XhosaNLP, "ha": HausaNLP, "ru": RussianNLP,
        **FREQ_NLP,
    }
    lemmatize = nlp_by_lang[language]().lemmatize
    rows = build_sentence_rows(
        parse_tatoeba_sentences(tgt),
        parse_tatoeba_sentences(eng),
        parse_tatoeba_links(links),
        rank_by_word,
        lemmatize,
        per_word=per_word,
    )
    out_path = DATA_DIR / f"{language}_sentences.tsv"
    n = write_sentences_tsv(rows, out_path)
    logger.info("Wrote %d example sentences to %s", n, out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build seed data from open datasets")
    parser.add_argument(
        "--language", "-l",
        choices=["tr", "sw", "yo", "ha", "xh", "es", "it", "fr", "de", "ca",
                 "ro", "el", "ar", "ru", "en"],
        required=True
    )
    parser.add_argument(
        "--source", choices=["freedict", "kaikki"], default="freedict",
        help="Translation source: freedict (small, instant) or kaikki (large, best coverage)",
    )
    parser.add_argument("--max-words", type=int, default=10000)
    parser.add_argument(
        "--sentences", action="store_true",
        help="Also build graded example sentences from Tatoeba",
    )
    parser.add_argument("--cache-dir", type=Path, default=DATA_DIR / "raw")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    freq_tsv = DATA_DIR / f"{args.language}_frequency.tsv"
    if args.sentences and freq_tsv.exists():
        # A sentences run must never rebuild — and possibly overwrite with a
        # lesser source — a frequency file that already exists. Delete the
        # TSV (or run without --sentences) to force a rebuild.
        logger.info("Keeping existing %s; building sentences only", freq_tsv)
    else:
        build_language(args.language, args.source, args.max_words, args.cache_dir)
    if args.sentences:
        build_sentences(args.language, args.cache_dir)


if __name__ == "__main__":
    main()
