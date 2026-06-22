import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import GenRequest, GenResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chats", tags=["chats"])


class CreateRoomBody(BaseModel):
    name: Optional[str] = None


class PatchRoomBody(BaseModel):
    name: Optional[str] = None


class AddMessageBody(BaseModel):
    role: str
    text: Optional[str] = None
    image_path: Optional[str] = None
    reference_image: Optional[str] = None
    generation_id: Optional[str] = None


@router.post("", response_model=dict)
async def create_chat(body: CreateRoomBody = CreateRoomBody()) -> dict:
    from app.deps import chat_store
    room = chat_store.create_room(name=body.name or "새 채팅")
    logger.info("room created: %s", room.id)
    return {"id": room.id, "name": room.name, "created_at": room.created_at}


@router.get("", response_model=list)
async def list_chats() -> list:
    from app.deps import chat_store
    rooms = chat_store.list_rooms()
    return [{"id": r.id, "name": r.name, "updated_at": r.updated_at} for r in rooms]


@router.get("/{chat_id}", response_model=dict)
async def get_chat(chat_id: str) -> dict:
    from app.deps import chat_store
    room = chat_store.get_room(chat_id)
    if room is None:
        raise HTTPException(status_code=404, detail="chat not found")
    messages = chat_store.list_messages(chat_id)
    return {
        "room": {"id": room.id, "name": room.name, "identity_tags": room.identity_tags},
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "text": m.text,
                "image_path": m.image_path,
                "reference_image": m.reference_image,
                "generation_id": m.generation_id,
                "created_at": m.created_at,
            }
            for m in messages
        ],
    }


@router.patch("/{chat_id}", response_model=dict)
async def update_chat(chat_id: str, body: PatchRoomBody) -> dict:
    from app.deps import chat_store
    room = chat_store.update_room(chat_id, name=body.name)
    if room is None:
        raise HTTPException(status_code=404, detail="chat not found")
    return {"id": room.id, "name": room.name}


@router.delete("/{chat_id}", response_model=dict)
async def delete_chat(chat_id: str) -> dict:
    from app.deps import chat_store
    if not chat_store.delete_room(chat_id):
        raise HTTPException(status_code=404, detail="chat not found")
    logger.info("room deleted: %s", chat_id)
    return {"deleted": chat_id}


@router.post("/{chat_id}/messages", response_model=dict)
async def add_message(chat_id: str, body: AddMessageBody) -> dict:
    from app.deps import chat_store
    if chat_store.get_room(chat_id) is None:
        raise HTTPException(status_code=404, detail="chat not found")
    msg = chat_store.add_message(
        chat_id,
        body.role,
        text=body.text,
        image_path=body.image_path,
        reference_image=body.reference_image,
        generation_id=body.generation_id,
    )
    return {"id": msg.id, "role": msg.role, "created_at": msg.created_at}


@router.post("/{chat_id}/generate", response_model=GenResult)
async def chat_generate(chat_id: str, request: GenRequest) -> GenResult:
    """Generate image and persist both user and AI messages."""
    from app.deps import chat_store, orchestrator

    if chat_store.get_room(chat_id) is None:
        raise HTTPException(status_code=404, detail="chat not found")

    # Save user message
    ref_name: Optional[str] = None
    if request.reference_image:
        ref_name = "attached"  # actual upload handled by orchestrator
    chat_store.add_message(
        chat_id,
        "user",
        text=request.message or None,
        reference_image=ref_name,
    )

    req = GenRequest(
        message=request.message,
        chat_id=chat_id,
        history=request.history,
        reference_image=request.reference_image,
    )
    try:
        result = await orchestrator.run(req)
    except Exception as exc:
        logger.exception("chat generate error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Save AI message
    chat_store.add_message(
        chat_id,
        "ai",
        text="생성 완료." if result.image_path else "생성 실패.",
        image_path=result.image_path,
        generation_id=result.generation_id,
    )
    return result


@router.get("/{chat_id}/generations", response_model=list)
async def list_generations(chat_id: str, limit: int = 50) -> list:
    from app.deps import chat_store
    if chat_store.get_room(chat_id) is None:
        raise HTTPException(status_code=404, detail="chat not found")
    gens = chat_store.list_generations(room_id=chat_id, limit=limit)
    return [
        {
            "id": g.id,
            "image_path": g.image_path,
            "seed": g.seed,
            "steps": g.steps,
            "cfg": g.cfg,
            "sampler": g.sampler,
            "width": g.width,
            "height": g.height,
            "status": g.status,
            "created_at": g.created_at,
        }
        for g in gens
    ]


@router.get("/generations/all", response_model=list)
async def list_all_generations(limit: int = 50) -> list:
    from app.deps import chat_store
    gens = chat_store.list_generations(limit=limit)
    return [
        {
            "id": g.id,
            "room_id": g.room_id,
            "image_path": g.image_path,
            "seed": g.seed,
            "status": g.status,
            "created_at": g.created_at,
        }
        for g in gens
    ]
