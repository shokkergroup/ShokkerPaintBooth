from pathlib import Path

from PIL import Image

import _forge_validate as validate


def test_alpha_health_distinguishes_blank_and_nonblank_rgba(tmp_path: Path) -> None:
    # SPB's shared tmp_path harness can point at a cleaned directory between runs.
    tmp_path.mkdir(parents=True, exist_ok=True)
    blank = tmp_path / "blank.png"
    visible = tmp_path / "visible.png"
    Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(blank)
    image = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    image.putpixel((2, 1), (255, 255, 255, 255))
    image.save(visible)

    assert validate._alpha_health(blank)["nonzero_alpha_pixels"] == 0
    assert validate._alpha_health(visible)["nonzero_alpha_pixels"] == 1


def test_semantic_counts_keep_numbers_separate_from_brands_and_paint() -> None:
    counts = validate._semantic_counts(
        ["Base", "band_right", "number_door_left", "acdelco_right", "Template"]
    )

    assert counts == {
        "brand_or_sponsor_like": 1,
        "number_like": 1,
        "paint_like": 2,
        "template_like": 1,
    }


def test_group_coverage_requires_named_semantic_groups() -> None:
    coverage = validate._group_coverage(["00 TEMPLATE - LOCKED", "30 NUMBERS", "40 SPONSORS"])

    assert coverage["template"] is True
    assert coverage["numbers"] is True
    assert coverage["sponsors"] is True
    assert coverage["paint"] is False


def test_image_difference_distinguishes_exact_from_layer_drift() -> None:
    expected = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    actual = expected.copy()
    assert validate._image_difference(actual, expected)["different_pixels"] == 0
    actual.putpixel((2, 3), (10, 20, 30, 40))
    result = validate._image_difference(actual, expected)
    assert result["different_pixels"] == 1
    assert result["max_channel_error"] == 40


def test_leaf_walk_respects_hidden_parent_group() -> None:
    class Layer:
        def __init__(self, name: str, *, visible: bool = True, children: list["Layer"] | None = None):
            self.name = name
            self.visible = visible
            self.children = children

        def is_group(self) -> bool:
            return self.children is not None

        def __iter__(self):
            return iter(self.children or [])

    visible_leaf = Layer("visible")
    hidden_leaf = Layer("hidden-child")
    layers = [Layer("visible-group", children=[visible_leaf]), Layer("hidden-group", visible=False, children=[hidden_leaf])]
    assert validate._leaf_objects_bottom_first(layers) == [visible_leaf]
