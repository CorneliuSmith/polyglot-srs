"""Thai → Latin reading (RTGS, via pythainlp).

Thai was the last non-Roman script in this corpus with no reading at all —
3,754 words and 4,376 sentences. The seeder deferred it, and unlike Korean's
deferral the reasoning was sound: RTGS is not a character mapping. Thai writes
vowels before, above, below and after their consonant, leaves some implicit,
and marks no boundaries between words. You cannot romanize it without first
knowing where the words and syllables are, which needs a real segmenter.

So this defers to one. Two decisions, both measured rather than assumed:

**Tokenize first.** Handing a whole sentence to `romanize` returns one
unbroken string — ผมชอบอาหารไทย becomes *phomchop-ahanthai*, which a learner
cannot read any more easily than the Thai. Segmenting with `newmm` (bundled
dictionary, offline) gives *phom chop ahan thai*, which is the point.

**Use the neural engine, not the rule-based default.** `royin` implements RTGS
by rule and fails on ordinary words: over the 3,754-word Thai vocabulary it
left raw Thai characters in its own output 107 times (2.9%) — เพราะ
"because" came out *pheraะ*, มหาวิทยาลัย *mahaoิtyalai*, ก็ได้ *k็dai* — and
silently dropped initial consonants elsewhere (หาร → *an*, not *han*). It also
mis-syllabified compounds: คนไทย → *khanathai* for *khon thai*. `thai2rom_onnx`
gets every one of those right and leaves ZERO Thai characters across the same
3,754 words, at 0.8 ms each. Its model ships inside the pythainlp package
(4 MB of ONNX), so nothing is downloaded at runtime.

**What RTGS does not give you, stated plainly:** it drops tone entirely and
does not distinguish vowel length. Thai is tonal, so this reading tells a
learner how to *approximate* a word, never how to say it correctly — คำ and
ค่ำ both romanize to *kham*. That is a limit of the standard, not of this
code, and it is why the seeder's note asked for "romanization with tones". A
tone-marked reading still wants a native reviewer. This is the honest floor:
better than nothing for a script that is otherwise opaque, and no substitute
for hearing the word.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

THAI_START, THAI_END = "฀", "๿"
ENGINE = "thai2rom_onnx"

# ๆ (ไม้ยมก, mai yamok) is a repetition mark, not a letter: it has no sound of
# its own and tells the reader to say the preceding word twice. Handed to the
# engine as a token it hallucinates a syllable out of nothing — มากๆ came out
# *mak wi*, นานๆ *nano*, ต่างๆ *tango*. Expanding it first is deterministic
# and correct, so it is fixed here even though the layer does not ship.
MAI_YAMOK = "ๆ"


def _is_thai(ch: str) -> bool:
    return THAI_START <= ch <= THAI_END


def thai_to_roman(text: str) -> str:
    """An RTGS reading of *text*, word-segmented. Non-Thai runs pass through
    verbatim, which is what keeps a cloze blank a blank — an earlier draft
    assembled character by character and shredded `{{answer}}` into
    `{{a n s w e r}}`."""
    if not text or not any(_is_thai(c) for c in text):
        return ""
    try:
        from pythainlp.tokenize import word_tokenize
        from pythainlp.transliterate import romanize
    except ImportError:  # dependency dropped to save build disk — see pyproject
        logger.warning("pythainlp is not installed; Thai readings are off")
        return ""

    # Split into alternating Thai / non-Thai SEGMENTS, never characters.
    segments: list[tuple[bool, str]] = []
    for ch in text:
        thai = _is_thai(ch)
        if segments and segments[-1][0] == thai:
            segments[-1] = (thai, segments[-1][1] + ch)
        else:
            segments.append((thai, ch))

    out: list[str] = []
    for thai, chunk in segments:
        if not thai:
            # Thai carries no spaces of its own, so a non-Thai run lands flush
            # against the romanized words on either side. Pad the ones that are
            # WORDS — `{{answer}}`, `___`, an embedded Latin name — and leave
            # bare punctuation hugging its neighbour, so `chaimai?` stays put
            # while `kin{{answer}}thukwan` becomes `kin {{answer}} thukwan`.
            # A punctuation-based rule cannot make this distinction: the blank
            # token opens with `{`, which every such rule treats as leading.
            if any(c.isalnum() or c == "_" for c in chunk):
                out.append(" " + chunk.strip() + " ")
            else:
                out.append(chunk)
            continue
        words = [w for w in word_tokenize(chunk, keep_whitespace=False) if w.strip()]
        expanded: list[str] = []
        for w in words:
            if w == MAI_YAMOK:
                if expanded:
                    expanded.append(expanded[-1])
                continue
            if w.endswith(MAI_YAMOK):  # the tokenizer sometimes keeps it attached
                stem = w[:-1].strip()
                if stem:
                    expanded += [stem, stem]
                continue
            expanded.append(w)
        words = expanded
        romanized = []
        for w in words:
            try:
                r = (romanize(w, engine=ENGINE) or "").strip()
            except Exception as exc:  # noqa: BLE001 — a reading must never 500
                logger.warning("thai romanize failed for %r: %s", w, exc)
                continue
            if r:
                romanized.append(r)
        if romanized:
            out.append(" ".join(romanized))

    return " ".join("".join(out).split())
