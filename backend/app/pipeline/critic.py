import logging

from app.clients.ollama_client import OllamaClient
from app.models.schemas import Critique

logger = logging.getLogger(__name__)


class Critic:
    """⑥ Self-evaluation loop using vision model (qwen3-vl-abliterated).

    Checks generated image for anatomy errors, composition issues, etc.
    Returns Critique with pass/fail and retry decision.
    Uses abliterated VL model so NSFW output can be evaluated without refusal.
    """

    def __init__(self, ollama: OllamaClient) -> None:
        self._ollama = ollama

    async def evaluate(self, image_path: str, prompt_context: dict) -> Critique:
        # Phase 3: VL-based evaluation not yet implemented — always pass
        logger.info("critic: Phase 3 stub — skipping evaluation for %s", image_path)
        return Critique(passed=True)
