"""Tests for the /models chat-model compatibility filter."""
from app.api.routes_models import is_chat_compatible


def test_chat_models_are_compatible():
    assert is_chat_compatible("qwen3:14b")
    assert is_chat_compatible("huihui_ai/qwen3-abliterated:14b")
    assert is_chat_compatible("gemma4:12b")


def test_vision_and_embedding_models_rejected():
    # VL returns empty output for text-only intent JSON; embed cannot chat.
    assert not is_chat_compatible("huihui_ai/qwen3-vl-abliterated:8b")
    assert not is_chat_compatible("nomic-embed-text:latest")
