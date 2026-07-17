"""Cached neural TTS (WP7a).

Browser speechSynthesis was the audio story and it was awful: robotic,
inconsistent across devices, and absent entirely for most languages on
mobile. This service synthesizes real neural audio per sentence/word —
generated once on first play, cached in the public 'tts' storage bucket,
served from the CDN forever after.

Providers: Azure Speech (keyed, official — REQUIRED in production, since
Microsoft rejects the keyless edge-tts endpoint from datacenter IPs) with
edge-tts as the keyless fallback for local dev. Same neural voices either
way; the interface is one function, so adding MMS for the uncovered
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
    "hi": "hi-IN-SwaraNeural",
    # No neural voice exists for Jamaican Patois; jam is intentionally absent.
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

    Provider chain (beta lesson 2026-07-16: Microsoft rejects edge-tts's
    keyless endpoint from datacenter IPs — it works from a laptop and
    fails from DigitalOcean, so prod audio silently fell back to the
    browser voice):
      1. Azure Speech (official API, same voices) when AZURE_SPEECH_KEY
         is set — this is the production path.
      2. edge-tts otherwise — local dev, residential IPs.

    Raises ValueError for uncovered languages (callers gate on voice_for
    first) and RuntimeError when the provider returns no audio.
    """
    voice = voice_for(language_code)
    if voice is None:
        raise ValueError(f"No TTS voice for language '{language_code}'")

    from backend.config import get_settings

    settings = get_settings()
    if getattr(settings, "azure_speech_key", ""):
        return await _synthesize_azure(
            text, voice,
            settings.azure_speech_key,
            getattr(settings, "azure_speech_region", "eastus"),
        )
    return await _synthesize_edge(text, voice)


async def _synthesize_azure(
    text: str, voice: str, key: str, region: str
) -> bytes:
    """Azure Cognitive Services Speech — the exact same neural voices as
    edge-tts, through the keyed API that datacenters may actually use."""
    from xml.sax.saxutils import escape

    import httpx

    # Voice names carry their locale prefix: en-US-JennyNeural → en-US.
    lang = "-".join(voice.split("-")[:2])
    ssml = (
        f"<speak version='1.0' xml:lang='{lang}'>"
        f"<voice name='{voice}'>"
        f"<prosody rate='{RATE}'>{escape(text)}</prosody>"
        f"</voice></speak>"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                "User-Agent": "PolyglotSRS",
            },
            content=ssml.encode(),
        )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Azure TTS {resp.status_code}: {resp.text[:120]}"
        )
    if not resp.content:
        raise RuntimeError("Azure TTS returned no audio")
    return resp.content


async def _synthesize_edge(text: str, voice: str) -> bytes:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=RATE)
    chunks: list[bytes] = []
    async for message in communicate.stream():
        if message["type"] == "audio":
            chunks.append(message["data"])
    audio = b"".join(chunks)
    if not audio:
        raise RuntimeError("TTS provider returned no audio")
    return audio
