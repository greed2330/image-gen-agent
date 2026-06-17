import logging

from app.clients.ollama_client import OllamaClient
from app.clients.cloud_llm_client import CloudLLMClient
from app.models.schemas import GenRequest, Intent, NsfwLevel
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)


class IntentParser:
    """① Korean natural language → Intent JSON (seed tags only).

    Routing logic:
    - SAFE: qwen3:14b (or cloud for complex requests)
    - SUGGESTIVE/EXPLICIT: qwen3:14b parses SFW structure (clinical framing),
      abliterated handles NSFW element extraction
    The abliterated model never reads raw Korean chat — it receives structured input only.
    Ref: docs/설계문서/07 §1-A
    """

    def __init__(
        self,
        ollama: OllamaClient,
        cloud: CloudLLMClient,
        memory: MemoryService,
    ) -> None:
        self._ollama = ollama
        self._cloud = cloud
        self._memory = memory

    async def parse(self, request: GenRequest) -> Intent:
        """Parse user message into Intent with rough seed_tags."""
        raise NotImplementedError
