import logging
from typing import Any

logger = logging.getLogger(__name__)


class MemoryService:
    """mem0 wrapper. Stores per-chat-room user preferences and generation history.

    Backed by local Qdrant + nomic-embed-text.
    Ref: docs/설계문서/04-메모리-전략.md
    """

    async def add(self, chat_id: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Store a memory entry for chat_id."""
        raise NotImplementedError

    async def search(self, chat_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Retrieve relevant memories for a query."""
        raise NotImplementedError

    async def get_all(self, chat_id: str) -> list[dict[str, Any]]:
        """Return all memories for chat_id."""
        raise NotImplementedError
