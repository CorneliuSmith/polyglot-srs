"""Greek → Latin reading (ELOT 743 / ISO 843 transcription).

Greek was the odd one out: Cyrillic got a computed reading and Greek did not,
though the two scripts pose a learner the same problem and Greek is the more
tractable of the pair — the mapping is regular, the exceptions are a closed
set of digraphs, and the standard is the one printed in Greek passports.

Transcription, not transliteration. ELOT 743 has two tables; the reading a
learner needs is the one that tells them how the word SOUNDS, so <αυ> before
a voiced sound is `av` and before a voiceless one is `af` — «αυτό» is *afto*,
not *auto*. Getting that backwards is worse than showing nothing, because a
reading is trusted precisely by the learner who cannot yet check it.

Accents are dropped: they mark stress, and ELOT 743 does not carry them into
the Latin form. Diaeresis IS meaningful — it exists to say "these two vowels
are NOT a digraph" (Μαΐου = *Maiou*, not *Meou*), so it is honoured and then
discarded.
"""
from __future__ import annotations

import unicodedata

# Voiceless consonants + word end. <αυ ευ ηυ> take `f` before these, `v` else.
VOICELESS = set("θκξπστφχψ")

DIGRAPHS = {
    "ου": "ou", "ΟΥ": "OU", "Ου": "Ou",
    "γγ": "ng", "γξ": "nx", "γχ": "nch",
    # Two digraphs whose value depends on POSITION. The initial form is listed
    # here and the medial one is substituted below.
    "μπ": "b",   # medial: mp
    "γκ": "gk",  # medial: ng
    "ντ": "nt", "τσ": "ts", "τζ": "tz",
}

SINGLE = {
    "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i",
    "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "x",
    "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y",
    "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o",
}


DIAERESIS = "\u0308"


def _strip_accents(text: str) -> str:
    """Drop tonos/oxia, keep diaeresis, and stay DECOMPOSED.

    Recomposing to NFC was a bug: it folded the surviving diaeresis back into
    a precomposed <ϊ>, which then fell through the letter tables and printed
    itself — «Μαΐου» came out *Maϊou*, Greek letter and all. Decomposed, the
    mark is its own character and the digraph check can simply look for it.
    """
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text)
        if ch == DIAERESIS or not unicodedata.combining(ch)
    )


def _case(value: str, first_upper: bool, rest_upper: bool = False) -> str:
    """<θ> is one Greek letter and two Latin ones, so an uppercase Θ is `Th`,
    not `TH` — unless the source really is shouting, which only the NEXT
    letter can tell us. Θεσσαλονίκη was coming out THessaloniki."""
    if not first_upper:
        return value
    return value.upper() if rest_upper else value.capitalize()


def _is_greek(ch: str) -> bool:
    return "Ͱ" <= ch <= "Ͽ" or "ἀ" <= ch <= "῿"


def greek_to_roman(text: str) -> str:
    """An ELOT 743 reading of *text*. Non-Greek runs pass through untouched,
    which is what keeps a cloze blank a blank."""
    if not text:
        return ""
    src = _strip_accents(text)
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        ch = src[i]
        if ch == DIAERESIS:
            i += 1  # already consumed as a grouping signal
            continue
        if not _is_greek(ch):
            out.append(ch)
            i += 1
            continue

        low = ch.lower()
        nxt = src[i + 1].lower() if i + 1 < n else ""
        upper = ch.isupper()
        nxt_upper = src[i + 1].isupper() if i + 1 < n else False
        # A diaeresis on the SECOND vowel says "these are two sounds, not a
        # digraph" — «Μαΐου» is *Maiou*, never *Meou*. It is the one mark that
        # changes how letters group, which is why it survives _strip_accents.
        split = i + 2 < n and src[i + 2] == DIAERESIS

        two = low + nxt
        if not split and two in ("αυ", "ευ", "ηυ"):
            after = src[i + 2].lower() if i + 2 < n else ""
            voiced = not (after in VOICELESS or not _is_greek(after))
            base = {"αυ": "a", "ευ": "e", "ηυ": "i"}[two]
            out.append(_case(base + ("v" if voiced else "f"), upper, nxt_upper))
            i += 2
            continue
        if not split and two in DIGRAPHS:
            val = DIGRAPHS[two]
            # <γκ> had no entry at all until the corpus check caught it: it
            # fell through to γ→g plus κ→k, which is right word-initially by
            # pure accident and wrong everywhere else — έγκυος read *egkyos*
            # for *engyos*, πιγκουίνος *pigkouinos* for *pingouinos*. The μπ
            # branch beside it had implemented exactly this split for months.
            if out and out[-1][-1:].isalpha():
                val = {"μπ": "mp", "γκ": "ng"}.get(two, val)
            out.append(_case(val, upper, nxt_upper))
            i += 2
            continue

        val = SINGLE.get(low)
        if val is None:
            out.append(ch)
            i += 1
            continue
        # Final sigma is written ς, but <σ> at word end means the same sound.
        out.append(_case(val, upper, nxt_upper))
        i += 1
    return "".join(c for c in out if c != DIAERESIS)
