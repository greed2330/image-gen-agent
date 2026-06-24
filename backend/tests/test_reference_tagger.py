"""Tests for ReferenceTagger (VL call mocked)."""
import pytest
from unittest.mock import AsyncMock

from app.services.reference_tagger import ReferenceTagger, _parse_tags


def test_parse_tags_cleans_and_dedups():
    raw = 'white hair, red eyes ,white hair,\nkemonomimi, "tiger tail", '
    assert _parse_tags(raw) == ["white hair", "red eyes", "kemonomimi", "tiger tail"]


@pytest.mark.asyncio
async def test_extract_returns_parsed_tags():
    ollama = AsyncMock()
    ollama.chat.return_value = "white hair, red eyes, animal ears, tiger ears, tiger tail, kemonomimi"
    tagger = ReferenceTagger(ollama=ollama)

    tags = await tagger.extract("base64data")
    assert "tiger ears" in tags and "white hair" in tags
    # VL model used with an image payload
    _, kwargs = ollama.chat.call_args
    assert kwargs["messages"][0]["images"] == ["base64data"]


@pytest.mark.asyncio
async def test_extract_returns_empty_on_failure():
    ollama = AsyncMock()
    ollama.chat.side_effect = RuntimeError("vl down")
    tagger = ReferenceTagger(ollama=ollama)
    assert await tagger.extract("x") == []
