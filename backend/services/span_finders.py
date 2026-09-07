"""Which languages find a word in a sentence by something other than the
default regex — one registry, used by every consumer of `make_cloze`.

The card (`repositories/cards.py`), the audit (`quality/audit_content.py`),
the authored-sentence gate (`scripts/apply_authored_sentences.py`) and the
prune each used to keep their own `{"th": ...}` dict, which is how a
language added to one of them would silently stay on the regex in the
others (quality rule 13: follow a layer end to end). Imports are lazy: the
audit is the every-commit gate and must not pay for the Thai lexicon on a
course that never needs it.

- `th` — no spaces, so a boundary is not a character; segmentation finds
  the word (CHECKS §29).
- `tr` — Python's IGNORECASE folds dotless `ı` onto `i` (with `İ`, `ſ` and
  the Kelvin sign, the four non-ASCII letters the docs warn about), so the
  regex blanked `mı` in "Var mı?" for the `mi` card and would carve `sik`
  out of a sentence for `sık`. Turkish casing keeps the two letters apart.
"""
from __future__ import annotations

from collections.abc import Callable

SpanFinder = Callable[[str, str], "tuple[int, int] | None"]


def span_finder(code: str | None) -> SpanFinder | None:
    """The finder for *code*, or None for "use the regex"."""
    if code == "th":
        from backend.services.nlp.thai import answer_span
        return answer_span
    if code == "tr":
        from backend.services.nlp.turkish import answer_span
        return answer_span
    return None
