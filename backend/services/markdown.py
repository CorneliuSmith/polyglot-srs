"""Card markdown — what a grammar explanation may carry, on the way in.

Since 4 Sep 2026 explanations, culture notes and function notes render as
markdown when they carry markdown syntax (`components/ExplanationView.tsx`
routes a block with bold, lists, tables, code or links through
react-markdown + rehype-sanitize; plain blocks keep the typesetter). The
client's sanitiser is the last line; this is the first, because the column
is written by the editor, the seeders and the AI, and a defect that gets
into the row is served to every learner until someone notices.

What is removed:

- raw HTML tags. Markdown allows inline HTML; the renderer never parses it
  (no rehype-raw), so a tag would print literally — but a literal
  `<script>` on a card is still wrong, and stripping here keeps the column
  readable by anything that is not the sanitising renderer.
- link and image destinations on a scheme other than http(s). The text
  stays; the destination goes.

What is NOT touched: the markdown itself. Bold, lists, tables and code are
the point. The corpus in data/ carries none of it today
(tests/test_content_markdown_guard.py keeps it that way for the seed), so
this matters for contributor-written rows.
"""
from __future__ import annotations

import re

_TAG = re.compile(r"</?[a-zA-Z][^<>]*>")
# [text](dest) and ![alt](dest) whose destination is not http(s), a
# fragment or a relative path — javascript:, data:, vbscript: and friends.
# The destination may carry one level of balanced parentheses
# (javascript:alert(1)), as CommonMark allows.
_BAD_LINK = re.compile(
    r"!?\[([^\]]*)\]\(\s*(?!https?://|#|/|\.)[a-zA-Z][a-zA-Z0-9+.-]*:"
    r"(?:[^()\s]|\([^()]*\))*\)"
)


def clean_markdown(text: str | None) -> str | None:
    """The text with raw HTML tags removed and unsafe link destinations
    dropped (their text kept). None and empty strings pass through."""
    if text is None:
        return None
    out = _TAG.sub("", text)
    out = _BAD_LINK.sub(lambda m: m.group(1), out)
    return out
