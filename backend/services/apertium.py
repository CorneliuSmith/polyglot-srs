"""Optional Apertium morphological analysis for the generation checker (WP42).

When a language has no local NLP backend (many low-resource ones), the vocab
example checker can only do a whole-word surface match — an *inflected* form of
the target word gets rejected, which drags accept-rates down on exactly the
languages the paid pipeline is meant to fill. If `APERTIUM_API_URL` points at an
Apertium-APy server (public https://apertium.org/apy or self-hosted), we instead
ask Apertium to analyze each token and accept the sentence when a token's
analysis lemma matches the target word.

Entirely opt-in and fail-safe: unset = disabled, and any network/parse/config
error returns "no lemmas found" so the checker simply falls back to the surface
match — Apertium can never *block* generation, only *rescue* an inflected form.
"""

from __future__ import annotations

import httpx

from backend.config import get_settings

# Our (mostly ISO 639-1) language codes -> the Apertium analyzer mode to call.
# Only languages Apertium actually ships an analyzer for are worth mapping; an
# unmapped language skips Apertium and stays on the surface match. Extend this
# as you install more APy modes (a self-hosted APy lists them at /listPairs).
_APERTIUM_MODES: dict[str, str] = {
    "ar": "ara",
    "sw": "swa",
    "es": "spa",
    "fr": "fra",
    "it": "ita",
    "pt": "por",
    "ro": "ron",
    "ca": "cat",
}

_TIMEOUT_SECONDS = 8.0


def apertium_available(language_code: str) -> bool:
    """True if Apertium is configured AND has a mode for this language."""
    if language_code not in _APERTIUM_MODES:
        return False
    try:
        settings = get_settings()
    except Exception:
        return False
    return bool(getattr(settings, "apertium_api_url", ""))


def _lemmas_from_analysis(analysis: str) -> set[str]:
    """Pull lemmas out of one Apertium `analyze` string.

    Examples:
      'corre/correr<vblex><pri><p3><sg>'      -> {'correr'}
      'casa/casa<n><f><sg>/casar<vblex><...>' -> {'casa', 'casar'}
      'xyz/*xyz'  (unknown word)              -> {}   (no valid reading)
      'Kwa'       (no analysis at all)        -> {}
    """
    if "/" not in analysis:
        return set()
    _surface, *readings = analysis.split("/")
    out: set[str] = set()
    for reading in readings:
        reading = reading.strip()
        if not reading or reading.startswith("*"):  # '*' marks an unknown token
            continue
        lemma = reading.split("<", 1)[0].strip().lower()
        if lemma:
            out.add(lemma)
    return out


async def analyze_lemmas(language_code: str, text: str) -> set[str]:
    """Every lemma Apertium finds in *text*. Empty set on any failure or when
    Apertium isn't configured for this language (so callers can treat an empty
    result as 'no help available' and fall back)."""
    if not apertium_available(language_code):
        return set()
    settings = get_settings()
    base = settings.apertium_api_url.rstrip("/")
    mode = _APERTIUM_MODES[language_code]
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.get(
                f"{base}/analyze", params={"lang": mode, "q": text}
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return set()
    # APy /analyze returns [[analysis, input_token], ...].
    lemmas: set[str] = set()
    if isinstance(data, list):
        for item in data:
            if isinstance(item, (list, tuple)) and item:
                lemmas |= _lemmas_from_analysis(str(item[0]))
    return lemmas
