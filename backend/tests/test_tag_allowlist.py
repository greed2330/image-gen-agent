from app.services.tag_allowlist import TagAllowlist


def test_empty_allowlist_passes_all():
    a = TagAllowlist()
    valid, dropped = a.validate(["1girl", "pink hair", "nonexistent_xyz"])
    assert valid == ["1girl", "pink hair", "nonexistent_xyz"]
    assert dropped == []


def test_loaded_allowlist_drops_unknown(tmp_path):
    csv = tmp_path / "danbooru_tags.csv"
    csv.write_text("1girl,0,1000\npink hair,0,500\n", encoding="utf-8")

    a = TagAllowlist()
    a._tags = {"1girl", "pink hair"}
    valid, dropped = a.validate(["1girl", "pink hair", "fake_tag_xyz"])
    assert "fake_tag_xyz" in dropped
    assert "1girl" in valid


def test_validate_empty_input():
    a = TagAllowlist()
    valid, dropped = a.validate([])
    assert valid == []
    assert dropped == []
