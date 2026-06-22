"""Tests for ChatStore — uses in-memory SQLite (sqlite://)."""
import pytest
from sqlmodel import SQLModel, create_engine, Session

from app.models.db import Generation, Message, Room
from app.services.tag_groups import merge_identity, load_tag_groups


@pytest.fixture
def store(monkeypatch):
    """Create a ChatStore backed by an in-memory SQLite DB."""
    import app.db as db_module

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    import app.models.db  # noqa: F401
    SQLModel.metadata.create_all(engine)

    from contextlib import contextmanager

    @contextmanager
    def _get_session():
        with Session(engine) as s:
            yield s

    monkeypatch.setattr(db_module, "get_session", _get_session)
    monkeypatch.setattr(db_module, "_engine", engine)

    from app.services.chat_store import ChatStore
    return ChatStore()


# --- Room CRUD ---

def test_create_and_get_room(store):
    room = store.create_room("테스트 방")
    assert room.id
    assert room.name == "테스트 방"

    fetched = store.get_room(room.id)
    assert fetched is not None
    assert fetched.name == "테스트 방"


def test_list_rooms_ordered_by_updated_at(store):
    r1 = store.create_room("방1")
    r2 = store.create_room("방2")
    store.update_room(r1.id, name="방1 수정")  # r1 newer updated_at

    rooms = store.list_rooms()
    assert rooms[0].id == r1.id  # most recently updated first


def test_delete_room_cascades(store):
    room = store.create_room("삭제 방")
    store.add_message(room.id, "user", text="안녕")
    assert store.delete_room(room.id) is True
    assert store.get_room(room.id) is None
    assert store.list_messages(room.id) == []


def test_delete_nonexistent_room(store):
    assert store.delete_room("no-such-id") is False


# --- Messages ---

def test_add_and_list_messages(store):
    room = store.create_room()
    store.add_message(room.id, "user", text="백호 수인 소녀")
    store.add_message(room.id, "ai", text="생성 완료.", image_path="out.png")

    msgs = store.list_messages(room.id)
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[1].image_path == "out.png"


# --- Identity card ---

def test_identity_starts_empty(store):
    room = store.create_room()
    assert store.get_identity(room.id) == []


def test_set_and_get_identity(store):
    room = store.create_room()
    store.set_identity(room.id, ["white hair", "tiger ears"])
    assert store.get_identity(room.id) == ["white hair", "tiger ears"]


# --- Generation ---

def test_add_and_list_generation(store):
    room = store.create_room()
    gen = Generation(
        room_id=room.id,
        user_message="백호",
        seed=12345,
        steps=28,
        cfg=5.0,
        sampler="euler_ancestral",
        scheduler="normal",
        width=832,
        height=1216,
        status="ok",
    )
    saved = store.add_generation(gen)
    assert saved.id
    assert saved.seed == 12345

    gens = store.list_generations(room_id=room.id)
    assert len(gens) == 1
    assert gens[0].seed == 12345


# --- merge_identity (attribute group slot replacement) ---

def test_merge_identity_replaces_hair_color():
    groups = load_tag_groups()
    card = ["white hair", "tiger ears"]
    new_tags = ["red hair"]  # same group as white hair → replace
    result = merge_identity(card, new_tags, groups)
    assert "white hair" not in result
    assert "red hair" in result
    assert "tiger ears" in result


def test_merge_identity_keeps_unrelated_tags():
    groups = load_tag_groups()
    card = ["white hair", "amber eyes"]
    new_tags = ["red hair"]  # only replaces hair slot
    result = merge_identity(card, new_tags, groups)
    assert "amber eyes" in result
    assert "red hair" in result
    assert "white hair" not in result


def test_merge_identity_no_duplicate():
    groups = load_tag_groups()
    card = ["white hair"]
    result = merge_identity(card, ["white hair"], groups)
    assert result.count("white hair") == 1
