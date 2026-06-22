import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{filename}")
async def serve_image(filename: str, download: int = 0) -> FileResponse:
    """Serve a generated image from the ComfyUI output directory.
    Pass ?download=1 to trigger browser download (Content-Disposition: attachment).
    """
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="invalid filename")
    path = Path(settings.comfyui_output_dir) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="image not found")
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'} if download else {}
    return FileResponse(path, media_type="image/png", headers=headers)
