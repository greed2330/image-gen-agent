import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def _make_mem0_config() -> dict:
    return {
        "vector_store": {
            "provider": "qdrant",
            "config": {"url": settings.qdrant_url},
        },
        "llm": {
            "provider": "ollama",
            "config": {
                "model": settings.llm_main_model,
                "ollama_base_url": settings.ollama_base_url,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": settings.llm_embed_model,
                "ollama_base_url": settings.ollama_base_url,
            },
        },
    }


class MemoryService:
    """mem0 wrapper. Stores per-chat-room user preferences and generation history.

    Backed by local Qdrant + nomic-embed-text.
    Lazy-initialised: _mem is None until first use (Qdrant may not be running at startup).
    """

    def __init__(self) -> None:
        self._mem: Any = None

    def _get_mem(self) -> Any:
        if self._mem is None:
            from mem0 import Memory
            self._mem = Memory.from_config(_make_mem0_config())
            logger.info("mem0 initialised")
        return self._mem

    async def add(self, chat_id: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Store a memory entry for chat_id."""
        meta = {"chat_id": chat_id, **(metadata or {})}
        self._get_mem().add(content, user_id=chat_id, metadata=meta)
        logger.info("memory add: chat_id=%s", chat_id)

    async def search(self, chat_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Retrieve relevant memories for a query."""
        results = self._get_mem().search(query, user_id=chat_id, limit=top_k)
        return results.get("results", []) if isinstance(results, dict) else results

    async def get_all(self, chat_id: str) -> list[dict[str, Any]]:
        """Return all memories for chat_id."""
        results = self._get_mem().get_all(user_id=chat_id)
        return results.get("results", []) if isinstance(results, dict) else results
