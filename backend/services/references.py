"""Reference-link validation shared by the grammar seeder, contributor API,
and curriculum generator.

References (external readings/sources shown in the grammar panel) are user-
or model-supplied, so they must be sanitized. Two shapes are allowed:

  - online:  {title, url}          — http(s) URLs only, so javascript: and
                                     data: URLs never reach the frontend
  - offline: {title, book[, page]} — a printed source; no URL at all

Titles/URLs/book names are length-bounded and the list is capped.
"""
from __future__ import annotations

MAX_REFERENCES = 10
MAX_TITLE_LEN = 200
MAX_URL_LEN = 500
MAX_BOOK_LEN = 200
MAX_PAGE_LEN = 40


def clean_references(refs) -> list[dict]:
    """Return a sanitized list of online ({title, url}) and offline
    ({title, book[, page]}) reference entries."""
    out: list[dict] = []
    if not isinstance(refs, list):
        return out
    for r in refs:
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        book = (r.get("book") or "").strip()
        if not title:
            continue
        if url:
            if not (url.startswith("http://") or url.startswith("https://")):
                continue
            out.append({"title": title[:MAX_TITLE_LEN], "url": url[:MAX_URL_LEN]})
        elif book:
            entry = {"title": title[:MAX_TITLE_LEN], "book": book[:MAX_BOOK_LEN]}
            page = str(r.get("page") or "").strip()
            if page:
                entry["page"] = page[:MAX_PAGE_LEN]
            out.append(entry)
        else:
            continue
        if len(out) >= MAX_REFERENCES:
            break
    return out


def reference_key(ref: dict) -> str:
    """The stable key read-tracking uses for one reference entry."""
    return ref.get("url") or ref.get("title") or ""


MAX_RELATED = 6
MAX_CONTRAST_LEN = 200


def clean_related(entries) -> list[dict]:
    """Sanitize authored Related entries: {title, contrast?}.

    *title* names another grammar point in the same language; the API resolves
    it to an id (and the learner's stage) at read time, so an entry whose title
    doesn't resolve simply doesn't render — never an error.
    """
    out: list[dict] = []
    if not isinstance(entries, list):
        return out
    for r in entries:
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or "").strip()
        if not title:
            continue
        entry = {"title": title[:MAX_TITLE_LEN]}
        contrast = (r.get("contrast") or "").strip()
        if contrast:
            entry["contrast"] = contrast[:MAX_CONTRAST_LEN]
        out.append(entry)
        if len(out) >= MAX_RELATED:
            break
    return out
