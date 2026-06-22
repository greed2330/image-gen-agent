"""Tests for IntentParser — LLM calls mocked."""
import pytest
from unittest.mock import AsyncMock

from app.models.schemas import GenRequest, NsfwLevel


@pytest.mark.asyncio
async def test_intent_parser_parses_valid_json():
    from app.pipeline.intent_parser import IntentParser

    ollama = AsyncMock()
    ollama.chat.return_value = (
        '{"subjects":["1girl"],"style":"anime","setting":null,"mood":"happy",'
        '"nsfw_level":0,"identity_tags":["1girl","pink hair","twintails"],"scene_tags":["smile","standing"],"workflow_hint":null}'
    )

    parser = IntentParser(ollama=ollama, cloud=AsyncMock(), memory=AsyncMock())
    result = await parser.parse(GenRequest(message="분홍 머리 소녀", chat_id="room1"))

    assert result.nsfw_level == NsfwLevel.SAFE
    assert "1girl" in result.seed_tags
    assert result.style == "anime"


@pytest.mark.asyncio
async def test_intent_parser_retries_on_bad_json():
    from app.pipeline.intent_parser import IntentParser

    ollama = AsyncMock()
    # First call returns garbage, second returns valid JSON
    ollama.chat.side_effect = [
        "Sorry, I cannot help with that.",
        '{"subjects":["1girl"],"style":null,"setting":null,"mood":null,'
        '"nsfw_level":0,"identity_tags":["1girl"],"scene_tags":[],"workflow_hint":null}',
    ]

    parser = IntentParser(ollama=ollama, cloud=AsyncMock(), memory=AsyncMock())
    result = await parser.parse(GenRequest(message="소녀 그림", chat_id="room1"))

    assert "1girl" in result.seed_tags
    assert ollama.chat.call_count == 2


@pytest.mark.asyncio
async def test_intent_parser_returns_minimal_on_total_failure():
    from app.pipeline.intent_parser import IntentParser

    ollama = AsyncMock()
    ollama.chat.return_value = "no json here at all"

    parser = IntentParser(ollama=ollama, cloud=AsyncMock(), memory=AsyncMock())
    result = await parser.parse(GenRequest(message="test", chat_id="room1"))

    # Should not raise — returns empty Intent
    assert result.seed_tags == []


@pytest.mark.asyncio
async def test_intent_parser_explicit_uses_abliterated():
    from app.pipeline.intent_parser import IntentParser
    from app.config import settings

    ollama = AsyncMock()
    # First call (main model): returns explicit
    # Second call (abliterated): returns better tags
    ollama.chat.side_effect = [
        '{"subjects":["1girl"],"style":"anime","setting":null,"mood":null,'
        '"nsfw_level":2,"identity_tags":["1girl","nude"],"scene_tags":[],"workflow_hint":null}',
        '{"subjects":["1girl"],"style":"anime","setting":null,"mood":null,'
        '"nsfw_level":2,"identity_tags":["1girl","nude"],"scene_tags":["lying"],"workflow_hint":null}',
    ]

    parser = IntentParser(ollama=ollama, cloud=AsyncMock(), memory=AsyncMock())
    result = await parser.parse(GenRequest(message="누드 소녀", chat_id="room1"))

    assert result.nsfw_level == NsfwLevel.EXPLICIT
    # Second call must use nsfw model
    second_call_model = ollama.chat.call_args_list[1][1]["model"]
    assert second_call_model == settings.llm_nsfw_model
