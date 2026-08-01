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


def is_explicit(*texts: str | None) -> bool:
    """True if any of *texts* reads as explicit.

    Pass every English-side field you have — a vocabulary item's definition
    and its part of speech, or a sentence and its translation. Any hit marks
    the row.
    """
    for text in texts:
        if not text:
            continue
        if _TERM_RE.search(text) or _QUALIFIER_RE.search(text):
            return True
    return False


#: The same rule as SQL, for the migration's backfill and for any query that
#: wants to filter without a per-row Python pass. Kept beside the Python
#: version deliberately: they must agree, and a reader comparing them should
#: not have to go looking. `~*` is Postgres case-insensitive regex.
SQL_EXPLICIT_PATTERN = (
    r"\y(" + "|".join(_EXPLICIT_TERMS) + r")\y"
    r"|" + "|".join(_EXPLICIT_QUALIFIERS)
)
