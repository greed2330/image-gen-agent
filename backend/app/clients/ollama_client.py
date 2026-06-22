import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT_GENERATE = 180  # local LLM can be slow on first token
_TIMEOUT_EMBED = 30


class OllamaClient:
    def __init__(self) -> None:
        self._base = settings.ollama_base_url

    async def generate(self, model: str, prompt: str, system: str = "", **kwargs: Any) -> str:
        """Send a generate request and return the response text."""
        logger.info("ollama generate: model=%s", model)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/api/generate",
                json={"model": model, "prompt": prompt, "system": system, "stream": False, **kwargs},
                timeout=_TIMEOUT_GENERATE,
            )
            resp.raise_for_status()
            return resp.json()["response"]

    async def chat(self, model: str, messages: list[dict], system: str = "", **kwargs: Any) -> str:
        """Multi-turn chat. Returns assistant message text.

        system: prepended as role='system' message (standard for /api/chat).
        """
        full_messages = ([{"role": "system", "content": system}] + messages) if system else messages
        logger.info("ollama chat: model=%s, turns=%d", model, len(full_messages))
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/api/chat",
                json={"model": model, "messages": full_messages, "stream": False, **kwargs},
                timeout=_TIMEOUT_GENERATE,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def unload(self, model: str) -> None:
        """Force-unload model from VRAM (keep_alive: 0).
        Must be called before loading a heavy image model — see VRAM safety rules."""
        logger.info("VRAM: ollama unload model=%s", model)
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self._base}/api/generate",
                json={"model": model, "keep_alive": 0},
                timeout=30,
            )

    async def list_models(self) -> list[str]:
        """Return installed model names from ollama (GET /api/tags)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._base}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
        return [m["name"] for m in data.get("models", [])]

    async def embed(self, model: str, text: str) -> list[float]:
        """Return embedding vector."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/api/embed",
                json={"model": model, "input": text},
                timeout=_TIMEOUT_EMBED,
            )
            resp.raise_for_status()
            return resp.json()["embeddings"][0]
