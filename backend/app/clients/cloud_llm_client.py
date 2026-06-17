import logging

from app.config import settings

logger = logging.getLogger(__name__)


class CloudLLMClient:
    """Cloud LLM for complex SFW intent parsing only.
    NEVER route NSFW content here — cloud APIs refuse it."""

    def __init__(self) -> None:
        self._api_key = settings.cloud_llm_api_key
        self._model = settings.cloud_llm_model

    async def chat(self, messages: list[dict], system: str = "") -> str:
        """Send messages and return response text."""
        raise NotImplementedError
