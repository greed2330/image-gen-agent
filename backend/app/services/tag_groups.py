from pathlib import Path

import yaml

_GROUPS_PATH = Path(__file__).parent.parent / "presets" / "tag_attribute_groups.yaml"


def normalize_tag(tag: str) -> str:
    return tag.strip().lower().replace("_", " ")


def attr_group_of(tag: str, groups: dict[str, list[str]]) -> str | None:
    for gname, members in groups.items():
        if tag in members:
            return gname
    return None


def load_tag_groups() -> dict[str, list[str]]:
    with _GROUPS_PATH.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return {g: [normalize_tag(t) for t in members] for g, members in raw.items()}


def merge_identity(
    card_tags: list[str],
    new_tags: list[str],
    groups: dict[str, list[str]],
) -> list[str]:
    """Merge new identity tags into card, replacing same-group slots (e.g. hair color)."""
    result = [normalize_tag(t) for t in card_tags]
    for raw in new_tags:
        nt = normalize_tag(raw)
        g = attr_group_of(nt, groups)
        if g:
            result = [t for t in result if attr_group_of(t, groups) != g]
        if nt not in result:
            result.append(nt)
    return result
