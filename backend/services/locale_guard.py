"""Does this text actually read in the language we are about to call it?

A learner studying Turkish with Arabic support was shown
"This city is very big and millions of people live there." under the
label الترجمة. The text was not wrong — it was English, served because no
Arabic rendering existed yet, and every layer downstream simply trusted
that whatever came back was in the requested locale.

Two different failures produce that screen, and only one of them is
visible in SQL:

  * MISSING — the locale row does not exist, so the query's COALESCE /
    `translation_locale IN (locale, 'en')` fallback serves English. The
    query knows; it just never said so, because the served locale was
    not selected into the payload.
  * MISLABELLED — a row exists FOR the locale and holds the wrong
    language anyway: an auto-translate pass that echoed its input, an
    import with the locale column defaulted, a hand-edit into the wrong
    row. No amount of locale tracking catches this one, because the
    database already believes it is Arabic.

This module catches both, by asking the only question that survives
either failure: is this text written in the script the locale uses?

That question has no answer for a Latin-script locale — "the book" and
"el libro" are the same script — so `script_of` returns None there and
`text_matches_locale` answers True rather than guessing. This guard is
deliberately one-sided: what it flags IS wrong, what it passes is merely
not provably wrong, and the served-locale field carried alongside it in
the payload covers the Latin-to-Latin case.
"""
from __future__ import annotations

import unicodedata

# Locale -> the script its prose is written in. Only locales whose script
# differs from Latin can be checked this way; everything else is absent on
# purpose and reads as "cannot tell".
_LOCALE_SCRIPT: dict[str, str] = {
    "ar": "ARABIC",
    "fa": "ARABIC",
    "ur": "ARABIC",
    "he": "HEBREW",
    "yi": "HEBREW",
    "ru": "CYRILLIC",
    "uk": "CYRILLIC",
    "bg": "CYRILLIC",
    "sr": "CYRILLIC",
    "el": "GREEK",
    "hi": "DEVANAGARI",
    "mr": "DEVANAGARI",
    "ne": "DEVANAGARI",
    "th": "THAI",
    "ko": "HANGUL",
    "ja": "HIRAGANA",   # kana carry the grammar; kanji alone is ambiguous
    "zh": "CJK",
    "hy": "ARMENIAN",
    "ka": "GEORGIAN",
    "am": "ETHIOPIC",
    "bn": "BENGALI",
    "ta": "TAMIL",
    "te": "TELUGU",
}

# Enough of the text must be in the expected script to call it that
# language. Well below half on purpose: a real translation can be mostly
# a quoted Latin name ("فيلم Titanic رائع") and must still pass, while
# fully-English prose scores zero and never squeaks through.
_MIN_SCRIPT_RATIO = 0.25


def script_of(locale: str | None) -> str | None:
    """The script *locale* is written in, or None when it cannot be used to
    tell languages apart (every Latin-script locale)."""
    if not locale:
        return None
    return _LOCALE_SCRIPT.get(locale.split("-")[0].strip().lower())


def _script_name(ch: str) -> str | None:
    """The script a single letter belongs to, by its Unicode name. Anything
    that is not a letter — digits, punctuation, spaces, emoji — has no
    script and is excluded from the ratio entirely, so "١٩٩١ ,." neither
    proves nor disproves anything."""
    if not ch.isalpha():
        return None
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return None
    first = name.split()[0]
    if first in ("HIRAGANA", "KATAKANA"):
        return "HIRAGANA"
    if first == "CJK":
        return "CJK"
    return first


def script_ratio(text: str, script: str) -> float:
    """Share of *text*'s letters that are written in *script* (0.0–1.0).
    Returns 0.0 for text with no letters at all."""
    letters = [s for s in (_script_name(c) for c in text) if s is not None]
    if not letters:
        return 0.0
    return sum(1 for s in letters if s == script) / len(letters)


def has_letters(text: str) -> bool:
    """Whether *text* contains anything a script could be read off. A date,
    a price or a lone dash does not."""
    return any(_script_name(c) for c in text)


def text_matches_locale(text: str | None, locale: str | None) -> bool:
    """True unless *text* is provably not written in *locale*.

    Three things pass without being checked, because none of them is
    evidence of the wrong language: empty text (that is a missing field,
    a different bug), text with no letters at all ("1991", "—"), and any
    Latin-script locale (indistinguishable by script).
    """
    if not text or not text.strip():
        return True
    script = script_of(locale)
    if script is None:
        return True
    if not has_letters(text):
        return True
    return script_ratio(text, script) >= _MIN_SCRIPT_RATIO


