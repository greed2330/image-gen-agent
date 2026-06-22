import json
from pathlib import Path

from app.config import settings

_PATH = Path(__file__).parent.parent.parent / "data" / "runtime_settings.json"


class RuntimeConfig:
    def __init__(self) -> None:
        self._data: dict = {}

    def init(self) -> None:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        if _PATH.exists():
            self._data = json.loads(_PATH.read_text(encoding="utf-8"))

    def get_chat_model(self) -> str:
        return self._data.get("chat_model") or settings.llm_main_model

    def set_chat_model(self, model: str) -> None:
        self._data["chat_model"] = model
        _PATH.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
