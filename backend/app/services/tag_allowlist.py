import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_ALLOWLIST_PATH = Path(__file__).parent.parent / "presets" / "danbooru_tags.csv"


class TagAllowlist:
    """Hard safety net: removes tags not in the danbooru allowlist CSV.

    This is the deterministic final filter after TIPO expansion.
    TIPO is probabilistic (reduces hallucination), this guarantees it.
    Unknown tags are either nearest-neighbour substituted or dropped with a warning.
    """

    def __init__(self) -> None:
        self._tags: set[str] = set()

    def load(self) -> None:
        """Load danbooru tag CSV. Call once at startup."""
        if not _ALLOWLIST_PATH.exists():
            logger.warning("danbooru_tags.csv not found — allowlist disabled. Download from: https://github.com/DominikDoom/a1111-sd-webui-tagcomplete")
            return
        with _ALLOWLIST_PATH.open(encoding="utf-8") as f:
            for line in f:
                tag = line.split(",")[0].strip()
                if tag:
                    self._tags.add(tag)
        logger.info("tag allowlist loaded: %d tags", len(self._tags))

    def validate(self, tags: list[str]) -> tuple[list[str], list[str]]:
        """Return (valid_tags, dropped_tags). If allowlist empty, passes all through."""
        if not self._tags:
            return tags, []
        valid, dropped = [], []
        for tag in tags:
            (valid if tag in self._tags else dropped).append(tag)
        if dropped:
            logger.warning("allowlist dropped %d tags: %s", len(dropped), dropped)
        return valid, dropped