# The fields that are supposed to be in the LEARNER'S language.
# Deliberately not `sentence`, `correct_answer`, `gloss` or
# `transliteration`: those are in (or about) the language being studied,
# and checking them against the support locale would flag every card.
LOCALIZED_FIELDS = ("translation", "hint", "definition", "baseline")

# A personal cloze card's hint is its ANSWER — the learner's own word in
# the language they are studying (repositories/cards.py serves
# `cc.answer AS hint`, because a personal card carries no authored cue).
# Checking it against the support locale flags every personal card of
# every non-Latin learner, which is how this guard would have earned a
# reputation for crying wolf on its first day.
_FIELDS_BY_CARD_TYPE: dict[str, tuple[str, ...]] = {
    "personal": ("translation",),
}


def fields_for(card_type: str | None) -> tuple[str, ...]:
    return _FIELDS_BY_CARD_TYPE.get(card_type or "", LOCALIZED_FIELDS)


def mismatched_fields(
    card: dict, locale: str | None, fields: tuple[str, ...] | None = None
) -> list[str]:
    """Which of *card*'s learner-language fields are provably not in
    *locale*. Empty list is the normal case — including for every
    Latin-script locale, where this cannot be determined."""
    if script_of(locale) is None:
        return []
    checked = fields if fields is not None else fields_for(card.get("card_type"))
    return [
        f for f in checked
        if f in card and not text_matches_locale(card.get(f), locale)
    ]


def mark_locale_mismatches(card: dict, locale: str | None) -> dict:
    """Stamp a card with the fields that are not in the learner's language,
    and strip the ones that are a THIRD language.

    Applied to the assembled payload rather than inside each query on
    purpose: one call covers vocabulary, grammar and personal cards, and
    it catches a row that merely CLAIMS to be in the locale — which no
    amount of tracking the served locale in SQL can do.

    Two outcomes, because a mismatch is not one thing:

    * **English** (or anything this cannot read) is KEPT and labelled. It
      is the app's authored base and the fallback every query already
      reaches for, and the field is the learner's only semantic cue on a
      cloze — withholding it would trade a card they can read the wrong
      language on for one they cannot answer at all.
    * **A provable third language is REMOVED.** "El bebé llora mucho por
      la noche." under an Arabic label helps nobody: it is not what they
      asked for and not the fallback either. The owner's rule is the
      learner's locale, else English, never a third language — so the
      field goes, the card serves without it exactly as a card that never
      had a translation does, and `locale_withheld` says so for anything
      that wants to report it.

    Removal needs proof on both halves (not the locale AND not English),
    so an undecidable string keeps its old behaviour. Absent keys mean
    "nothing to report", so older clients and every Latin-script locale
    see exactly what they saw before.
    """
    bad = mismatched_fields(card, locale)
    if not bad:
        return card
    withheld = [f for f in bad if is_probably_english(card.get(f)) is False]
    if withheld:
        for f in withheld:
            card[f] = None
        card["locale_withheld"] = withheld
    labelled = [f for f in bad if f not in withheld]
    if labelled:
        card["locale_mismatch"] = labelled
    return card


# ---------------------------------------------------------------------------
# The Latin-to-Latin case the script check cannot reach.
#
# The script test above proves "this is not Arabic". It cannot prove "this is
# Spanish rather than English", because they share an alphabet — and that is
# the gap a learner fell into: an Arabic-support account studying English was
# shown "El bebé llora mucho por la noche." under "الترجمة (not in your
# language yet)". The script guard did its job (that is certainly not Arabic)
# and then the payload served the row anyway, because the only alternative it
# knew about was withholding the learner's one semantic cue.
#
# English is the app's authored base and the fallback every query already
# reaches for, so the rule the owner asked for is: the learner's locale, else
# English, and never a third language. Deciding that needs one question the
# script test cannot answer — is this English? — so here is the cheapest
# honest answer to it: function words. No model call, no dependency, and it
# runs on every card.
#
# It is deliberately one-sided in the same way the script guard is. It reports
# "provably not English" or "cannot tell", never "definitely English", and
# only the first of those changes what a learner sees. Anything short,
# ambiguous, or unmarked keeps its old behaviour — which matters more than it
# looks, because the English course's own drill translations are terse notes
# like "Introducing yourself." with no function words in them at all, and
# withholding those would be a worse bug than the one this fixes.

