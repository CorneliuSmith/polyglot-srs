"""Speech-to-text for Speak (docs/plans/speak.md, stage 2).

Azure's **fast transcription** endpoint, on the key and region the app
already uses for neural TTS — `azure_speech_key` / `azure_speech_region`.
No new vendor, no new secret, and the resource is already in production.
See docs/plans/speak-speech.md for why this tier and not real-time
streaming: batch is a fifth of the price, and a turn the learner
deliberately ended can afford two seconds.

Two things this module is deliberately strict about.

**Coverage is a per-course fact, not a guess.** Azure transcribes far
fewer languages than the app teaches, and a course with no model must
fall back to typing permanently rather than mis-hearing a beginner into
nonsense. `LOCALES` below is the allowlist; anything absent has no
microphone, and the UI says so. It is deliberately narrower than
`tts.VOICES` in one direction and wider in another — Speak can listen to
Hebrew, Persian, Indonesian and Filipino, which have no neural voice
here, and cannot listen to Jamaican Patois, Latin, Māori, Xhosa, Yoruba
or Hausa, which is most of what the voice list is missing too.

**The audio is never kept.** It arrives, it is transcribed, it is
discarded — it is not written to storage, not logged, and not held
beyond the request. Recordings of someone's voice are biometric data and
this app has no business storing them to save a re-record.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger("stt")

# The BCP-47 locale Azure wants, per course code. Chosen to match the TTS
# voice's locale where one exists (es-ES, pt-BR, ar-SA) so a learner hears
# and is heard in the same variety.
#
# VERIFY BEFORE ADDING: Azure's supported-language list moves, and the cost
# of an optimistic entry is a learner talking into a microphone that
# transcribes them into a language they aren't speaking. The list below is
# the conservative set; the absent courses are listed in UNSUPPORTED so the
# omission reads as a decision rather than an oversight.
LOCALES: dict[str, str] = {
    "en": "en-US",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "it": "it-IT",
    "ca": "ca-ES",
    "pt": "pt-BR",
    "ro": "ro-RO",
    "el": "el-GR",
    "ru": "ru-RU",
    "tr": "tr-TR",
    "ar": "ar-SA",
    "sw": "sw-KE",
    "hi": "hi-IN",
    "nl": "nl-NL",
    "th": "th-TH",
    "ko": "ko-KR",
    "he": "he-IL",
    "fa": "fa-IR",
    "id": "id-ID",
    "tl": "fil-PH",
}

# Courses with no speech recognition, and why. These keep the typed path
# for good — not as a stopgap, and the UI should say "type your turn"
# rather than showing a microphone that cannot work.
UNSUPPORTED: dict[str, str] = {
    "jam": "no Azure model for Jamaican Patois",
    "la": "no Azure model for Latin (no living speaker corpus)",
    "mi": "no Azure model for Māori",
    "xh": "no Azure model for Xhosa",
    "yo": "no Azure model for Yoruba",
    "ha": "no Azure model for Hausa",
}

# What MediaRecorder actually produces, and what we let through. Chrome and
# Firefox record WebM/Opus; Safari records MP4/AAC. Azure's fast
# transcription accepts both, but the browser sends its own codec string
# ("audio/webm;codecs=opus"), so match on the prefix rather than equality.
CONTENT_TYPES: dict[str, str] = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
}

# A turn, not a lecture. Two minutes of Opus is well under this; the cap is
# here so a mis-wired client cannot post a podcast.
MAX_AUDIO_BYTES = 8 * 1024 * 1024


class SttError(RuntimeError):
    """Transcription failed. The caller falls back to typing."""


def locale_for(language_code: str) -> str | None:
    """The Azure locale for a course, or None when it cannot be heard."""
    return LOCALES.get(language_code)


def extension_for(content_type: str | None) -> str | None:
    """The file extension for a recorder's MIME type, or None if unusable.

    Browsers append codec parameters — "audio/webm;codecs=opus" — so the
    type is matched on its base only.
    """
    base = (content_type or "").split(";")[0].strip().lower()
    return CONTENT_TYPES.get(base)


def transcription_available() -> bool:
    """Whether this server can hear anything at all.

    Unlike TTS there is no keyless fallback: edge-tts has no transcription
    twin, and inventing one locally would be a different product. Without
    the Azure key, Speak is a typed feature and says so.
    """
    from backend.config import get_settings

    settings = get_settings()
    return bool(getattr(settings, "azure_speech_key", ""))


async def transcribe(
    audio: bytes, language_code: str, content_type: str | None = None
) -> str:
    """Transcribe one recorded turn. Returns the text, keeps nothing.

    Raises ValueError for a course with no model or an audio type we don't
    accept — both are caller bugs the UI should have prevented — and
    SttError for anything the provider does, which is a fallback-to-typing
    condition rather than a failed session.
    """
    locale = locale_for(language_code)
    if locale is None:
        raise ValueError(f"No speech recognition for language '{language_code}'")
    extension = extension_for(content_type)
    if extension is None:
        raise ValueError(f"Unsupported audio type '{content_type}'")
    if not audio:
        raise ValueError("Empty recording")
    if len(audio) > MAX_AUDIO_BYTES:
        raise ValueError("Recording too long")

    from backend.config import get_settings

    settings = get_settings()
    key = getattr(settings, "azure_speech_key", "")
    if not key:
        raise SttError("No speech provider configured")
    region = getattr(settings, "azure_speech_region", "eastus")

    import httpx

    # The fast-transcription API takes the audio and a JSON "definition" as
    # one multipart body and answers with the whole transcript, rather than
    # the streaming protocol's socket. One request, one answer, no session
    # to keep alive across a flaky mobile connection.
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"https://{region}.api.cognitive.microsoft.com"
            "/speechtotext/transcriptions:transcribe?api-version=2024-11-15",
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "User-Agent": "PolyglotSRS",
            },
            files={
                "audio": (f"turn.{extension}", audio,
                          (content_type or "application/octet-stream")
                          .split(";")[0]),
                "definition": (
                    None,
                    json.dumps({"locales": [locale]}),
                    "application/json",
                ),
            },
        )
    if resp.status_code != 200:
        raise SttError(f"Azure STT {resp.status_code}: {resp.text[:160]}")
    try:
        data = resp.json()
    except ValueError as exc:
        raise SttError("Azure STT returned no JSON") from exc

    # combinedPhrases is the whole utterance already joined; phrases is the
    # per-segment breakdown. Prefer the former and fall back to stitching,
    # because a response shape that changed shouldn't silently return "".
    combined = data.get("combinedPhrases") or []
    text = " ".join(
        (p.get("text") or "").strip() for p in combined
    ).strip()
    if not text:
        text = " ".join(
            (p.get("text") or "").strip() for p in (data.get("phrases") or [])
        ).strip()
    return text
