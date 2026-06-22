import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_MAX_TOKENS = 2048


class CloudLLMClient:
    """Cloud LLM for complex SFW intent parsing only.
    NEVER route NSFW content here — cloud APIs refuse it."""

    def __init__(self) -> None:
        self._api_key = settings.cloud_llm_api_key
        self._model = settings.cloud_llm_model

    async def chat(self, messages: list[dict], system: str = "") -> str:
        """Send messages and return response text."""
        if not self._api_key:
            raise RuntimeError("CLOUD_LLM_API_KEY not set — cloud LLM unavailable")
        logger.info("cloud LLM chat: model=%s, turns=%d", self._model, len(messages))
        payload: dict = {
            "model": self._model,
            "max_tokens": _MAX_TOKENS,
            "messages": messages,
        }
        if system:
            payload["system"] = system
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": _ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            resp.raise_for_status()
        return resp.json()["content"][0]["text"]
