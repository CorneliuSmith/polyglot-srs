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
from backend.services.nlp.hindi import HindiNLP
from backend.services.nlp.korean import KoreanNLP
from backend.services.nlp.latin_base import (
    CatalanNLP,
    DutchNLP,
    FrenchNLP,
    GermanNLP,
    GreekNLP,
    ItalianNLP,
    MaoriNLP,
    PortugueseNLP,
    RomanianNLP,
    SpanishNLP,
    fold_diacritics,
)
from backend.services.nlp.russian import RussianNLP
from backend.services.nlp.swahili import SwahiliNLP
from backend.services.nlp.thai import ThaiNLP
from backend.services.nlp.turkish import TurkishNLP, turkish_lower
from backend.services.nlp.xhosa import XhosaNLP
from backend.services.nlp.yoruba import YorubaNLP, strip_tones
from backend.services.seeder.base import DATA_DIR

# Languages sourced generically from a HermitDave frequency list
# (OpenSubtitles) + a kaikki Wiktionary dictionary. The path is
# script-agnostic — ro/el/ar ride the same rails as the Latin five; it just
# needs a frequency list, a kaikki extract, and a lemmatizer.
FREQUENCYWORDS_LANGS = {"es", "it", "fr", "de", "ca", "ro", "el", "ar", "ru", "pt", "hi", "nl", "th", "ko"}
LATIN_NLP = {
    "es": SpanishNLP, "it": ItalianNLP, "fr": FrenchNLP,
    "de": GermanNLP, "ca": CatalanNLP, "mi": MaoriNLP,
    "pt": PortugueseNLP,
}
# Lemmatizers for the generic path (superset of LATIN_NLP). Russian's
# pymorphy3 normal_form folds OpenSubtitles inflections onto kaikki
# headwords — the OpenRussian download host no longer resolves, so Russian
# rides these rails too.
FREQ_NLP = {
    **LATIN_NLP,
    "ro": RomanianNLP, "el": GreekNLP, "ar": ArabicNLP, "ru": RussianNLP,
    "hi": HindiNLP, "nl": DutchNLP, "th": ThaiNLP, "ko": KoreanNLP,
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
    "mi_kaikki": "https://kaikki.org/dictionary/M%C4%81ori/kaikki.org-dictionary-M%C4%81ori.jsonl",
    "ro_kaikki": "https://kaikki.org/dictionary/Romanian/kaikki.org-dictionary-Romanian.jsonl",
    "el_kaikki": "https://kaikki.org/dictionary/Greek/kaikki.org-dictionary-Greek.jsonl",
    "ar_kaikki": "https://kaikki.org/dictionary/Arabic/kaikki.org-dictionary-Arabic.jsonl",
    "ru_kaikki": "https://kaikki.org/dictionary/Russian/kaikki.org-dictionary-Russian.jsonl",
    "pt_kaikki": "https://kaikki.org/dictionary/Portuguese/kaikki.org-dictionary-Portuguese.jsonl",
    "hi_kaikki": "https://kaikki.org/dictionary/Hindi/kaikki.org-dictionary-Hindi.jsonl",
    "nl_kaikki": "https://kaikki.org/dictionary/Dutch/kaikki.org-dictionary-Dutch.jsonl",
    "th_kaikki": "https://kaikki.org/dictionary/Thai/kaikki.org-dictionary-Thai.jsonl",
    "ko_kaikki": "https://kaikki.org/dictionary/Korean/kaikki.org-dictionary-Korean.jsonl",
    # HermitDave FrequencyWords (OpenSubtitles 2018), per ISO code.
    "frequencywords": (
        "https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
        "master/content/2018/{code}/{code}_50k.txt"
    ),
    "yo_corpus_repo": "https://github.com/Niger-Volta-LTI/yoruba-text.git",
    # Xhosa: Leipzig Corpora community corpus (CC-BY), 23,993 sentences of
    # real web register. This replaced the bible bootstrap on 24 Aug 2026 —
    # the comment below had recommended exactly this swap, and the bible list
    # is what made rank 2 uThixo "God" and rank 3 unyana "the Son of God in
    # Christian texts" while okanye "or", kwaye "and" and kodwa "but" had no
    # cards at all. Verified reachable 24 Aug 2026.
    "xh_leipzig": (
        "https://downloads.wortschatz-leipzig.de/corpora/"
        "xho_community_2017.tar.gz"
    ),
    # Kept: the bible corpus is still the only source for Māori, and Xhosa's
    # existing ranks were derived from it, so it stays reachable for
    # comparison and for any rebuild that wants both.
    "xh_corpus": (
        "https://raw.githubusercontent.com/christos-c/bible-corpus/"
        "master/bibles/Xhosa.xml"
    ),
    # Māori: same public-domain bible-corpus bootstrap as Xhosa (no
    # OpenSubtitles list exists; the Māori Broadcast Corpus is not
    # redistributable). Kaikki supplies the glosses.
    "mi_corpus": (
        "https://raw.githubusercontent.com/christos-c/bible-corpus/"
        "master/bibles/Maori.xml"
    ),
    # Hausa: Leipzig Corpora community corpus (CC-BY) — sentences file
    # doubles as the frequency corpus. Verified reachable 2026-07-12.
    "ha_leipzig": (
        "https://downloads.wortschatz-leipzig.de/corpora/"
        "hau_community_2017.tar.gz"
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
    # Hindi: HermitDave 2018 publishes only the FULL list under hi/ (no
    # hi_50k.txt); it is Devanagari OpenSubtitles counts. parse_hermitdave
    # ranks it, and build_frequency_rows caps at max_words.
    "hi_frequency": (
        "https://raw.githubusercontent.com/hermitdave/FrequencyWords/"
        "master/content/2018/hi/hi_full.txt"
    ),
}

# Support locales for English-as-target study ("I'm learning English from
# Spanish"): locale code -> Tatoeba ISO-639-3, for building English example
# sentences whose translations are in the LEARNER's language. These reuse
# the same cached Tatoeba files the per-language sentence builds download.
ENGLISH_SUPPORT_ISO3 = {
    "es": "spa", "fr": "fra", "de": "deu", "it": "ita", "ru": "rus",
    "tr": "tur", "ar": "ara", "el": "ell", "ro": "ron", "ca": "cat",
    "sw": "swh", "pt": "por", "hi": "hin",
}

TATOEBA_ISO3 = {
    "tr": "tur", "sw": "swh", "yo": "yor", "ha": "hau", "xh": "xho",
    # European tier + ru/ar (well-covered on Tatoeba)
    "es": "spa", "fr": "fra", "de": "deu", "it": "ita", "ca": "cat",
    "ro": "ron", "el": "ell", "ru": "rus", "ar": "ara", "pt": "por",
    "hi": "hin", "jam": "jam", "mi": "mri", "nl": "nld", "th": "tha",
    "ko": "kor",
    # These five were missing here, and the omission cost each course its
    # whole sentence bank: la, id, tl, he and fa had ZERO examples and were
    # queued for authoring from nothing, while Tatoeba has had an export for
    # every one of them the entire time. Checked 26 Aug 2026: all five return
    # HTTP 200 for both the sentence and the eng-links file.
    #
    # `la` needs one extra step the others do not: Tatoeba's Latin is largely
    # UNMACRONISED, and la.md's all-or-nothing macron policy does not allow
    # that to ship — harvest, then macronise.
    "la": "lat", "id": "ind", "tl": "tgl", "he": "heb", "fa": "pes",
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


# How much a part of speech looks like a WORD rather than a glyph or a place.
# kaikki emits one entry per (word, pos, etymology) and they arrive in no
# useful order, so taking the first entry that happens to carry a gloss is how
# French rank 15 `ne` — the negator — ended up defined as a Swiss canton, and
# rank 36 `y` — the pronoun "there" — as a letter of the alphabet. Both had the
# right sense sitting in a later entry that was never read. Lower sorts first.
_POS_RANK = {
    # Every genuine word class sits at ONE rank on purpose. Ordering them
    # against each other looks reasonable and is not: ranking adverbs above
    # numerals rewrote Turkish rank 1 `bir` from "one" to "only, solely,
    # merely" and rank 12 `var` from "there is" to "every, all", because both
    # carry a secondary adverbial sense. Within real words, arrival order —
    # which is roughly Wiktionary's own sense order — already decides well.
    "pron": 0, "pronoun": 0, "det": 0, "article": 0, "particle": 0,
    "conj": 0, "prep": 0, "postp": 0, "adv": 0, "verb": 0,
    "noun": 0, "adj": 0, "num": 0, "intj": 0, "classifier": 0, "counter": 0,
    "phrase": 1, "proverb": 2,
    # Bound morphemes: real, but a poor definition for a standalone headword.
    "prefix": 4, "suffix": 4, "infix": 4, "interfix": 4,
    # Not a word sense at all. This distinction is the whole point of ranking.
    "name": 8, "character": 9, "letter": 9, "symbol": 9, "punct": 9,
}
_POS_RANK_DEFAULT = 3

# Senses that describe a glyph, a region code or a sound rather than a meaning.
# Wider than the substring checks this replaces, which missed "a letter IN the
# French alphabet" and "The sound expressed by the letter A".
_NOT_A_MEANING = re.compile(
    r"letter (?:of|in) the|name of the .{0,30}letter|\b\w+(?:th|st|nd|rd) letter\b"
    r"|sound expressed by the letter|the sound of the letter|\bISO\s*\d"
    r"|chemical symbol (?:of|for)",
    re.IGNORECASE,
)

# A grammatical annotation standing where a definition should be. Russian `в`
# — rank 4 — ships as "[with prepositional]" because kaikki lists the case
# frames as senses in their own right and the meaning ("in, at, on") is the
# third one. Rejecting the frame lets the meaning win.
_BRACKET_ONLY = re.compile(r"^\s*\[[^\]]*\]\s*$")

# A sense header that only points elsewhere: "inflection of होना:", "plural of
# X:". Unlike "mother:", nothing survives stripping the colon.
_EMPTY_PROMISE = re.compile(
    r"\s*\((?:in the following senses?|see below|of the following)\)\s*$",
    re.IGNORECASE,
)

_POINTER_HEADER = re.compile(
    r"^(?:inflection|plural|feminine|masculine|singular|genitive|dative|"
    r"accusative|vocative|nominative|oblique|comparative|superlative|"
    r"alternative|archaic|obsolete|past|present|future)\b.*\bof\b"
    r"|^(?:first|second|third)-person\b",
    re.IGNORECASE,
)

# [[Appendix:Swahili_noun_classes#N class|n class_((IX))]] -> n class (IX)
_WIKI_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]|]*)\]\]")

