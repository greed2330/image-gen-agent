import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self) -> None:
        self._base = settings.ollama_base_url

    async def generate(self, model: str, prompt: str, system: str = "", **kwargs: Any) -> str:
        """Send a chat-completion request and return the response text."""
        raise NotImplementedError

    async def chat(self, model: str, messages: list[dict], **kwargs: Any) -> str:
        """Multi-turn chat. Returns assistant message text."""
        raise NotImplementedError

    async def unload(self, model: str) -> None:
        """Force-unload model from VRAM (keep_alive: 0).
        Must be called before loading a heavy image model — see VRAM safety rules."""
        logger.info("ollama unload: %s", model)
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self._base}/api/generate",
                json={"model": model, "keep_alive": 0},
                timeout=30,
            )

    async def embed(self, model: str, text: str) -> list[float]:
        """Return embedding vector."""
        raise NotImplementedError
