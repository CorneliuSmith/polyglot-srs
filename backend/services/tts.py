"""Cached neural TTS (WP7a).

Browser speechSynthesis was the audio story and it was awful: robotic,
inconsistent across devices, and absent entirely for most languages on
mobile. This service synthesizes real neural audio per sentence/word —
generated once on first play, cached in the public 'tts' storage bucket,
served from the CDN forever after.

Provider: Microsoft Edge's neural TTS endpoint via edge-tts — keyless and
free, which fits the beta. The interface is one function; swapping in a
paid provider (Azure/Google/Polly) or local MMS for the uncovered
languages later changes nothing upstream.

Coverage (verified against the live voice list): 13 of 17 languages.
yo/ha/xh/mi have no voice here — the client keeps its browser-synthesis
fallback for those until the MMS phase (ROADMAP WP7b).
"""
from __future__ import annotations

import hashlib

# One voice per language, chosen for clarity at learner speed. ar-SA is the
# closest to MSA; pt-BR matches the app's Brazilian-leaning content.
VOICES: dict[str, str] = {
    "en": "en-US-JennyNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "it": "it-IT-ElsaNeural",
    "ca": "ca-ES-JoanaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ro": "ro-RO-AlinaNeural",
    "el": "el-GR-AthinaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "tr": "tr-TR-EmelNeural",
    "ar": "ar-SA-ZariyahNeural",
    "sw": "sw-KE-ZuriNeural",
}

# Slightly slower than native speed — these are learners.
RATE = "-10%"


def voice_for(language_code: str) -> str | None:
    return VOICES.get(language_code)


def cache_key(voice: str, text: str) -> str:
    """Deterministic storage key for one (voice, text) clip."""
    return hashlib.sha256(f"{voice}\x00{text}".encode()).hexdigest()[:40]


async def synthesize(text: str, language_code: str) -> bytes:
    """Render *text* to MP3 bytes with the language's voice.

    Raises ValueError for uncovered languages (callers gate on voice_for
    first) and RuntimeError when the provider returns no audio.
    """
    import edge_tts

    voice = voice_for(language_code)
    if voice is None:
        raise ValueError(f"No TTS voice for language '{language_code}'")

    communicate = edge_tts.Communicate(text, voice, rate=RATE)
    chunks: list[bytes] = []
    async for message in communicate.stream():
        if message["type"] == "audio":
            chunks.append(message["data"])
    audio = b"".join(chunks)
    if not audio:
        raise RuntimeError("TTS provider returned no audio")
    return audio
