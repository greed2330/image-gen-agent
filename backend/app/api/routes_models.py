import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["models"])

# Name substrings marking a model unfit as the chat/intent-parsing model:
#   "embed" — embedding-only, cannot chat
#   "vl"    — vision-language; returns empty output for text-only intent JSON
#             (see docs/기타/디버깅기록/2026-06-24-intent-빈출력-VL모델.md)
_CHAT_INCOMPATIBLE = ("embed", "vl")


def is_chat_compatible(model: str) -> bool:
    """True if the model can serve as the chat/intent-parsing model."""
    low = model.lower()
    return not any(bad in low for bad in _CHAT_INCOMPATIBLE)


@router.get("")
async def list_models() -> dict:
    """Return installed ollama models and current chat model.
    Models unfit for intent parsing (embedding, vision-language) are excluded.
    """
    from app.deps import ollama, runtime_config
    available = [m for m in await ollama.list_models() if is_chat_compatible(m)]
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
    if not is_chat_compatible(model):
        raise HTTPException(status_code=400, detail=f"model not usable for intent parsing: {model}")
    runtime_config.set_chat_model(model)
    logger.info("chat model switched -> %s", model)
    return {"current": model}
