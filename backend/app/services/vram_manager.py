import logging

from app.clients.ollama_client import OllamaClient
from app.clients.comfyui_client import ComfyUIClient
from app.config import settings

logger = logging.getLogger(__name__)


class VramManager:
    """Enforces single-occupancy VRAM rule.

    Critical order: unload LLM first, then load image model.
    Reversing this order triggers an ollama infinite-loop bug when another
    process already occupies VRAM.
    Ref: docs/설계문서/02-하드웨어-VRAM-오케스트레이션.md
    """

    def __init__(self, ollama: OllamaClient, comfyui: ComfyUIClient) -> None:
        self._ollama = ollama
        self._comfyui = comfyui

    async def prepare_for_generation(self) -> None:
        """Unload active LLM models before handing VRAM to ComfyUI."""
        logger.info("VRAM: unloading LLM models")
        for model in [settings.llm_main_model, settings.llm_nsfw_model, settings.llm_vl_model]:
            await self._ollama.unload(model)
        logger.info("VRAM: LLM unloaded, ComfyUI may now load image model")

    async def release_after_generation(self) -> None:
        """Free ComfyUI VRAM after generation completes."""
        logger.info("VRAM: freeing ComfyUI models")
        await self._comfyui.free()
