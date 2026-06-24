"""Extract danbooru character tags from a reference image via the VL model.

Used in character mode (Doc 14): IPAdapter transfers a reference character's color
and vibe but weakly reproduces distinctive features (e.g. animal ears/tail). Feeding
those features back as emphasized identity_tags reinforces the likeness.
VRAM-safe: the VL model is in VramManager's unload list, freed before ComfyUI.
"""
import logging

from app.clients.ollama_client import OllamaClient
from app.config import settings

logger = logging.getLogger(__name__)

# Validated 2026-06-25 against the white-tiger reference (clean danbooru output).
_EXTRACT_PROMPT = """List ONLY the character's permanent visual features as danbooru tags (lowercase, spaces).
Format examples: "white hair", "red eyes", "long hair", "animal ears", "tiger ears", "tiger tail", "kemonomimi", "pale skin".
Rules:
- hair color MUST be written as "<color> hair" (e.g. "white hair", never just "white").
- eye color MUST be written as "<color> eyes" (e.g. "red eyes", never just "red").
- animal-eared character: include "animal ears" + "<species> ears" + "<species> tail" + "kemonomimi", species matching the tail.
- EXCLUDE clothing, pose, action, background, expression.
Output ONLY comma-separated danbooru tags, nothing else."""

_MAX_TAGS = 12


class ReferenceTagger:
    def __init__(self, ollama: OllamaClient) -> None:
        self._ollama = ollama

    async def extract(self, image_b64: str) -> list[str]:
        """Return danbooru character tags seen in the reference image (empty on failure)."""
        try:
            raw = await self._ollama.chat(
                model=settings.llm_vl_model,
                messages=[{"role": "user", "content": _EXTRACT_PROMPT, "images": [image_b64]}],
                options={"temperature": 0.1},
            )
        except Exception as exc:
            logger.warning("reference_tagger: extraction failed: %s", exc)
            return []

        tags = _parse_tags(raw)
        logger.info("reference_tagger: extracted %s", tags)
        return tags


def _parse_tags(raw: str) -> list[str]:
    """Comma/newline separated VL output → cleaned, deduped danbooru tags."""
    seen: set[str] = set()
    out: list[str] = []
    for chunk in raw.replace("\n", ",").split(","):
        tag = chunk.strip().strip('"\'*.').lower()
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
        if len(out) >= _MAX_TAGS:
            break
    return out
