from contextlib import contextmanager
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

_DB_PATH = Path(__file__).parent.parent / "data" / "app.db"
_engine = None


def init_db() -> None:
    global _engine
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(
        f"sqlite:///{_DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    import app.models.db  # noqa: F401 — registers tables with SQLModel metadata
    SQLModel.metadata.create_all(_engine)


@contextmanager
def get_session():
    if _engine is None:
        raise RuntimeError("DB not initialized — call init_db() first")
    with Session(_engine) as session:
        yield session
