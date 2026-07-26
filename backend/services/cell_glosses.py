"""Plain-language glosses for Gym paradigm cells.

The Gym baseline is "base (form; gloss)" — e.g. "preparar (tú; you,
singular)". The Gym is PRACTICE, not recall: the learner is handed the
target-language dictionary form and asked to produce the cell, so the cell
label gets a native-language explanation instead of translating the word.

Coverage is deliberately partial: person pronouns, abstract agreement labels
(1sg, m.pl…), and Swahili noun classes. A cell with no gloss (articles,
particles, suffix cells like Turkish "-de") renders as plain "base (form)" —
never guess a gloss.
"""
from __future__ import annotations

# Language-independent labels used across the seed data.
_UNIVERSAL: dict[str, str] = {
    "1sg": "I",
    "2sg": "you, singular",
    "3sg": "he/she/it",
    "1pl": "we",
    "2pl": "you, plural",
    "3pl": "they",
    "3sg.m": "he",
    "3sg.f": "she",
    "m.sg": "masculine singular",
    "m.pl": "masculine plural",
    "f.sg": "feminine singular",
    "f.pl": "feminine plural",
    "n.sg": "neuter singular",
    "n.pl": "neuter plural",
    "m": "masculine",
    "f": "feminine",
    "n": "neuter",
    "masc": "masculine",
    "fem": "feminine",
    "neut": "neuter",
    "masculine": "masculine agreement",
    "feminine": "feminine agreement",
    "neuter": "neuter agreement",
    "pl": "plural",
    "plural": "plural",
    "singular": "singular",
    "neg": "negated",
    "impersonal": "impersonal",
}

# Per-language pronoun cells (exactly the values the seed data uses).
_BY_LANGUAGE: dict[str, dict[str, str]] = {
    "es": {
        "yo": "I", "tú": "you, singular", "él": "he", "ella": "she",
        "él/ella": "he/she", "usted": "you, formal",
        "nosotros": "we", "vosotros": "you, plural (Spain)",
        "ellos": "they", "ustedes": "you, plural",
    },
    "fr": {
        "je": "I", "tu": "you, singular", "il": "he", "elle": "she",
        "nous": "we", "vous": "you, plural/formal",
        "ils": "they, masculine", "elles": "they, feminine",
    },
    "it": {
        "io": "I", "tu": "you, singular", "lui": "he", "lei": "she",
        "lui/lei": "he/she", "Lei": "you, formal",
        "noi": "we", "voi": "you, plural", "loro": "they",
    },
    "pt": {
        "eu": "I", "tu": "you, singular", "você": "you",
        "ele": "he", "ela": "she", "nós": "we",
        "vocês": "you, plural", "eles": "they",
    },
    "ro": {
        "eu": "I", "tu": "you, singular", "el": "he", "ea": "she",
        "el/ea": "he/she", "noi": "we", "voi": "you, plural",
        "ei": "they, masculine", "ele": "they, feminine",
    },
    "ca": {
        "jo": "I", "tu": "you, singular", "ell": "he", "ella": "she",
        "vostè": "you, formal", "nosaltres": "we",
        "vosaltres": "you, plural", "ells": "they, masculine",
        "elles": "they, feminine",
    },
    "de": {
        "ich": "I", "du": "you, singular", "er": "he", "sie": "she / they",
        "es": "it", "wir": "we", "ihr": "you, plural",
        "sie (pl)": "they",
    },
    "tr": {
        "ben": "I", "sen": "you, singular", "o": "he/she/it",
        "biz": "we", "siz": "you, plural/formal", "onlar": "they",
    },
    "el": {
        "εγώ": "I", "εσύ": "you, singular", "αυτός": "he", "αυτή": "she",
        "αυτό": "it", "εμείς": "we", "εσείς": "you, plural",
        "αυτοί": "they",
    },
    "ru": {
        "он": "he", "она": "she", "оно": "it",
    },
    "ar": {
        "أنا": "I", "أنتَ": "you, masculine", "أنتِ": "you, feminine",
        "أنتم": "you, plural", "هو": "he", "هي": "she",
        "هم": "they", "نحن": "we",
    },
    "hi": {
        "मैं": "I", "तुम": "you, informal", "आप": "you, formal",
        "तुम-form": "you, informal", "आप-form": "you, formal",
    },
    "sw": {
        "cl.1": "noun class 1 — a person",
        "cl.2": "noun class 2 — people",
        "cl.5": "noun class 5",
        "cl.7": "noun class 7",
        "cl.8": "noun class 8",
        "cl.9": "noun class 9",
    },
    "jam": {
        "mi": "I", "im": "he/she", "unu": "you, plural",
    },
}


def cell_gloss(language_code: str | None, cell: str | None) -> str | None:
    """The native-language explanation of a paradigm cell, or None when the
    cell isn't a glossable label (articles, particles, suffixes…)."""
    label = (cell or "").strip()
    if not label:
        return None
    per_lang = _BY_LANGUAGE.get((language_code or "").strip())
    if per_lang:
        hit = per_lang.get(label)
        if hit:
            return hit
    return _UNIVERSAL.get(label) or _UNIVERSAL.get(label.lower())
