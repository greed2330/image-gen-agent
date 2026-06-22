import logging
from pathlib import Path

import yaml

from app.models.schemas import CompiledPrompt, GenParams, Intent, ModelProfile, Resolution, RouteDecision, WorkflowType

logger = logging.getLogger(__name__)

_PRESETS_PATH = Path(__file__).parent.parent / "presets" / "model_presets.yaml"

_PROFILE_KEY = {
    ModelProfile.ILLUSTRIOUS: "illustrious_base",
    ModelProfile.NOOBAI: "noobai_base",
    ModelProfile.CHROMA: "chroma_base",
}

_ASPECT_HINT_MAP = {
    "portrait": "portrait",
    "landscape": "landscape",
    "square": "square",
    "세로": "portrait",
    "가로": "landscape",
    "정사각": "square",
}


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
        key = _PROFILE_KEY[route.model_profile]
        preset = self._presets[key]
        clamp = preset["hard_clamp"]

        steps = int(_clamp(preset["steps"], clamp["steps"][0], clamp["steps"][1]))
        cfg = float(_clamp(preset["cfg"], clamp["cfg"][0], clamp["cfg"][1]))

        aspect = _pick_aspect(intent.mood or "")
        res_list = preset["resolutions"].get(aspect, preset["resolutions"]["portrait"])

        denoise = 1.0
        if route.workflow == WorkflowType.IMG2IMG:
            denoise = float(preset.get("img2img_denoise", 0.55))

        logger.info(
            "params: profile=%s steps=%d cfg=%.1f aspect=%s denoise=%.2f",
            route.model_profile, steps, cfg, aspect, denoise,
        )
        return GenParams(
            steps=steps,
            cfg=cfg,
            sampler=preset["sampler"],
            scheduler=preset["scheduler"],
            resolution=Resolution(width=res_list[0], height=res_list[1]),
            denoise=denoise,
        )


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _pick_aspect(hint: str) -> str:
    h = hint.lower()
    for kw, aspect in _ASPECT_HINT_MAP.items():
        if kw in h:
            return aspect
    return "portrait"
