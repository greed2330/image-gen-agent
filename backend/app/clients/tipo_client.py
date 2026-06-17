import logging

from app.config import settings

logger = logging.getLogger(__name__)


class TipoClient:
    """Wraps TIPO (KGen) for danbooru tag expansion.

    Receives seed tags from LLM and returns a fully expanded, co-occurrence-aware
    danbooru tag list. TIPO is trained on the same danbooru data as Illustrious/NoobAI,
    so no format translation is needed.

    Note: NSFW tag quality is unverified — must be tested in Phase 1/2.
    Ref: https://github.com/KohakuBlueleaf/KGen
    """

    def __init__(self) -> None:
        self._model_size = settings.tipo_model_size

    async def expand_tags(self, seed_tags: list[str], model_profile: str) -> list[str]:
        """Expand seed tags into a full danbooru prompt.

        Args:
            seed_tags: rough tags from LLM (e.g. ["1girl", "pink hair", "smile"])
            model_profile: "illustrious" / "noobai" uses tag mode; "chroma" uses NL mode
        Returns:
            Expanded tag list (pre-allowlist — allowlist runs after this)
        """
        raise NotImplementedError

    async def expand_natural_language(self, seed_tags: list[str]) -> str:
        """Natural-language mode for Chroma/Flux profiles."""
        raise NotImplementedError