# A cross-reference sense that carries the meaning anyway:
#   alternative form of àbí (“or”)   ->  or
# Dropping these outright costs real vocabulary — Yoruba `tabi` ("or") at rank
# 44, `titun` ("new"), `joko` ("to sit"), Turkish `haydi` ("come on") are all
# ordinary words whose only Wiktionary sense points at a standard spelling. The
# meaning is sitting in the quotation marks; take it and keep the word.
_ALT_OF_MEANING = re.compile(
    r"^(?:alternative|archaic|obsolete|dated|nonstandard|informal)\b[^(]*"
    r"[(\[]?\s*[“\"']([^”\"']{1,80})[”\"']",
    re.IGNORECASE,
)

# The same cross-reference when it states no meaning, so only the target can
# supply one: "alternative form of hayde" -> hayde.
_POINTER_TARGET = re.compile(
    r"^(?:alternative|archaic|obsolete|dated|nonstandard|informal)\b[^,;]*?"
    r"\bof\s+([^\s,;(]+)",
    re.IGNORECASE,
)


def _clean_gloss(gloss: str) -> str | None:
    """A gloss a learner can read, or None if this sense cannot supply one.

    Three things happen here that the length check alone could not do:

    Wiki markup is rejected outright. Swahili rank 2 currently ships as
    "[[Appendix:Swahili_noun_classes#N class|n class_((IX))]] i" — 57 characters,
    so every length rule passes it, and it is unreadable.

    A gloss promising senses it does not carry is rejected. kaikki writes
    "from, away from, of, with (in the following senses):" and puts the senses
    in a nested structure; keeping the preamble gives the learner a colon and
    nothing after it.

    A long gloss is trimmed rather than discarded. The correct French `ne`
    sense is "not (used alone to negate a verb, now chiefly with only a few
    particular verbs; see usage notes)" — 95 characters, so the old rule threw
    it away and left the canton code to win. Cutting the usage note leaves
    "not", which is the definition.
    """
    gloss = (gloss or "").strip()
    if not gloss:
        return None
    # Unwrap wiki links rather than dropping the sense: for Swahili's concords
    # the markup IS the only sense kaikki carries, so rejecting it would leave
    # ranks 2, 14, 20 and 49 with no definition at all — worse than a weak one.
    # What survives is still thin and lands on the authoring list.
    if "[[" in gloss:
        gloss = _WIKI_LINK.sub(r"\1", gloss).replace("_", " ").strip()
    gloss = gloss.replace("((", "(").replace("))", ")")
    if not gloss or "[[" in gloss or "]]" in gloss:
        return None
    if _BRACKET_ONLY.match(gloss):
        return None
    if _NOT_A_MEANING.search(gloss):
        return None
    if gloss.rstrip().endswith(":"):
        # kaikki writes a sense header with its sub-senses nested underneath, so
        # the text arrives as "mother:" or "inflection of होना:". Rejecting both
        # cost the primary meaning of ordinary words — Thai rank 28 แม่ lost
        # "mother", rank 15 ดี lost "good", and สวัสดี ("hello") was left as
        # "welfare, well-being". Keep the header when it is itself a meaning and
        # drop it only when it is a pointer with nothing of its own to say.
        head = gloss.rstrip().rstrip(":").strip()
        # "…, with (in the following senses)" promises what it does not carry.
        head = _EMPTY_PROMISE.sub("", head).strip().rstrip(",;")
        if not head or _POINTER_HEADER.match(head):
            return None
        gloss = head
    if len(gloss) > 90:
        for cut in (" (", "; ", ", "):
            head = gloss.split(cut)[0].strip()
            if 0 < len(head) <= 90:
                return _balance(head)
        return None
    return _balance(gloss)


