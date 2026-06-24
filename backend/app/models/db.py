import time
import uuid
from typing import Optional

from sqlmodel import Column, Field, JSON, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


class Room(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str = "새 채팅"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    nsfw_default: int = 0
    identity_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class Message(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    room_id: str = Field(index=True)
    role: str  # "user" | "ai"
    text: Optional[str] = None
    image_path: Optional[str] = None
    reference_image: Optional[str] = None
    generation_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class Generation(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    room_id: str = Field(index=True)
    created_at: float = Field(default_factory=time.time, index=True)
    user_message: str = ""
    reference_image: Optional[str] = None
    identity_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    scene_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    nsfw_level: int = 0
    style: Optional[str] = None
    workflow: str = "txt2img"
    checkpoint: str = ""
    model_profile: str = ""
    positive: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    negative: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    steps: int = 0
    cfg: float = 0.0
    sampler: str = ""
    scheduler: str = ""
    width: int = 0
    height: int = 0
    denoise: float = 1.0
    seed: int = 0
    image_path: Optional[str] = None
    duration_ms: float = 0.0
    status: str = "ok"
    error: Optional[str] = None
