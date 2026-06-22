import asyncio
import logging
from functools import partial

from app.config import settings

logger = logging.getLogger(__name__)

# Tags that TIPO injects from danbooru distribution but harm uncensored output.
# Move to negative in prompt_compiler — do NOT drop silently.
# Ref: docs/설계문서/07 §2 / session_005 실측
CENSORED_TAGS: frozenset[str] = frozenset({
    "censored",
    "mosaic censoring",
    "mosaic censor",
    "bar censor",
    "convenient censoring",
    "light censor",
})


class TipoClient:
    """Wraps TIPO (KGen) for danbooru tag expansion.

    GPU-only: CPU is ~82s for long prompts (measured Phase 1).
    Model loaded lazily on first call — kgen caches it module-level.
    Runs in thread executor to avoid blocking the async event loop.

    API (verified 2026-06-18 against tipo-kgen installed version):
      parse_tipo_request(tag_map, ...) → (meta, operations, general_str, nl_prompt)
      tipo_runner(meta, operations, general, nl) → (parsed_dict, timing)
      parsed keys: special (subjects), general (expanded tags), tag (flat all)
    """

    def __init__(self) -> None:
        self._model = settings.tipo_model
        self._device = settings.tipo_device

    async def expand_tags(self, seed_tags: list[str], model_profile: str, nsfw_level: int = 0) -> list[str]:
        """Expand seed tags into a full danbooru tag list (pre-allowlist).

        nsfw_level: 0=safe, 1=sensitive, 2=explicit — controls TIPO rating context.
        Returns raw expanded list — censored tag handling is caller's responsibility.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, partial(self._expand_sync, seed_tags, nsfw_level)
        )

    def _expand_sync(self, seed_tags: list[str], nsfw_level: int = 0) -> list[str]:
        import kgen.models as kmodels
        import kgen.executor.tipo as tipo

        kmodels.load_model(self._model, gguf=False, device=self._device)
        logger.info("TIPO expand: seeds=%s nsfw=%d", seed_tags, nsfw_level)

        rating = {0: "safe", 1: "sensitive", 2: "explicit"}.get(nsfw_level, "safe")
        tag_map = {
            "rating": [rating],
            "special": [],
            "general": seed_tags,
            "quality": [],
            "characters": [],
            "copyrights": [],
            "artist": [],
            "meta": [],
        }
        meta, operations, general, nl = tipo.parse_tipo_request(
            tag_map, generate_extra_nl_prompt=False
        )
        parsed, _timing = tipo.tipo_runner(meta, operations, general, nl)

        # special = subject tags (e.g. "1girl"), general = expanded tags
        tags = parsed.get("special", []) + parsed.get("general", [])
        logger.info("TIPO expand: %d seeds → %d tags", len(seed_tags), len(tags))
        return tags

    async def expand_natural_language(self, seed_tags: list[str]) -> str:
        """Natural-language mode for Chroma/Flux profiles."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, partial(self._expand_nl_sync, seed_tags)
        )

    def _expand_nl_sync(self, seed_tags: list[str]) -> str:
        import kgen.models as kmodels
        import kgen.executor.tipo as tipo

        kmodels.load_model(self._model, gguf=False, device=self._device)
        tag_map = {
            "rating": ["explicit"],
            "special": [],
            "general": seed_tags,
            "quality": [],
            "characters": [],
            "copyrights": [],
            "artist": [],
            "meta": [],
        }
        meta, operations, general, nl = tipo.parse_tipo_request(
            tag_map, generate_extra_nl_prompt=True
        )
        parsed, _timing = tipo.tipo_runner(meta, operations, general, nl)
        extended = parsed.get("extended", "")
        return extended if isinstance(extended, str) else ", ".join(seed_tags)