def _balance(gloss: str) -> str | None:
    """Drop a parenthetical the sense list left half-open.

    kaikki nests parentheses, so cutting a long gloss at the first " (" can
    leave an unclosed one behind: Russian `за` trimmed to "to; during (close to
    в течение (v tečenije". Cutting back to the last balanced point is better
    than shipping a bracket the learner has to mentally close.
    """
    while gloss.count("(") > gloss.count(")"):
        gloss = gloss[: gloss.rfind("(")].strip().rstrip(",;—-").strip()
        if not gloss:
            return None
    return gloss or None


def parse_kaikki_jsonl(
    path: Path, wanted: set[str] | None = None, *, follow_pointers: bool = True
) -> dict[str, dict]:
    """Stream a kaikki.org Wiktionary extract -> {word: {pos, gloss, plural}}.

    Every entry for a word is read and the best-ranked one wins, rather than the
    first that happens to parse. Pass *wanted* to filter to a known word set and
    keep memory flat on the large dumps.

    A word left holding only a cross-reference ("alternative form of hayde") is
    then resolved by following it, because the pointer is usually worse than
    useless: measured across the nineteen rebuilt lists, 521 of them named a
    target that is not in the same course at all, so the learner is sent to look
    up a word they do not have. Most are not even variants — Arabic rank 65
    `انا` points at `أَنَا`, differing only in vocalization, and Romanian
    `dumnezeu` at `Dumnezeu`, differing only in case.
    """
    # word -> (pos_rank, arrival_order, pos, gloss)
    best: dict[str, tuple[int, int, str | None, str]] = {}
    order = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            order += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            word = (obj.get("word") or "").strip().lower()
            if not word:
                continue
            if wanted is not None and word not in wanted:
                continue
            # A definition a HUMAN can read. Three tiers of sense:
            #  - junk, never shown: case/spelling cross-references
            #    ("alternative letter-case form of я"), letter-name senses
            #    ("The name of the Cyrillic script letter Я"), misspellings
            #  - fallback: inflection senses — "third-person singular
            #    present of είμαι" IS the right gloss for a surface form
            #    the lemmatizer didn't fold
            #  - content: real meanings, preferred whenever one exists.
            # The first entry with a usable definition wins, not merely the
            # first entry (я the pronoun beats я the letter).
            content: list[str] = []
            fallback: list[str] = []
            last_resort: list[str] = []
            for sense in obj.get("senses") or []:
                tags = set(sense.get("tags") or [])
                if "alt_of" in sense or tags & {"alt-of", "obsolete",
                                                "misspelling"}:
                    # Rescue the meaning if the cross-reference states it, so a
                    # real word is not lost to a spelling pointer. When it does
                    # not state one, keep the pointer as a last resort rather
                    # than dropping the word: Turkish `hadi` and `haydi` ("come
                    # on") are ranks 53 and 199 and have no other sense at all.
                    for g in sense.get("glosses") or []:
                        text = (g or "").strip()
                        found = _ALT_OF_MEANING.match(text)
                        recovered = _clean_gloss(found.group(1)) if found else None
                        if recovered:
                            fallback.append(recovered)
                        elif text:
                            last_resort.append(text)
                    continue
                is_form = "form_of" in sense or "form-of" in tags
                for g in sense.get("glosses") or []:
                    text = (g or "").strip()
                    low = text.lower()
                    if low.startswith("the name of the") or "script letter" in low:
                        continue
                    if low.startswith(("alternative ", "romanization of",
                                       "misspelling", "obsolete ", "archaic ")):
                        # Same rescue as the tagged cross-references above, for
                        # senses that only say so in prose. Turkish `hadi` and
                        # `haydi` ("come on") sit at ranks 53 and 199 with no
                        # other sense at all, so skipping these outright drops
                        # ordinary words off the list. The pointer itself is a
                        # weak definition, so it is kept only as a last resort.
                        found = _ALT_OF_MEANING.match(text)
                        recovered = _clean_gloss(found.group(1)) if found else None
                        if recovered:
                            fallback.append(recovered)
                        else:
                            last_resort.append(text)
                        continue
                    cleaned = _clean_gloss(g)
                    if cleaned:
                        (fallback if is_form else content).append(cleaned)
            glosses = list(dict.fromkeys(content or fallback or last_resort))
            if not glosses:
                continue
            # one clear sense; a second only when the first is terse
            gloss = glosses[0]
            if len(gloss) < 15 and len(glosses) > 1:
                gloss = "; ".join(glosses[:2])

            pos = obj.get("pos")
            rank = _POS_RANK.get((pos or "").strip().lower(), _POS_RANK_DEFAULT)
            # A bare spelling pointer ("alternative form of hayde", no meaning
            # given) is a last resort and sinks below everything real.
            #
            # A form-of sense does NOT sink. Penalising those was tried and
            # reverted: for a frequency list built from surface forms, the
            # inflection IS usually the right answer, and demoting it hands the
            # card to whatever rare homograph happens to be a content sense.
            # Measured on a full rebuild, that turned German `hast` (rank 49,
            # "you have") into "haste", `habe` into "belongings", Italian `ha`
            # (rank 18, "has") into "ah! (ironic)" and `ti` into the musical
            # note B. Wiktionary's own sense order is the better guide here.
            if not content and not fallback:
                rank += 5
            candidate = (rank, order, pos, gloss)
            if word not in best or candidate < best[word]:
                best[word] = candidate

    if follow_pointers:
        _follow_pointers(path, best)

    return {
        word: {"pos": pos, "gloss": gloss, "plural": None}
        for word, (_rank, _order, pos, gloss) in best.items()
    }


