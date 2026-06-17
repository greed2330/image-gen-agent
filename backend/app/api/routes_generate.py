import logging

from fastapi import APIRouter, WebSocket
from fastapi.responses import JSONResponse

from app.models.schemas import GenRequest, GenResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("", response_model=GenResult)
async def generate(request: GenRequest) -> GenResult:
    """Run the full 6-stage pipeline and return the result with trace."""
    raise NotImplementedError


@router.websocket("/progress")
async def progress_ws(websocket: WebSocket) -> None:
    """Stream generation progress events."""
    raise NotImplementedError
