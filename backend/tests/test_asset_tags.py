import pytest

from services.asset_tags import _normalize_tag_name


def test_normalize_tag_name() -> None:
    assert _normalize_tag_name("  Flower  ") == "flower"


def test_normalize_tag_name_rejects_empty() -> None:
    with pytest.raises(Exception) as exc:
        _normalize_tag_name("   ")
    assert exc.value.status_code == 400
