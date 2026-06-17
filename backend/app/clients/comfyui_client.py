import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class ComfyUIClient:
    def __init__(self) -> None:
        self._base = settings.comfyui_base_url

    async def submit(self, workflow: dict[str, Any]) -> str:
        """POST workflow JSON to /prompt. Returns prompt_id."""
        raise NotImplementedError

    async def wait_result(self, prompt_id: str) -> str:
        """Poll /history until generation complete. Returns output image path."""
        raise NotImplementedError

    async def free(self) -> None:
        """Unload models from VRAM after generation (/free endpoint)."""
        raise NotImplementedError
