import logging
from pathlib import Path

import yaml

from app.models.schemas import CompiledPrompt, GenParams, Intent, Resolution, RouteDecision

logger = logging.getLogger(__name__)

_PRESETS_PATH = Path(__file__).parent.parent / "presets" / "model_presets.yaml"


class ParamResolver:
    """④ Resolve generation parameters: preset base + LLM nudge + hard clamp.

    LLM never sets raw numbers freely — it nudges within allowed_nudge range.
    hard_clamp is enforced by code regardless of LLM output.
    Ref: docs/설계문서/07 §3
    """

    def __init__(self) -> None:
        self._presets: dict = {}

    def load_presets(self) -> None:
        with _PRESETS_PATH.open(encoding="utf-8") as f:
            self._presets = yaml.safe_load(f)
        logger.info("model presets loaded: %s", list(self._presets.keys()))

    async def resolve(
        self, intent: Intent, route: RouteDecision, compiled: CompiledPrompt
    ) -> GenParams:
        raise NotImplementedError
