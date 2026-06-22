import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 2   # seconds between /history polls
_POLL_MAX = 150      # max polls before timeout (~5 min)


class ComfyUIClient:
    def __init__(self) -> None:
        self._base = settings.comfyui_base_url
        self._output_dir = Path(settings.comfyui_output_dir)
        self._input_dir = Path(settings.comfyui_input_dir)

    async def upload_image(self, b64: str) -> str:
        """Decode base64 image, write to ComfyUI input dir, return filename for LoadImage node."""
        import base64
        import uuid
        data = base64.b64decode(b64)
        filename = f"ref_{uuid.uuid4().hex}.png"
        self._input_dir.mkdir(parents=True, exist_ok=True)
        (self._input_dir / filename).write_bytes(data)
        logger.info("ComfyUI: uploaded reference %s (%d bytes)", filename, len(data))
        return filename

    async def submit(self, workflow: dict[str, Any]) -> str:
        """POST workflow JSON to /prompt. Returns prompt_id."""
        logger.info("ComfyUI: submitting workflow")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/prompt",
                json={"prompt": workflow},
                timeout=30,
            )
            resp.raise_for_status()
            prompt_id: str = resp.json()["prompt_id"]
        logger.info("ComfyUI: prompt_id=%s", prompt_id)
        return prompt_id

    async def wait_result(self, prompt_id: str) -> str:
        """Poll /history until generation complete. Returns absolute image path."""
        logger.info("ComfyUI: waiting for prompt_id=%s", prompt_id)
        async with httpx.AsyncClient() as client:
            for _ in range(_POLL_MAX):
                await asyncio.sleep(_POLL_INTERVAL)
                resp = await client.get(
                    f"{self._base}/history/{prompt_id}",
                    timeout=10,
                )
                resp.raise_for_status()
                history = resp.json()
                if prompt_id not in history:
                    continue
                outputs = history[prompt_id].get("outputs", {})
                for node_output in outputs.values():
                    images = node_output.get("images", [])
                    if images:
                        img = images[0]
                        sub = img.get("subfolder", "")
                        path = self._output_dir / sub / img["filename"] if sub else self._output_dir / img["filename"]
                        logger.info("ComfyUI: generation done path=%s", path)
                        return str(path)
        raise TimeoutError(f"ComfyUI generation timed out: prompt_id={prompt_id}")

    async def free(self) -> None:
        """Unload models from VRAM after generation (/free endpoint)."""
        logger.info("VRAM: ComfyUI free")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/free",
                json={"unload_models": True, "free_memory": True},
                timeout=30,
            )
            resp.raise_for_status()
        logger.info("VRAM: ComfyUI models unloaded")