# Words that are common in one Latin-script language and rare or absent in
# English. Chosen to be closed-class (articles, prepositions, conjunctions,
# copulas): they appear in almost any sentence of their language and are not
# borrowed into English prose the way nouns are.
_LATIN_MARKERS: dict[str, frozenset[str]] = {
    "es": frozenset("el la los las un una unos unas que por con para del al "
                    "es son está están muy más pero como cuando donde porque "
                    "su sus lo se no hay tiene".split()),
    "pt": frozenset("o os as um uma que por com para do da dos das no na "
                    "não mais muito mas como quando onde porque seu sua é "
                    "são está estão tem".split()),
    "fr": frozenset("le la les un une des du de est sont dans pour avec "
                    "mais très plus ce cette qui que ne pas au aux sur son "
                    "ses leur elle il".split()),
    "it": frozenset("il lo la gli le un una che per con del della dei delle "
                    "è sono molto più ma come quando dove perché suo sua "
                    "nel nella non".split()),
    "de": frozenset("der die das ein eine einen und ist sind nicht mit für "
                    "sehr aber auch von zu im am auf dem den des".split()),
    "nl": frozenset("de het een en is zijn niet met voor zeer maar ook van "
                    "naar op in aan dat die deze".split()),
    "ca": frozenset("el la els les un una que amb per del dels són és molt "
                    "més però com quan on perquè seva seu".split()),
    "ro": frozenset("și este sunt nu cu pentru din care mai foarte dar când "
                    "unde pentru că lui ei".split()),
    "tr": frozenset("bir ve bu için ile çok daha değil ama gibi olarak "
                    "kadar sonra önce her".split()),
    "id": frozenset("yang dan di ke dari untuk dengan tidak ini itu adalah "
                    "pada atau juga akan sudah".split()),
}

# The same class of word in English, to compare against.
_ENGLISH_MARKERS = frozenset(
    "the a an is are was were be been and or of to in on at for with that "
    "this these those it he she they you i not very more but as from by "
    "have has had do does did will would can could".split()
)

# Letters and punctuation that only some of these languages use. Worth a
# marker each on their own, because a short string can carry one of these
# and no function word at all ("Año nuevo").
_LATIN_SIGNS: dict[str, str] = {
    "es": "ñ¿¡",
    "pt": "ãõ",
    "fr": "œ",
    "de": "ß",
    "tr": "ğışİ",
    "ro": "ăâîșț",
}

# Two hits, and more than English scores. One hit is a coincidence — "die"
# and "a" are English words too — and requiring a MARGIN over English keeps
# a sentence that merely quotes a foreign phrase on the English side.
_LATIN_MIN_HITS = 2


def _words(text: str) -> list[str]:
    out, cur = [], []
    for ch in text.lower():
        if ch.isalpha():
            cur.append(ch)
        elif cur:
            out.append("".join(cur))
            cur = []
    if cur:
        out.append("".join(cur))
    return out


def probable_latin_language(text: str | None) -> str | None:
    """The Latin-script language *text* is probably in, or None when the
    evidence does not support naming one. Never returns 'en': this exists
    to answer "is it something OTHER than English", and English is the
    thing being compared against."""
    if not text or not text.strip():
        return None
    words = _words(text)
    if not words:
        return None
    seen = set(words)
    english = sum(1 for w in seen if w in _ENGLISH_MARKERS)
    best, best_score = None, 0
    for code, markers in _LATIN_MARKERS.items():
        score = sum(1 for w in seen if w in markers)
        score += sum(1 for ch in _LATIN_SIGNS.get(code, "") if ch in text.lower())
        if score > best_score:
            best, best_score = code, score
    if best_score >= _LATIN_MIN_HITS and best_score > english:
        return best
    return None


def is_probably_english(text: str | None) -> bool | None:
    """True when *text* looks like English, False when it provably looks
    like another Latin-script language, None when there is not enough to
    go on. Only False is acted on."""
    if not text or not text.strip():
        return None
    if probable_latin_language(text) is not None:
        return False
    return True if any(w in _ENGLISH_MARKERS for w in _words(text)) else None


def is_third_language(text: str | None, locale: str | None) -> bool:
    """*text* is neither the learner's locale nor English — the one case
    that must never be served. Requires PROOF on both halves, so an
    undecidable string is not a third language and keeps its old
    behaviour."""
    if text_matches_locale(text, locale):
        return False
    return is_probably_english(text) is False
