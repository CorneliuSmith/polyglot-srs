"""Hindi NLP backend: Devanagari normalization, rule-based lemmatizer, and
a romanizer with schwa deletion for vocabulary readings.

Hindi has no lightweight pure-Python morphological analyzer bundled here, so
the lemmatizer is rule-based like the Latin-tier backends: it folds the most
productive inflections (verb habitual/participle endings, oblique plurals,
marked-noun obliques) onto their citation forms so OpenSubtitles corpus
tokens match kaikki Wiktionary headwords. A real analyzer can replace it
later without changing the interface.

The romanizer produces the practical (Hunterian-style) reading shown as the
transliteration hint layer: IAST-ish vowel qualities without diacritic
clutter, with the standard schwa-deletion heuristic (word-final inherent -a
always dropped; medial inherent -a dropped in the VC_CV context, which gets
laṛkā/samajh/naukrī right). Readings are aids, not phonology — flagged for
native review with the rest of the Hindi tier.
"""
from __future__ import annotations

import unicodedata

from backend.services.nlp.base import BaseNLP

# ── Devanagari → roman tables ───────────────────────────────────────────────

_INDEPENDENT_VOWELS = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ii", "उ": "u", "ऊ": "uu",
    "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "ऑ": "o", "ऍ": "e",
}

_MATRAS = {
    "ा": "aa", "ि": "i", "ी": "ii", "ु": "u", "ू": "uu",
    "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    "ॉ": "o", "ॅ": "e",
}

_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
    "ष": "sh", "स": "s", "ह": "h",
}

# NFC DECOMPOSES the precomposed nukta letters (U+0958–095F), so the nukta
# always arrives as base consonant + U+093C; this maps the base to the
# Perso-Arabic loan sound.
_NUKTA_SOUNDS = {
    "क": "q", "ख": "kh", "ग": "gh", "ज": "z", "झ": "zh",
    "ड": "r", "ढ": "rh", "फ": "f",
}

_VIRAMA = "्"
_ANUSVARA = "ं"
_CHANDRABINDU = "ँ"
_NUKTA = "़"


def devanagari_to_roman(text: str) -> str:
    """Romanize Devanagari with the practical schwa-deletion heuristic."""
    text = unicodedata.normalize("NFC", text.strip())
    out: list[str] = []
    for token in text.split():
        out.append(_romanize_word(token))
    return " ".join(out)


def _romanize_word(word: str) -> str:
    # Pass 1: expand to syllable units [roman, vowel, is_script] where vowel
    # may be the inherent schwa "a", an explicit matra, or "" (virama).
    # is_script marks Devanagari-derived units so punctuation riding on the
    # word (मतलब?) never blocks word-final schwa deletion.
    units: list[list] = []
    chars = list(word)
    i = 0
    while i < len(chars):
        ch = chars[i]
        if ch in _CONSONANTS:
            cons = _CONSONANTS[ch]
            i += 1
            if i < len(chars) and chars[i] == _NUKTA:
                cons = _NUKTA_SOUNDS.get(ch, cons)
                i += 1
            if i < len(chars) and chars[i] in _MATRAS:
                units.append([cons, _MATRAS[chars[i]], True])
                i += 1
            elif i < len(chars) and chars[i] == _VIRAMA:
                units.append([cons, "", True])
                i += 1
            else:
                units.append([cons, "a", True])  # inherent schwa
        elif ch in _INDEPENDENT_VOWELS:
            units.append(["", _INDEPENDENT_VOWELS[ch], True])
            i += 1
        elif ch in (_ANUSVARA, _CHANDRABINDU):
            if units:
                units[-1][1] += "n"
            i += 1
        else:
            units.append([ch, "", False])  # pass through anything unknown
            i += 1

    # Pass 2: schwa deletion, RIGHT TO LEFT (the standard rule): an inherent
    # schwa deletes word-finally, and medially in V C _ C V — where the
    # following vowel is read AFTER later deletions have applied, so
    # मतलब → matlab (final ब deletes first, then त's schwa survives is
    # wrong — त deletes because ल still carries its vowel) and
    # लड़का → laṛkā, समझ → samajh, जनता → jantā all come out right.
    script_idx = [k for k, u in enumerate(units) if u[2]]
    for pos in range(len(script_idx) - 1, -1, -1):
        k = script_idx[pos]
        unit = units[k]
        if unit[1] != "a":
            continue
        nxt = units[script_idx[pos + 1]] if pos + 1 < len(script_idx) else None
        if nxt is None:
            unit[1] = ""  # word-final
            continue
        prev = units[script_idx[pos - 1]] if pos > 0 else None
        if prev is not None and prev[1] != "" and nxt[1] != "":
            unit[1] = ""

    return "".join(c + v for c, v, _s in units)


# ── Lemmatizer rules ────────────────────────────────────────────────────────

# Ordered (suffix, replacement) rules; first match wins. Productive verb
# endings fold onto the -नाinfinitive; noun rules fold oblique/plural marked
# forms onto the -ा citation form.
_LEMMA_RULES: list[tuple[str, str]] = [
    ("ताा", "ना"),      # defensive doubled-matra artifacts in subtitles
    ("ता", "ना"), ("ती", "ना"), ("ते", "ना"),        # habitual participle
    ("या", "ना"), ("ये", "ना"), ("यी", "ना"),        # perfective (आया…)
    ("ेंगे", "ना"), ("ेगा", "ना"), ("ेगी", "ना"),    # future
    ("िए", "ना"), ("िये", "ना"),                     # polite imperative
    ("ों", "ा"), ("ें", ""), ("ियों", "ी"),          # oblique plurals
    ("े", "ा"),                                       # marked-noun oblique
]


class HindiNLP(BaseNLP):
    """Rule-based Hindi backend (Devanagari; no case, no diacritic folding)."""

    def normalize(self, text: str) -> str:
        return text.strip().lower()

    def lemmatize(self, word: str) -> str:
        w = word.strip().lower()
        for suffix, repl in _LEMMA_RULES:
            if w.endswith(suffix) and len(w) > len(suffix) + 1:
                return w[: -len(suffix)] + repl
        return w

    def get_morphological_family(self, word: str) -> set[str]:
        w = word.strip().lower()
        family = {w, self.lemmatize(w)}
        # Expand a -ना infinitive into its most common surface forms so the
        # grader accepts them as WRONG_FORM (right word, wrong inflection).
        lemma = self.lemmatize(w)
        if lemma.endswith("ना"):
            stem = lemma[:-2]
            family |= {
                stem + "ता", stem + "ती", stem + "ते",
                stem + "या", stem + "ेगा", stem + "ेगी", stem + "ो",
            }
        return family

    def get_aspect_partner(self, verb: str, card_context: dict | None = None) -> str | None:
        return None
