from pathlib import Path

from PIL import Image

import _forge_final_showcase as showcase


def test_fit_tile_preserves_requested_size() -> None:
    image = Image.new("RGBA", (400, 100), (255, 0, 0, 128))
    result = showcase.fit_tile(image, (200, 160))
    assert result.size == (200, 160)
    assert result.mode == "RGB"


def test_semantic_tile_composites_two_transparent_layers(tmp_path: Path) -> None:
    number = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    number.paste((255, 20, 20, 255), (10, 10, 40, 40))
    sponsor = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    sponsor.paste((20, 220, 80, 255), (60, 60, 90, 90))
    number_path, sponsor_path = tmp_path / "number.png", tmp_path / "sponsor.png"
    number.save(number_path)
    sponsor.save(sponsor_path)
    result = showcase.semantic_tile(number_path, sponsor_path, (240, 200))
    assert result.size == (240, 200)
    assert result.mode == "RGB"
