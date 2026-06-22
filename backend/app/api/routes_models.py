import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
async def list_models() -> dict:
    """Return installed ollama models and current chat model.
    Embedding models are excluded from the chat candidate list.
    """
    from app.deps import ollama, runtime_config
    available = [m for m in await ollama.list_models() if "embed" not in m.lower()]
    return {"available": available, "current": runtime_config.get_chat_model()}


@router.put("/chat")
async def set_chat_model(body: dict) -> dict:
    """Switch the main chat (intent-parsing) model. NSFW model is not switchable."""
    from app.deps import ollama, runtime_config
    model = body.get("model")
    if not model:
        raise HTTPException(status_code=400, detail="model field required")
    installed = await ollama.list_models()
    if model not in installed:
        raise HTTPException(status_code=400, detail=f"model not installed: {model}")
    runtime_config.set_chat_model(model)
    logger.info("chat model switched -> %s", model)
    return {"current": model}
