import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Awaitable, Callable

import httpx
import websockets

from app.config import settings

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 2   # seconds between /history polls
_POLL_MAX = 150      # max polls before timeout (~5 min)
_GEN_TIMEOUT = 300   # max seconds to wait for a streamed generation

ProgressCb = Callable[[int, int], Awaitable[None]]


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

    async def submit(self, workflow: dict[str, Any], client_id: str | None = None) -> str:
        """POST workflow JSON to /prompt. Returns prompt_id.

        client_id tags the run so ComfyUI sends its progress events to the WS
        connection opened with that same clientId (see generate()).
        """
        logger.info("ComfyUI: submitting workflow")
        body: dict[str, Any] = {"prompt": workflow}
        if client_id:
            body["client_id"] = client_id
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self._base}/prompt", json=body, timeout=30)
            resp.raise_for_status()
            prompt_id: str = resp.json()["prompt_id"]
        logger.info("ComfyUI: prompt_id=%s", prompt_id)
        return prompt_id

    def _image_path_from_history(self, history: dict, prompt_id: str) -> str | None:
        """Extract the absolute output image path from a /history response."""
        if prompt_id not in history:
            return None
        outputs = history[prompt_id].get("outputs", {})
        for node_output in outputs.values():
            images = node_output.get("images", [])
            if images:
                img = images[0]
                sub = img.get("subfolder", "")
                path = self._output_dir / sub / img["filename"] if sub else self._output_dir / img["filename"]
                return str(path)
        return None

    async def generate(
        self,
        workflow: dict[str, Any],
        client_id: str,
        progress_cb: ProgressCb | None = None,
    ) -> str:
        """Submit a workflow and stream ComfyUI progress over its WebSocket.

        Forwards each sampling-progress event to progress_cb, returns the output
        image path once execution completes. Replaces poll-based wait_result for
        the interactive path.
        """
        ws_base = self._base.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_base}/ws?clientId={client_id}"
        logger.info("ComfyUI: connecting WS %s", ws_url)
        async with websockets.connect(ws_url, max_size=None) as ws:
            prompt_id = await self.submit(workflow, client_id)
            async with asyncio.timeout(_GEN_TIMEOUT):
                async for raw in ws:
                    if isinstance(raw, (bytes, bytearray)):
                        continue  # binary frames = preview images; ignore
                    msg = json.loads(raw)
                    data = msg.get("data", {})
                    if data.get("prompt_id") != prompt_id:
                        continue
                    if msg.get("type") == "progress":
                        if progress_cb:
                            await progress_cb(int(data.get("value", 0)), int(data.get("max", 1)))
                    elif msg.get("type") == "executing" and data.get("node") is None:
                        break  # execution finished for this prompt

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._base}/history/{prompt_id}", timeout=10)
            resp.raise_for_status()
            path = self._image_path_from_history(resp.json(), prompt_id)
        if path is None:
            raise RuntimeError(f"ComfyUI finished but produced no image: prompt_id={prompt_id}")
        logger.info("ComfyUI: generation done path=%s", path)
        return path

    async def wait_result(self, prompt_id: str) -> str:
        """Poll /history until generation complete. Returns absolute image path."""
        logger.info("ComfyUI: waiting for prompt_id=%s", prompt_id)
        async with httpx.AsyncClient() as client:
            for _ in range(_POLL_MAX):
                await asyncio.sleep(_POLL_INTERVAL)
                resp = await client.get(f"{self._base}/history/{prompt_id}", timeout=10)
                resp.raise_for_status()
                path = self._image_path_from_history(resp.json(), prompt_id)
                if path:
                    logger.info("ComfyUI: generation done path=%s", path)
                    return path
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