def _follow_pointers(path: Path, best: dict[str, tuple[int, int, str | None, str]]) -> None:
    """Replace a bare cross-reference gloss with the meaning it points at.

    One extra pass, and only for the targets actually named — the words needing
    this are a fraction of a percent of any list. A target that itself resolves
    to a pointer is left alone rather than chased: two hops is already a sign
    the entry is a spelling thicket, and a cycle would not terminate.
    """
    targets: dict[str, list[str]] = {}
    for word, (_rank, _order, _pos, gloss) in best.items():
        found = _POINTER_TARGET.match(gloss)
        if not found:
            continue
        target = found.group(1).strip(".,;:\"'“”()[]").lower()
        if target and target != word:
            targets.setdefault(target, []).append(word)
    if not targets:
        return

    resolved = parse_kaikki_jsonl(path, wanted=set(targets), follow_pointers=False)
    for target, words in targets.items():
        entry = resolved.get(target)
        if not entry:
            continue
        gloss = entry["gloss"]
        if _POINTER_TARGET.match(gloss):
            continue
        for word in words:
            rank, order, pos, _old = best[word]
            best[word] = (rank, order, pos, gloss)


# Word tokens INCLUDING combining marks: Python's \w excludes Unicode Mn/Mc
# marks, so the plain [^\W\d_]+ pattern shredded every Devanagari word with
# a matra (नहीं tokenized as नह) — the reason Hindi sentence matching found
# almost nothing. The added ranges cover Devanagari signs/matras, Arabic
# harakat, and general combining diacriticals; digit-bearing tokens are
# filtered after the fact to preserve the old \d exclusion.
_WORD_CHARS = (
    r"[^\W\d_]"
    r"|[ऀ-ःऺ-ॏ॑-ॗॢ-ॣঁ-ঃ]"
    r"|[ً-ْٰ]"
    r"|[̀-ͯ]"
)
_WORD_RE_RAW = re.compile(f"(?:{_WORD_CHARS})+", re.UNICODE)


