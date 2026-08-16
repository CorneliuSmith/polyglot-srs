"""Speech-to-text service — coverage, formats, and the provider call.

Two of these exist because the failure they guard is silent. A course
whose locale is guessed wrong doesn't error; it transcribes a learner into
a language they aren't speaking. And a recorder MIME type the matcher
doesn't recognise doesn't crash; it makes the microphone quietly stop
working on one browser.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services import stt
from backend.services.stt import (
    LOCALES,
    UNSUPPORTED,
    SttError,
    extension_for,
    locale_for,
    transcribe,
    transcription_available,
)
from backend.services.tts import VOICES


class FakeSettings:
    azure_speech_key = "key"
    azure_speech_region = "eastus"


class TestCoverage:
    def test_every_course_is_either_heard_or_explicitly_not(self):
        """No course may be missing by accident. A language absent from
        both maps is one nobody decided about — and the decision matters,
        because it is the difference between a microphone and a keyboard."""
        overlap = set(LOCALES) & set(UNSUPPORTED)
        assert not overlap, f"{overlap} is both supported and not"

    def test_the_unsupported_list_says_why(self):
        assert all(reason.strip() for reason in UNSUPPORTED.values())

    def test_listening_and_speaking_are_different_facts(self):
        """Not a subset either way, and the code must never infer one from
        the other. Hebrew and Persian can be heard and have no neural
        voice; Māori has a voice in the reader and cannot be heard."""
        assert {"he", "fa", "id", "tl"} <= set(LOCALES)
        assert {"he", "fa", "id", "tl"}.isdisjoint(VOICES)
        assert "mi" in UNSUPPORTED

    def test_locales_are_bcp_47(self):
        for code, locale in LOCALES.items():
            assert "-" in locale, f"{code} → {locale} is not a BCP-47 locale"

    def test_a_course_with_no_model_has_no_locale(self):
        assert locale_for("la") is None
        assert locale_for("es") == "es-ES"

    def test_the_variety_matches_the_voice_where_both_exist(self):
        """A learner should be heard in the variety they are spoken to in
        — pt-BR both ways, not pt-BR out and pt-PT back."""
        for code, locale in LOCALES.items():
            voice = VOICES.get(code)
            if voice:
                assert voice.startswith(locale + "-"), f"{code}: {voice} vs {locale}"


class TestRecorderFormats:
    def test_the_codec_parameter_does_not_break_the_match(self):
        """MediaRecorder reports 'audio/webm;codecs=opus', not 'audio/webm'.
        Matching on equality made Chrome's own recording unrecognisable."""
        assert extension_for("audio/webm;codecs=opus") == "webm"
        assert extension_for("AUDIO/WEBM") == "webm"

    def test_safari_records_mp4(self):
        """The one that is easy to miss: Safari has no WebM encoder, so
        every iPhone turn arrives as MP4/AAC."""
        assert extension_for("audio/mp4") == "mp4"
        assert extension_for("audio/mp4;codecs=mp4a.40.2") == "mp4"

    def test_anything_else_is_refused(self):
        assert extension_for("video/mp4") is None
        assert extension_for("application/octet-stream") is None
        assert extension_for(None) is None


class TestTranscribe:
    def _resp(self, payload, status=200):
        r = MagicMock()
        r.status_code = status
        r.json.return_value = payload
        r.text = json.dumps(payload)
        return r

    def _client(self, resp):
        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)
        return ctx, client

    async def test_it_sends_the_course_locale_and_returns_the_text(self):
        ctx, client = self._client(self._resp(
            {"combinedPhrases": [{"text": "Quiero un café"}]}))
        with patch("backend.config.get_settings", return_value=FakeSettings()), \
             patch("httpx.AsyncClient", return_value=ctx):
            text = await transcribe(b"audio", "es", "audio/webm;codecs=opus")
        assert text == "Quiero un café"
        definition = client.post.await_args.kwargs["files"]["definition"]
        assert json.loads(definition[1]) == {"locales": ["es-ES"]}

    async def test_it_falls_back_to_the_phrase_list(self):
        """A response shape that changed should not silently return ''."""
        ctx, _ = self._client(self._resp(
            {"combinedPhrases": [], "phrases": [{"text": "Hola"},
                                                {"text": "qué tal"}]}))
        with patch("backend.config.get_settings", return_value=FakeSettings()), \
             patch("httpx.AsyncClient", return_value=ctx):
            assert await transcribe(b"a", "es", "audio/webm") == "Hola qué tal"

    async def test_a_provider_error_is_an_stt_error(self):
        ctx, _ = self._client(self._resp({"error": "nope"}, status=429))
        with patch("backend.config.get_settings", return_value=FakeSettings()), \
             patch("httpx.AsyncClient", return_value=ctx):
            with pytest.raises(SttError):
                await transcribe(b"a", "es", "audio/webm")

    async def test_an_unheard_language_is_refused_before_any_call(self):
        with patch("backend.config.get_settings", return_value=FakeSettings()), \
             patch("httpx.AsyncClient") as http:
            with pytest.raises(ValueError, match="No speech recognition"):
                await transcribe(b"a", "la", "audio/webm")
        http.assert_not_called()

    async def test_an_unusable_format_is_refused_before_any_call(self):
        with patch("backend.config.get_settings", return_value=FakeSettings()), \
             patch("httpx.AsyncClient") as http:
            with pytest.raises(ValueError, match="Unsupported audio type"):
                await transcribe(b"a", "es", "video/mp4")
        http.assert_not_called()

    async def test_an_oversized_recording_is_refused_before_any_call(self):
        big = b"0" * (stt.MAX_AUDIO_BYTES + 1)
        with patch("backend.config.get_settings", return_value=FakeSettings()), \
             patch("httpx.AsyncClient") as http:
            with pytest.raises(ValueError, match="too long"):
                await transcribe(big, "es", "audio/webm")
        http.assert_not_called()


class TestAvailability:
    def test_no_key_means_no_microphone(self):
        """There is no keyless fallback the way TTS has edge-tts. Without
        the Azure key Speak is a typed feature and has to say so, rather
        than offering a button that fails on press."""
        class NoKey:
            azure_speech_key = ""

        with patch("backend.config.get_settings", return_value=NoKey()):
            assert transcription_available() is False
        with patch("backend.config.get_settings", return_value=FakeSettings()):
            assert transcription_available() is True
