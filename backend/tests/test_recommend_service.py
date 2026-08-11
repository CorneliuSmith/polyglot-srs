"""generate_recommendations: the model call, its schema, and its fallback.

The router had tests; the service that actually talks to the API did not,
which is how recommendations shipped with a schema the API rejects and
nobody noticed for weeks. These cover the call itself.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from anthropic import BadRequestError

from backend.services import recommend as reco

PICKS = {"picks": [{
    "type": "book", "title": "Cien años de soledad", "creator": "GGM",
    "year": "1967", "blurb": "A classic.", "why": "Matches your history bent.",
    "level": "B2", "genre": "magical realism",
}]}


class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Resp:
    def __init__(self, text):
        self.content = [_TextBlock(text)]
        self.usage = None


class _Settings:
    tutor_dev_mock = False
    anthropic_api_key = "sk-test"
    tutor_model = "claude-sonnet-5"
    tutor_summary_model = "claude-sonnet-5"
    tutor_model_low_resource = "claude-opus-4-8"


def _bad_request(message: str) -> BadRequestError:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(400, request=request, json={
        "type": "error",
        "error": {"type": "invalid_request_error", "message": message},
    })
    return BadRequestError(message, response=response, body=None)


async def _generate(create):
    client = AsyncMock()
    client.messages.create = create
    with patch.object(reco, "AsyncAnthropic", return_value=client), \
         patch.object(reco, "get_settings", return_value=_Settings()):
        picks = await reco.generate_recommendations(
            language_name="Spanish", language_code="es", level="B1",
            learned_count=300, about="history", genres=["History"],
            media_types=["book"],
        )
    return picks, client


class TestSchemaCall:
    @pytest.mark.asyncio
    async def test_asks_for_the_schema_and_returns_the_picks(self):
        create = AsyncMock(return_value=_Resp(json.dumps(PICKS)))
        picks, _ = await _generate(create)
        assert picks[0]["title"] == "Cien años de soledad"
        sent = create.await_args.kwargs["output_config"]["format"]["schema"]
        assert sent is reco._RECO_SCHEMA


class TestPlainJsonFallback:
    """A schema the API won't take must not be the end of the feature —
    that is precisely how this stayed broken through three fixes."""

    @pytest.mark.asyncio
    async def test_retries_without_the_schema_when_it_is_rejected(self):
        create = AsyncMock(side_effect=[
            _bad_request("output_config.format.schema: bad schema"),
            _Resp(json.dumps(PICKS)),
        ])
        picks, _ = await _generate(create)
        assert picks[0]["title"] == "Cien años de soledad"
        assert create.await_count == 2
        # The retry carries no schema, and says what shape to answer in.
        retry = create.await_args.kwargs
        assert "output_config" not in retry
        assert '"picks"' in retry["system"]

    @pytest.mark.asyncio
    async def test_the_fallback_survives_a_fenced_reply(self):
        create = AsyncMock(side_effect=[
            _bad_request("bad schema"),
            _Resp("```json\n" + json.dumps(PICKS) + "\n```"),
        ])
        picks, _ = await _generate(create)
        assert picks[0]["type"] == "book"

    @pytest.mark.asyncio
    async def test_the_fallback_survives_a_sentence_before_the_json(self):
        create = AsyncMock(side_effect=[
            _bad_request("bad schema"),
            _Resp("Here are the picks:\n" + json.dumps(PICKS)),
        ])
        picks, _ = await _generate(create)
        assert picks[0]["level"] == "B2"

    @pytest.mark.asyncio
    async def test_a_non_schema_error_still_propagates(self):
        # An exhausted key or an unknown model is a real failure the draft
        # must report, not paper over with a second call.
        create = AsyncMock(side_effect=RuntimeError("provider down"))
        with pytest.raises(RuntimeError):
            await _generate(create)


class TestParsePicks:
    def test_unparseable_text_yields_nothing_rather_than_raising(self):
        assert reco._parse_picks("not json at all") == []

    def test_non_dict_entries_are_dropped(self):
        assert reco._parse_picks('{"picks": ["nope", {"title": "ok"}]}') == [
            {"title": "ok"}
        ]