class _WordRe:
    """Drop-in for the old regex: findall() with mark-aware tokens."""

    @staticmethod
    def findall(text: str) -> list[str]:
        # Tokens made ONLY of combining marks (stray matras) are noise.
        return [
            t for t in _WORD_RE_RAW.findall(text)
            if re.search(r"[^\W\d_]", t, re.UNICODE)
        ]


_WORD_RE = _WordRe()


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
    tolerated_unknown_rank: int = 19999,
    tokenize=None,
) -> int:
    """Score a sentence by its rarest word: max frequency rank over tokens.

    This is the progression metric — a sentence is only as easy as its
    hardest word. Two forgiveness rules (beta fix — the old all-or-nothing
    drop left Hindi with 427 sentences from a corpus of thousands and
    Catalan at 17% coverage):

      - single-letter tokens are ignored: they are elision clitics (l'home,
        d'una) and initials, not vocabulary;
      - exactly ONE unknown multi-letter token scores *tolerated_unknown_rank*
        (hard-but-usable) instead of poisoning the sentence. Easiest-first
        selection means such sentences only surface for words that would
        otherwise have no example at all. Two or more unknowns still get
        *unknown_penalty* — that's a sentence the learner can't read.
    """
    ranks = []
    unknowns = 0
    tokens = tokenize(sentence.lower()) if tokenize else _WORD_RE.findall(sentence.lower())
    for token in tokens:
        if len(token) == 1:
            continue
        rank = rank_by_word.get(token)
        if rank is None:
            rank = rank_by_word.get(lemmatize(token))
        if rank is None:
            unknowns += 1
            continue
        ranks.append(rank)
    if unknowns >= 2 or (unknowns == 1 and not ranks):
        return unknown_penalty
    if unknowns == 1:
        ranks.append(tolerated_unknown_rank)
    return max(ranks) if ranks else unknown_penalty


def build_sentence_rows(
    target_sentences: dict[int, str],
    eng_sentences: dict[int, str],
    links: list[tuple[int, int]],
    rank_by_word: dict[str, int],
    lemmatize,
    per_word: int = 3,
    max_difficulty: int = 20000,
    tokenize=None,
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
        difficulty = sentence_difficulty(
            sentence, rank_by_word, lemmatize, tokenize=tokenize
        )
        if difficulty > max_difficulty:
            continue
        words = set()
        tokens = tokenize(sentence.lower()) if tokenize else _WORD_RE.findall(sentence.lower())
        for token in tokens:
            if token in rank_by_word:
                words.add(token)
            else:
                lemma = lemmatize(token)
                # A lemma match may only bridge real morphology, never bare
                # diacritics: for accent-folding languages lemmatize("él")
                # is "el", which used to hand él-sentences to the article
                # card (and año-sentences to "ano"). If folding alone
                # explains the match, the sentence does NOT contain this
                # word — skip it.
                if lemma in rank_by_word and fold_diacritics(token) != lemma:
                    words.add(lemma)
        if words:
            scored.append((difficulty, sentence, translation, words))

    return _select_example_rows(scored, per_word)


def _select_example_rows(
    scored: list[tuple[int, str, str, set[str]]], per_word: int
) -> list[dict]:
    """Easiest-first selection: each word collects up to *per_word* examples."""
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
                     difficulty_rank, translation_locale,
                     transliteration, gloss)
                SELECT $1, v.id, u.sentence, u.translation, u.rank, u.locale,
                       u.translit, u.gloss
                FROM UNNEST($2::text[], $3::text[], $4::text[], $5::int[],
                            $6::text[], $7::text[], $8::text[])
                     AS u(word, sentence, translation, rank, locale,
                          translit, gloss)
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
                # These two were silently dropped until 25 Aug 2026. The TSVs
                # have carried a `transliteration` column for `ko` since it was
                # built, and production read 18% — because nothing on this path
                # ever wrote it. The interlinear `gloss` was 0% in production
                # for EVERY language for the same reason. Authoring either
                # layer was invisible to a learner until this line existed.
                [((r.get("transliteration") or "").strip() or None) for r in chunk],
                [((r.get("gloss") or "").strip() or None) for r in chunk],
            )
            count += len(inserted_rows)
        return count
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

# Both live in gloss_overrides so the English seeder can reach them without
# pulling this module's heavier imports in with them.
from .gloss_overrides import GLOSS_OVERRIDES_PATH, load_gloss_overrides  # noqa: E402,F401

