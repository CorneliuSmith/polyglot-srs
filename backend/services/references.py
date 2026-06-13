"""Reference-link validation shared by the grammar seeder, contributor API,
and curriculum generator.

Reference links (external readings/sources shown in the grammar panel) are
user- or model-supplied, so they must be sanitized: only http(s) URLs are
kept, titles/URLs are length-bounded, and the list is capped. This blocks
javascript: and data: URLs from ever reaching the frontend.
"""
from __future__ import annotations

MAX_REFERENCES = 10
MAX_TITLE_LEN = 200
MAX_URL_LEN = 500


def clean_references(refs) -> list[dict]:
    """Return a sanitized list of {title, url} entries (http/https only)."""
    out: list[dict] = []
    if not isinstance(refs, list):
        return out
    for r in refs:
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        if not title or not url:
            continue
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        out.append({"title": title[:MAX_TITLE_LEN], "url": url[:MAX_URL_LEN]})
        if len(out) >= MAX_REFERENCES:
            break
    return out
