import logging
import time
from typing import Optional

from sqlmodel import select

from app.db import get_session
from app.models.db import Generation, Message, Room

logger = logging.getLogger(__name__)


class ChatStore:
    # --- 방 ---

    def create_room(self, name: str = "새 채팅") -> Room:
        with get_session() as s:
            room = Room(name=name)
            s.add(room)
            s.commit()
            s.refresh(room)
            return room

    def get_room(self, room_id: str) -> Optional[Room]:
        with get_session() as s:
            return s.get(Room, room_id)

    def list_rooms(self) -> list[Room]:
        with get_session() as s:
            return list(s.exec(select(Room).order_by(Room.updated_at.desc())).all())

    def update_room(self, room_id: str, *, name: Optional[str] = None) -> Optional[Room]:
        with get_session() as s:
            room = s.get(Room, room_id)
            if room is None:
                return None
            if name is not None:
                room.name = name
            room.updated_at = time.time()
            s.add(room)
            s.commit()
            s.refresh(room)
            return room

    def delete_room(self, room_id: str) -> bool:
        with get_session() as s:
            room = s.get(Room, room_id)
            if room is None:
                return False
            for msg in s.exec(select(Message).where(Message.room_id == room_id)).all():
                s.delete(msg)
            for gen in s.exec(select(Generation).where(Generation.room_id == room_id)).all():
                s.delete(gen)
            s.delete(room)
            s.commit()
            return True

    # --- 메시지 ---

    def add_message(
        self,
        room_id: str,
        role: str,
        *,
        text: Optional[str] = None,
        image_path: Optional[str] = None,
        reference_image: Optional[str] = None,
        generation_id: Optional[str] = None,
    ) -> Message:
        with get_session() as s:
            msg = Message(
                room_id=room_id,
                role=role,
                text=text,
                image_path=image_path,
                reference_image=reference_image,
                generation_id=generation_id,
            )
            s.add(msg)
            room = s.get(Room, room_id)
            if room:
                room.updated_at = time.time()
                s.add(room)
            s.commit()
            s.refresh(msg)
            return msg

    def list_messages(self, room_id: str) -> list[Message]:
        with get_session() as s:
            return list(
                s.exec(
                    select(Message)
                    .where(Message.room_id == room_id)
                    .order_by(Message.created_at)
                ).all()
            )

    # --- 캐릭터 카드 ---

    def get_identity(self, room_id: str) -> list[str]:
        room = self.get_room(room_id)
        return room.identity_tags if room else []

    def set_identity(self, room_id: str, tags: list[str]) -> None:
        with get_session() as s:
            room = s.get(Room, room_id)
            if room:
                room.identity_tags = tags
                s.add(room)
                s.commit()

    # --- 생성기록 ---

    def add_generation(self, gen: Generation) -> Generation:
        with get_session() as s:
            s.add(gen)
            s.commit()
            s.refresh(gen)
            logger.info("generation saved: id=%s status=%s", gen.id, gen.status)
            return gen

    def list_generations(
        self,
        room_id: Optional[str] = None,
        limit: int = 50,
    ) -> list[Generation]:
        with get_session() as s:
            q = select(Generation).order_by(Generation.created_at.desc()).limit(limit)
            if room_id:
                q = q.where(Generation.room_id == room_id)
            return list(s.exec(q).all())
