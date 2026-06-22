"""Tests for OllamaClient and ComfyUIClient — all external calls mocked."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# --- OllamaClient ---

@pytest.mark.asyncio
async def test_ollama_generate_returns_response():
    from app.clients.ollama_client import OllamaClient

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "hello world"}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        client = OllamaClient()
        result = await client.generate("qwen3:14b", "test prompt")

    assert result == "hello world"


@pytest.mark.asyncio
async def test_ollama_chat_returns_content():
    from app.clients.ollama_client import OllamaClient

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"message": {"content": "assistant reply"}}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        client = OllamaClient()
        result = await client.chat("qwen3:14b", [{"role": "user", "content": "hi"}])

    assert result == "assistant reply"


@pytest.mark.asyncio
async def test_ollama_embed_returns_vector():
    from app.clients.ollama_client import OllamaClient

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        client = OllamaClient()
        result = await client.embed("nomic-embed-text", "test")

    assert result == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_ollama_unload_calls_keep_alive_zero():
    from app.clients.ollama_client import OllamaClient

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    post_mock = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = post_mock
        client = OllamaClient()
        await client.unload("qwen3:14b")

    call_kwargs = post_mock.call_args
    assert call_kwargs[1]["json"]["keep_alive"] == 0


@pytest.mark.asyncio
async def test_ollama_list_models_returns_names():
    from app.clients.ollama_client import OllamaClient

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "models": [
            {"name": "qwen3:14b"},
            {"name": "qwen3:4b"},
            {"name": "nomic-embed-text"},
        ]
    }

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        client = OllamaClient()
        result = await client.list_models()

    assert result == ["qwen3:14b", "qwen3:4b", "nomic-embed-text"]


# --- ComfyUIClient ---

@pytest.mark.asyncio
async def test_comfyui_submit_returns_prompt_id():
    from app.clients.comfyui_client import ComfyUIClient

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"prompt_id": "abc-123"}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        client = ComfyUIClient()
        result = await client.submit({"3": {"class_type": "KSampler"}})

    assert result == "abc-123"


@pytest.mark.asyncio
async def test_comfyui_free_posts_to_free_endpoint():
    from app.clients.comfyui_client import ComfyUIClient

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    post_mock = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = post_mock
        client = ComfyUIClient()
        await client.free()

    call_kwargs = post_mock.call_args
    assert call_kwargs[1]["json"]["unload_models"] is True
    assert call_kwargs[1]["json"]["free_memory"] is True


@pytest.mark.asyncio
async def test_comfyui_wait_result_returns_path():
    from app.clients.comfyui_client import ComfyUIClient

    history_resp = MagicMock()
    history_resp.raise_for_status = MagicMock()
    history_resp.json.return_value = {
        "abc-123": {
            "outputs": {
                "9": {"images": [{"filename": "output_00001_.png", "subfolder": "", "type": "output"}]}
            }
        }
    }

    with patch("httpx.AsyncClient") as MockClient:
        with patch("asyncio.sleep", new_callable=AsyncMock):
            MockClient.return_value.__aenter__.return_value.get = AsyncMock(return_value=history_resp)
            client = ComfyUIClient()
            result = await client.wait_result("abc-123")

    assert "output_00001_.png" in result
