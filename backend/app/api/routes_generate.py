import logging

from fastapi import APIRouter, HTTPException, WebSocket

from app.models.schemas import GenRequest, GenResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("", response_model=GenResult)
async def generate(request: GenRequest) -> GenResult:
    """Run the full 6-stage pipeline and return the result with trace."""
    from app.deps import orchestrator
    try:
        return await orchestrator.run(request)
    except Exception as exc:
        logger.exception("pipeline error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/dry-run", response_model=GenResult)
async def generate_dry_run(request: GenRequest) -> GenResult:
    """Stages ①–④ only; no ComfyUI submission. Useful for prompt inspection."""
    from app.deps import orchestrator
    try:
        return await orchestrator.run(request, dry_run=True)
    except Exception as exc:
        logger.exception("dry-run error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.websocket("/progress")
async def progress_ws(websocket: WebSocket) -> None:
    """Stream generation progress events. (Phase 4 — not yet implemented)"""
    await websocket.close(code=1001, reason="not implemented")
