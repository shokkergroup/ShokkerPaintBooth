from pathlib import Path

import pytest
from PIL import Image

import _forge_review_grid as review


def test_parse_tile() -> None:
    assert review.parse_tile("Before=C:/before.png") == ("Before", Path("C:/before.png"))


def test_compose_writes_expected_grid(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (20, 10), "red").save(source)
    output = tmp_path / "grid.png"
    review.compose("Title", "Subtitle", [("One", source), ("Two", source)], 2, output)
    assert Image.open(output).size == (1254, 448)


def test_compose_rejects_empty_tiles(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one"):
        review.compose("Title", "Subtitle", [], 2, tmp_path / "grid.png")
