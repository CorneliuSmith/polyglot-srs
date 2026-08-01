"""Explicit-content detection for seeded and generated learner content.

Why this exists: the frequency lists and the harvested sentence corpora come
from subtitle and web data, which is honest about how people actually speak.
Spanish *puta* sits at rank 505 — inside the first thousand words any beginner
meets — and the sentence corpus supplied "Fucking whore." as its example. A
learner reported it. Nobody had chosen to teach them that word; it arrived
because it is genuinely frequent.

The judgement call, and it is a real one: this is NOT censorship of the
language. Adult learners reading real material will meet these words, they are
frequent for a reason, and a learner who has opted in should get them — that
is why the setting exists rather than a permanent deletion. But arriving
unannounced in a beginner's second week, in an app someone might be using on a
commute or handing to a teenager, is a different thing. So: off by default,
one toggle to turn on.

Matching runs on the ENGLISH side — the definition of a vocabulary item, the
translation of a sentence. That is the reliable common denominator: every
seeded row has one, the vocabulary spans twenty-odd languages whose profanity
we cannot enumerate, and a lexicographer writing "whore, slut, prostitute" as
a gloss has already done the classification for us.

Kept deliberately narrow. Mild words (damn, hell, crap) are NOT here: a filter
that hides "hell" breaks religious and idiomatic vocabulary across most of the
languages, and a learner who turns this on expecting to avoid slurs did not
ask to lose *diablo*. False positives are worse than misses here, because a
miss is visible and reportable while a silently-hidden word is neither.
"""
from __future__ import annotations

import re

#: Whole words (and obvious compounds) that mark a gloss as explicit.
#: Word-boundary matched, so "assassin", "bass" and "Scunthorpe" are safe.
_EXPLICIT_TERMS = (
    # Sexual slurs and sex work — the reported case.
    "whore", "whores", "whoring", "whorehouse", "whorehouses",
    "slut", "sluts", "slutty",
    "prostitute", "prostitutes", "prostitution",
    "hooker", "hookers", "brothel", "brothels", "pimp", "pimps",
    # Strong profanity.
    "fuck", "fucks", "fucked", "fucking", "fucker", "fuckers",
    "shit", "shits", "shitty", "shitting", "bullshit",
    "cunt", "cunts", "twat", "twats",
    "bitch", "bitches", "bastard", "bastards",
    "wanker", "wankers", "bollocks", "arsehole", "asshole", "assholes",
    "dickhead", "prick", "pricks",
    # Explicit anatomy and acts. "Penis"/"vagina" are deliberately ABSENT:
    # they are clinical, appear in medical and biology vocabulary, and
    # hiding them would be prudishness rather than protection.
    # "cock" is absent on purpose: it glosses *gallo*, *coq*, *Hahn* — the
    # rooster — across half the catalogue, and hiding those to catch a sense
    # "dick" already covers is exactly the false positive this list is
    # supposed to avoid.
    "dick", "dicks", "tits", "titties",
    "blowjob", "blowjobs", "handjob", "cum", "jizz", "wank",
    "masturbate", "masturbation", "masturbating",
    "porn", "porno", "pornography", "pornographic",
    "orgasm", "orgasms",
    # Slurs. Not enumerated further than this: the general principle is that
    # a gloss whose own wording flags it ("offensive", "vulgar", "slur") is
    # caught by the qualifier list below, which generalises better than
    # chasing every epithet.
    "faggot", "faggots",
)

#: Lexicographers label these themselves. Catching the LABEL generalises past
#: any word list we could write, and across every language in the catalogue.
_EXPLICIT_QUALIFIERS = (
    "vulgar", "obscene", "profanity", "expletive",
    "derogatory slur", "ethnic slur", "racial slur",
    "taboo word", "swear word", "swearword",
)

_TERM_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in _EXPLICIT_TERMS) + r")\b",
    re.IGNORECASE,
)
_QUALIFIER_RE = re.compile(
    "|".join(re.escape(q) for q in _EXPLICIT_QUALIFIERS), re.IGNORECASE
)


#: A gloss that calls a sense mild is telling us not to filter it. Checked
#: before the qualifier list, which would otherwise match the word
#: "expletive" inside "(mild expletive)".
_MILD_RE = re.compile(r"\bmild(ly)?\b", re.IGNORECASE)


def _primary_sense(text: str) -> str:
    """The first sense of a gloss.

    Dictionary glosses lead with the primary sense and push the rest behind a
    semicolon: "cursed; damned, freaking, fucking" is *maldito*, an extremely
    common word whose first meaning is "cursed" — matching anywhere in the
    string hid it from every Spanish learner over a register listed fourth.
    Same for Hindi गंदगी, "filth, dirt; a vulgarity, expletive", which simply
    means dirt, and Turkish *herif*, "comrade, colleague; a term of
    contempt".

    Only the leading sense decides. A word whose FIRST meaning is explicit is
    an explicit word; one that merely has a crude sense somewhere is an
    ordinary word people also swear with, and the whole point of erring
    toward misses is that a wrongly-hidden word is invisible and unreportable.

    Splitting on the semicolon only, NOT the parenthesis: a gloss often opens
    with a register label — French *con* is "(dated) cunt, pussy" — and
    treating that label as the whole primary sense threw the actual meaning
    away and released a word nobody would call ordinary.
    """
    head = re.split(r";", text, maxsplit=1)[0]
    # Drop a leading register/usage label so the sense itself is what's read.
    return re.sub(r"^\s*\([^)]*\)\s*", "", head)


def _matches(text: str) -> bool:
    return bool(_TERM_RE.search(text) or _QUALIFIER_RE.search(text))


def is_explicit_gloss(*definitions: str | None) -> bool:
    """True if a DICTIONARY GLOSS names an explicit word.

    Judged on the leading sense only, and skipped entirely when the
    lexicographer has already labelled the sense mild.
    """
    for text in definitions:
        if not text or _MILD_RE.search(text):
            continue
        if _matches(_primary_sense(text)):
            return True
    return False


def is_explicit_sentence(*texts: str | None) -> bool:
    """True if a SENTENCE (or its translation) reads as explicit.

    Judged whole. A sentence has no primary sense to lead with, and applying
    the gloss rule to one lets "Nice weather today; fuck off." through on the
    strength of its first clause — which a draft of this module did, and only
    a test caught. Two functions rather than one with a flag, because the
    call sites are the thing that knows which kind of text it holds, and the
    SQL in migration 20260911 draws exactly the same distinction.
    """
    return any(_matches(t) for t in texts if t)


#: The same rule as SQL, for the migration's backfill and for any query that
#: wants to filter without a per-row Python pass. Kept beside the Python
#: version deliberately: they must agree, and a reader comparing them should
#: not have to go looking. `~*` is Postgres case-insensitive regex.
SQL_EXPLICIT_PATTERN = (
    r"\y(" + "|".join(_EXPLICIT_TERMS) + r")\y"
    r"|" + "|".join(_EXPLICIT_QUALIFIERS)
)
