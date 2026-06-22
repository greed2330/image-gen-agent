import logging
from pathlib import Path

import yaml

from app.clients.ollama_client import OllamaClient
from app.clients.tipo_client import TipoClient, CENSORED_TAGS
from app.models.schemas import CompiledPrompt, Intent, ModelProfile, RouteDecision
from app.services.tag_allowlist import TagAllowlist
from app.services.tag_groups import attr_group_of as _attr_group_of
from app.services.tag_groups import load_tag_groups, normalize_tag as _normalize_tag

logger = logging.getLogger(__name__)

_PRESETS_PATH = Path(__file__).parent.parent / "presets" / "model_presets.yaml"

_PROFILE_KEY = {
    ModelProfile.ILLUSTRIOUS: "illustrious_base",
    ModelProfile.NOOBAI: "noobai_base",
    ModelProfile.CHROMA: "chroma_base",
}


class PromptCompiler:
    """③ Compile seed tags into a final danbooru prompt via TIPO + allowlist.

    Pipeline (doc 07 §1-A → updated doc 09 §1):
      seed_tags → TIPO expansion → identity protection (emphasis + conflict exclusion)
                → censored-tag stripping → allowlist → CompiledPrompt

    Identity protection (doc 09 stage 1):
      Protected = all seed_tags (user-specified). After TIPO expansion:
        1. Protected tags are re-stated with emphasis weight (e.g. "(white hair:1.3)")
           so they survive being outnumbered by TIPO-added body/clothing tags.
        2. TIPO tags that conflict with a claimed attribute group slot (e.g. "black hair"
           when "white hair" is claimed) go to negative instead of positive.
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
        self._presets: dict = {}
        self._groups: dict[str, list[str]] = {}

    def load_presets(self) -> None:
        with _PRESETS_PATH.open(encoding="utf-8") as f:
            self._presets = yaml.safe_load(f)
        self._groups = load_tag_groups()

    async def compile(self, intent: Intent, route: RouteDecision) -> CompiledPrompt:
        if route.model_profile == ModelProfile.CHROMA:
            # Chroma uses natural-language mode — no tag protection needed
            nl_text = await self._tipo.expand_natural_language(intent.seed_tags)
            return CompiledPrompt(
                positive=[nl_text],
                negative=[],
                model_profile=route.model_profile,
            )

        # TIPO only expands scene tags — identity tags are excluded to prevent drowning/conflict injection
        tipo_input = intent.subjects + intent.scene_tags
        expanded = await self._tipo.expand_tags(
            tipo_input, route.model_profile.value, nsfw_level=intent.nsfw_level.value
        )

        # Protected = identity_tags. These are emphasized and shielded from TIPO conflicts.
        protected = [_normalize_tag(t) for t in intent.identity_tags if t.strip()]
        protected_set = set(protected)

        # Collect which attribute group slots are claimed by identity
        claimed: dict[str, set[str]] = {}
        for t in protected:
            g = _attr_group_of(t, self._groups)
            if g:
                claimed.setdefault(g, set()).add(t)

        # Classify TIPO output: skip duplicates, move conflicts to negative, keep the rest
        censored_found: list[str] = []
        extras_raw: list[str] = []
        conflict_neg: list[str] = []
        for t in expanded:
            if t in CENSORED_TAGS:
                censored_found.append(t)
                continue
            nt = _normalize_tag(t)
            if nt in protected_set:
                continue  # already covered by protected emphasis
            g = _attr_group_of(nt, self._groups)
            if g and g in claimed and nt not in claimed[g]:
                conflict_neg.append(nt)  # same group, different value → conflict
                continue
            extras_raw.append(t)

        valid_extras, dropped = self._allowlist.validate(extras_raw)

        key = _PROFILE_KEY[route.model_profile]
        preset = self._presets.get(key, {})
        weight = preset.get("identity_emphasis", 1.3)
        emphasized = [f"({t}:{weight})" for t in protected]

        quality_pos: list[str] = preset.get("quality_pos", [])
        quality_neg: list[str] = preset.get("quality_neg", [])
        forced_neg = list(CENSORED_TAGS)
        negative = _dedup(quality_neg + conflict_neg + censored_found + forced_neg)

        logger.info(
            "compile: %d protected(emphasis %.2f) + %d extras (dropped %d, conflict→neg %d)",
            len(emphasized), weight, len(valid_extras), len(dropped), len(conflict_neg),
        )
        return CompiledPrompt(
            positive=quality_pos + emphasized + valid_extras,
            negative=negative,
            model_profile=route.model_profile,
            dropped_tags=dropped,
        )


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
