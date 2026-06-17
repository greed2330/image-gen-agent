import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("")
async def create_chat() -> dict:
    raise NotImplementedError


@router.get("")
async def list_chats() -> list:
    raise NotImplementedError


@router.delete("/{chat_id}")
async def delete_chat(chat_id: str) -> dict:
    raise NotImplementedError
