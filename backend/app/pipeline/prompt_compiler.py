import logging

from app.clients.ollama_client import OllamaClient
from app.clients.tipo_client import TipoClient
from app.models.schemas import CompiledPrompt, Intent, ModelProfile, RouteDecision
from app.services.tag_allowlist import TagAllowlist

logger = logging.getLogger(__name__)


class PromptCompiler:
    """③ Compile seed tags into a final danbooru prompt via TIPO + allowlist.

    Pipeline (§1-A in doc 07):
      LLM seed_tags → [TIPO expansion] → [allowlist validation] → CompiledPrompt

    - SDXL profiles (illustrious/noobai): TIPO tag mode
    - Chroma profile: TIPO natural-language mode
    - Quality tokens and negative tags are appended from model preset config.
    """

    def __init__(
        self,
        ollama: OllamaClient,
        tipo: TipoClient,
        allowlist: TagAllowlist,
    ) -> None:
        self._ollama = ollama
        self._tipo = tipo
        self._allowlist = allowlist

    async def compile(self, intent: Intent, route: RouteDecision) -> CompiledPrompt:
        raise NotImplementedError