VOCAB_EXCLUSIONS_PATH = DATA_DIR / "vocab_exclusions.tsv"


def apply_vocab_exclusions(language: str, rows: list[dict]) -> list[dict]:
    """Drop rows the corpus keeps generating that must never become cards.

    A high-typo-frequency misspelling (citta, voila) inherits a real rank from
    the word it misspells, and kaikki then supplies whatever obscure entry
    owns that bare spelling — Tuscan "girl", "slowworm", a passé simple nobody
    meets. Deleting the row from the committed TSV is not a fix: the next
    regeneration re-emits it, exactly the way a DB-only fix is undone by the
    next re-seed. This file is the durable form of that deletion.
    """
    if not VOCAB_EXCLUSIONS_PATH.exists():
        return rows
    excluded: set[str] = set()
    with open(VOCAB_EXCLUSIONS_PATH, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if (row.get("language") or "").strip() == language:
                word = (row.get("word") or "").strip()
                if word:
                    excluded.add(word.casefold())
    if not excluded:
        return rows
    kept = [row for row in rows if (row.get("word") or "").casefold() not in excluded]
    if len(kept) < len(rows):
        logger.info("Excluded %d vocabulary rows for %s", len(rows) - len(kept), language)
    return kept


def apply_gloss_overrides(language: str, rows: list[dict]) -> list[dict]:
    """Hand-authored definitions for words no sense-picking rule gets right.

    Ranking parts of speech against each other cannot settle a word that is
    genuinely two words. Portuguese `a` is both the feminine definite article
    (rank 2, overwhelmingly what a learner meets) and an object pronoun; French
    `la` and Spanish `los` are the same shape. Whichever entry Wiktionary lists
    first wins, and for these it is the pronoun.

    Preferring the PREVIOUS list's part of speech was the obvious alternative
    and is unsafe: Turkish `ve` ("and") was filed as a `character` under the old
    parser, so trusting that would restore the very defect this work removes.

    So the top of the list gets human judgment, kept in one reviewable file
    beside the data it corrects — the same shape as the existing
    en_translation_overrides.tsv. Only words already present are corrected; an
    override never invents an entry, because rank comes from the corpus.
    """
    # Module global, so a test that patches GLOSS_OVERRIDES_PATH here is heard.
    import backend.services.seeder.source_data as _mod

    overrides = load_gloss_overrides(language, _mod.GLOSS_OVERRIDES_PATH)
    if not overrides:
        return rows
    applied = 0
    for row in rows:
        hit = overrides.get(row["word"])
        if not hit:
            continue
        gloss = (hit.get("en") or "").strip()
        pos = (hit.get("pos") or "").strip()
        if gloss:
            row["gloss"] = gloss
        if pos:
            row["pos"] = pos
        applied += 1
    logger.info("Applied %d gloss override(s) for %s", applied, language)
    return rows


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
    elif language == "mi":
        if source != "kaikki":
            raise ValueError(
                "Māori has no FreeDict dictionary — run with --source kaikki"
            )
        corpus_path = download(SOURCES["mi_corpus"], cache_dir / "mi_bible.xml")
        counts = corpus_word_counts(corpus_path)
        dictionary = _build_dictionary("mi", source, cache_dir, None)
        rows = _rows_from_counts(
            counts, dictionary, MaoriNLP().lemmatize, max_words
        )
    elif language == "ha":
        if source != "kaikki":
            raise ValueError(
                "Hausa has no FreeDict dictionary — run with --source kaikki"
            )
        corpus_dir = cache_dir / HAUSA_CORPUS_DIRNAME
        counts = plaintext_dir_counts(corpus_dir)
        if not counts:
            # Bootstrap from the Leipzig community corpus (CC-BY): the
            # sentences file (id<TAB>sentence) becomes plain corpus text.
            import tarfile
            tar_path = download(SOURCES["ha_leipzig"], cache_dir / "ha_leipzig.tar.gz")
            corpus_dir.mkdir(parents=True, exist_ok=True)
            with tarfile.open(tar_path, "r:gz") as tf:
                for member in tf.getmembers():
                    if member.name.endswith("-sentences.txt"):
                        raw = tf.extractfile(member).read().decode("utf-8")
                        lines = [
                            line.split("\t", 1)[1]
                            for line in raw.splitlines()
                            if "\t" in line
                        ]
                        (corpus_dir / "leipzig_community_2017.txt").write_text(
                            "\n".join(lines), encoding="utf-8"
                        )
            counts = plaintext_dir_counts(corpus_dir)
        if not counts:
            raise FileNotFoundError(
                f"No Hausa corpus text found under {corpus_dir}."
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
        # Hindi's HermitDave list lives at a different path (hi_full.txt);
        # everything else follows the {code}_50k.txt template.
        freq_url = (
            SOURCES["hi_frequency"] if language == "hi"
            else SOURCES["frequencywords"].format(code=language)
        )
        freq_path = download(freq_url, cache_dir / f"{language}_50k.txt")
        freq = parse_hermitdave(freq_path)
        dictionary = _build_dictionary(language, source, cache_dir, None)
        rows = build_frequency_rows(
            freq, dictionary, FREQ_NLP[language]().lemmatize, max_words
        )
    else:
        raise ValueError(f"Unsupported language: {language}")

    rows = apply_vocab_exclusions(language, rows)
    rows = apply_gloss_overrides(language, rows)
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

    # spaCy lemmatization runs a full pipeline per CALL — uncached, the
    # twelve-locale build made tens of millions of one-word spaCy runs and
    # took 8+ hours. The token vocabulary is only a few hundred thousand
    # strings, so a dict cache turns it into minutes.
    _raw_lemmatize = EnglishNLP().lemmatize
    _lemma_cache: dict[str, str] = {}

    def lemmatize(token: str) -> str:
        lemma = _lemma_cache.get(token)
        if lemma is None:
            lemma = _raw_lemmatize(token)
            _lemma_cache[token] = lemma
        return lemma

    eng = parse_tatoeba_sentences(
        download(SOURCES["tatoeba_eng"], cache_dir / "eng_sentences.tsv.bz2")
    )

    # The SAME English sentence appears in many locales' links — score it
    # once, not twelve times. None = too hard / no known words.
    score_cache: dict[int, tuple[int, set[str]] | None] = {}

    def score(eng_id: int, sentence: str) -> tuple[int, set[str]] | None:
        if eng_id in score_cache:
            return score_cache[eng_id]
        difficulty = sentence_difficulty(sentence, rank_by_word, lemmatize)
        result = None
        if difficulty <= 20000:
            words = set()
            for token in _WORD_RE.findall(sentence.lower()):
                if token in rank_by_word:
                    words.add(token)
                else:
                    lemma = lemmatize(token)
                    if lemma in rank_by_word:
                        words.add(lemma)
            if words:
                result = (difficulty, words)
        score_cache[eng_id] = result
        return result

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
        translations = parse_tatoeba_sentences(tgt)
        scored: list[tuple[int, str, str, set[str]]] = []
        # {iso3}-eng links are (locale_id, eng_id); English-as-target wants
        # the English side as the sentence and the locale side as its
        # translation.
        for loc_id, eng_id in parse_tatoeba_links(links_path):
            sentence = eng.get(eng_id)
            translation = translations.get(loc_id)
            if not sentence or not translation:
                continue
            hit = score(eng_id, sentence)
            if hit is None:
                continue
            difficulty, words = hit
            scored.append((difficulty, sentence, translation, words))
        rows = _select_example_rows(scored, per_word)
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

    # Letter/symbol homographs poison function words ("I" the pronoun vs
    # "i" the letter — whose Spanish "translation" is the letter i), so
    # only content-word entries contribute.
    # Entries vote per part of speech, and a POS priority resolves which
    # entry defines the word: pronoun/grammar entries first (so "I" the
    # pronoun beats "i" the letter-name noun), then noun before verb (so
    # "water" is agua, not the verb aguar). Within the winning POS the
    # MODAL translation across senses wins — Wiktionary's first sense is
    # often an oblique one ("you" → object clitic "lo").
    pos_priority = ("pron", "det", "article", "conj", "prep", "adp",
                    "particle", "num", "noun", "verb", "adj", "adv", "intj")
    priority_set = set(pos_priority)
    votes: dict[str, dict[str, dict[str, Counter]]] = {}
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
            pos = entry.get("pos") or ""
            if pos not in priority_set:
                continue
            # THE DICTIONARY'S PRIMARY SENSE decides: take the first sense
            # that carries translations (Wiktionary orders senses by
            # primacy), never a vote across all senses — voting let "go"'s
            # say-sense flood out the motion verbs, whose votes split over
            # идти/ехать/ходить. Top-level translation tables are grouped
            # by a "sense" caption in table order, NOT sense order, so they
            # are only used when no sense-level translations exist.
            # The PRIMARY sense is the one with the LARGEST translation
            # table — core meanings are translated into dozens of
            # languages, marginal ones ("a serving of water", "go: to
            # say") into a handful. First-listed order lied both ways.
            candidates: list[list] = [
                s2["translations"] for s2 in entry.get("senses") or []
                if s2.get("translations")
            ]
            top = entry.get("translations") or []
            if top:
                groups: dict[str, list] = {}
                for t in top:
                    groups.setdefault(t.get("sense") or "", []).append(t)
                candidates.extend(groups.values())
            if not candidates:
                continue
            translations = max(candidates, key=len)
            slot = votes.setdefault(word, {}).setdefault(pos, {})
            for t in translations:
                code = t.get("code") or t.get("lang_code")
                tw = (t.get("word") or "").strip()
                if code in locales and tw:
                    slot.setdefault(code, Counter())[tw] += 1
    # Keep votes PER part of speech — the seeder knows each word's own POS
    # (spaCy) and picks the matching entry, so "go" the verb gets ir/идти
    # while "water" the noun gets agua/вода. Never merge across entries:
    # Russian has no articles, so "a"'s article entry has no ru row, and
    # cross-entry back-fill once produced letter-name and abbreviation junk.
    # No equivalent in a language means NO translation — the UI falls back
    # to the English gloss.
    def _sane(word: str, tw: str) -> bool:
        if not tw or len(tw) > 40:
            return False
        if any(ch.isdigit() for ch in tw):
            return False
        if tw.lower() == word:  # "I" -> "i" is a letter echo, not a translation
            return False
        if "[" in tw or "]" in tw or "(" in tw:
            return False  # editorial brackets are not translations
        return True

    out: dict[str, dict[str, dict[str, str]]] = {}
    for word, per_pos in votes.items():
        for pos, counters in per_pos.items():
            resolved = {
                code: counter.most_common(1)[0][0]
                for code, counter in counters.items()
                if _sane(word, counter.most_common(1)[0][0])
            }
            if resolved:
                out.setdefault(word, {})[pos] = resolved
    return out


def build_english_frequency(cache_dir: Path, max_words: int = 10000) -> Path:
    """Build data/en_frequency.tsv from HermitDave (OpenSubtitles) at the
    same 10k scale as every other corpus language.

    The original bundled list had 3,001 words — which quietly capped the
    whole English pipeline: WordNet-backed vocab stopped at 1.7k and the
    i+1 sentence grader rejected almost every Tatoeba sentence (any word
    outside the list scores as unknown). Inflections fold onto lemmas via
    cached spaCy lemmatization.
    """
    from backend.services.nlp.english import EnglishNLP

    raw = download(
        SOURCES["frequencywords"].format(code="en"), cache_dir / "en_50k.txt"
    )
    _raw_lemmatize = EnglishNLP().lemmatize
    _cache: dict[str, str] = {}

    def lem(token: str) -> str:
        v = _cache.get(token)
        if v is None:
            v = _raw_lemmatize(token)
            _cache[token] = v
        return v

    counts: Counter = Counter()
    with open(raw, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) != 2 or not parts[1].isdigit():
                continue
            token = parts[0].lower()
            if not token.isalpha() or (len(token) == 1 and token not in ("a", "i")):
                continue
            counts[lem(token)] += int(parts[1])

    out_path = DATA_DIR / "en_frequency.tsv"
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["rank", "word"])
        for rank, (word, _n) in enumerate(counts.most_common(max_words), 1):
            writer.writerow([rank, word])
    logger.info("Wrote %d words to %s", min(max_words, len(counts)), out_path)
    return out_path


def build_english_translations(cache_dir: Path) -> Path:
    """Build data/en_translations.tsv (word/locale/translation) from kaikki."""
    build_english_frequency(cache_dir)
    freq_tsv = DATA_DIR / "en_frequency.tsv"
    # kaikki lookups are lowercase; the frequency list keeps spaCy's
    # capitalized lemmas ("I") — compare case-insensitively or the most
    # frequent word in English gets no translations at all.
    wanted = {w.lower() for w in _read_rank_by_word(freq_tsv)}

    path = download(SOURCES["en_kaikki_gz"], cache_dir / "en_kaikki.jsonl.gz")
    by_word = parse_english_kaikki_translations(
        path, wanted, set(ENGLISH_SUPPORT_ISO3)
    )

    out_path = DATA_DIR / "en_translations.tsv"
    n = 0
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["word", "pos", "locale", "translation"])
        for word in sorted(by_word):
            for pos in sorted(by_word[word]):
                for locale in sorted(by_word[word][pos]):
                    writer.writerow([word, pos, locale, by_word[word][pos][locale]])
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
    if language == "hi":
        # The rule lemmatizer folds only the most productive endings, so
        # corpus tokens like जाएगी or बच्चों miss the headword and the
        # sentence gets dropped. Expanding each headword into its surface
        # family (the same generator the answer-grader uses) closes most of
        # the gap: every family form scores at the headword's rank.
        nlp = HindiNLP()
        for word, rank in list(rank_by_word.items()):
            for form in nlp.get_morphological_family(word):
                rank_by_word.setdefault(form, rank)
    from backend.services.nlp.jamaican import JamaicanNLP
    from backend.services.nlp.latin_base import (
        HebrewNLP,
        IndonesianNLP,
        LatinNLP,
        PersianNLP,
        TagalogNLP,
    )

    nlp_by_lang = {
        "tr": TurkishNLP, "sw": SwahiliNLP, "yo": YorubaNLP,
        "xh": XhosaNLP, "ha": HausaNLP, "ru": RussianNLP,
        "jam": JamaicanNLP, "th": ThaiNLP, "la": LatinNLP,
        "id": IndonesianNLP, "tl": TagalogNLP, "he": HebrewNLP,
        "fa": PersianNLP,
        **FREQ_NLP,
    }
    lemmatize = nlp_by_lang[language]().lemmatize
    tokenize = None
    if language == "th":
        # Thai writes without spaces — greedy longest-match against the
        # frequency lexicon is the segmentation baseline (services/nlp/thai).
        from backend.services.nlp.thai import segment as thai_segment

        lexicon = set(rank_by_word)
        tokenize = lambda text: thai_segment(text, lexicon)  # noqa: E731
    rows = build_sentence_rows(
        parse_tatoeba_sentences(tgt),
        parse_tatoeba_sentences(eng),
        parse_tatoeba_links(links),
        rank_by_word,
        lemmatize,
        per_word=per_word,
        tokenize=tokenize,
    )
    out_path = DATA_DIR / f"{language}_sentences.tsv"
    n = write_sentences_tsv(rows, out_path)
    logger.info("Wrote %d example sentences to %s", n, out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build seed data from open datasets")
    parser.add_argument(
        "--language", "-l",
        choices=["tr", "sw", "yo", "ha", "xh", "mi", "es", "it", "fr", "de", "ca",
                 "ro", "el", "ar", "ru", "en", "pt", "hi", "jam", "nl", "th", "ko"],
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
