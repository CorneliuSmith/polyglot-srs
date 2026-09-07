"""Telling a drill's translation apart from an English usage note.

On every course but English a drill's `translation` renders its sentence in
the learner's language. On the English course the target language IS the
metalanguage, so an English-for-English "translation" would hand over the
answer — the field holds a usage NOTE instead ("Bare form — no -s.",
"The past of 'eat'."), and the real translations live per locale in
`data/grammar/en_drill_hints.<locale>.json`, 19 files attached by
`seed_grammar`. `docs/quality/en.md` note 0 is the convention.

The convention is sound, and invisible until the learner's locale is English
too: no `drill_hint_translations` row exists for `en`, the COALESCE that
serves the card falls through to the note, and the card prints
"do — the participle." under the heading **Translation** — a heading that
promises a rendering of the sentence and delivers a remark about it. The
owner met it on their own card (CHECKS §27).

This lives outside both repositories because both need it and `cards`
already imports `curriculum`.
"""
from __future__ import annotations

NOTE_AS_TRANSLATION_COURSES = frozenset({"en"})


def split_note(
    language_code: str | None,
    localized: str | None,
    base: str | None,
) -> tuple[str | None, str | None]:
    """Return (translation, context) for one drill.

    *localized* is what the COALESCE produced — the learner's-locale row when
    one exists, otherwise the authored field. *base* is the authored field on
    its own, which is what makes the two distinguishable.

    Off the English course there is no note, so this is a no-op: the
    translation stands and the context is empty.
    """
    if language_code not in NOTE_AS_TRANSLATION_COURSES:
        return localized, None
    note = (base or "").strip() or None
    # A "localized" value equal to the base is the fallback showing through
    # rather than a translation, and must not be presented as one.
    if localized and base and localized.strip() == base.strip():
        return None, note
    return localized, note
