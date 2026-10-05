from pathlib import Path

from PIL import Image

import _forge_render_design as renderer
import _forge_semantic as semantic


def _design() -> dict:
    element = {
        "id": "number-door-right",
        "asset": {"path": "assets/number.png"},
        "role": "number",
        "surface": "right_strip",
        "side": "right",
        "mirror_policy": "preserve_readability",
        "psd_group": semantic.PSD_GROUPS["number"],
        "placement": {"bbox": [0, 722, 655, 155], "fit": "stretch"},
        "confidence": 0.95,
        "abstentions": [],
    }
    return {
        "$schema": semantic.SCHEMA,
        "source": {"dossier": "_dlm_dossier"},
        "base": {"color": "#123456"},
        "surface_fills": {"roof": {"style": "solid", "colors": ["#123456"]}},
        "procedural": {"sponsors": []},
        "elements": [element],
    }


def test_design_to_brief_preserves_semantics_and_placement(tmp_path: Path) -> None:
    brief = renderer.design_to_brief(_design(), root=tmp_path)

    assert brief["base"]["color"] == "#123456"
    assert brief["roof"]["style"] == "solid"
    assert brief["graphics"][0]["bbox"] == [0, 722, 655, 155]
    assert brief["graphics"][0]["semantic"]["id"] == "number-door-right"
    assert brief["graphics"][0]["semantic"]["role"] == "number"
    assert Path(brief["graphics"][0]["image"]).is_absolute()


def test_expected_layer_names_match_legacy_duplicate_suffix_contract() -> None:
    elements = [
        {"asset": {"path": "a/logo.png"}},
        {"asset": {"path": "b/logo.png"}},
        {"asset": {"path": "a/number.png"}},
    ]

    assert renderer.expected_graphic_layer_names(elements) == ["logo", "logo 2", "number"]


def test_semantic_group_mapping_is_generic_and_contract_complete() -> None:
    assert len(renderer.GROUP_ORDER_BOTTOM_FIRST) == 8
    assert renderer.semantic_group_for_layer("Template", None) == semantic.PSD_GROUPS["template"]
    assert renderer.semantic_group_for_layer("Base", None) == semantic.PSD_GROUPS["base"]
    assert renderer.semantic_group_for_layer("Fill roof", None) == semantic.PSD_GROUPS["top_surface"]
    assert renderer.semantic_group_for_layer("Generated sweep", None) == semantic.PSD_GROUPS["paint_shape"]
    assert renderer.semantic_group_for_layer("Door 11", _design()["elements"][0]) == semantic.PSD_GROUPS["number"]


def test_semantic_group_composite_follows_group_then_layer_order() -> None:
    bottom = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
    top = Image.new("RGBA", (2, 2), (0, 255, 0, 128))
    result = renderer.composite_semantic_groups(
        [{"name": "bottom", "layers": [("a", bottom)]}, {"name": "top", "layers": [("b", top)]}],
        (2, 2),
    )
    expected = bottom.copy()
    expected.alpha_composite(top)
    assert renderer._difference(result, expected)["different_pixels"] == 0


def test_difference_reports_exact_and_changed_pixels() -> None:
    first = Image.new("RGBA", (3, 3), (0, 0, 0, 0))
    second = first.copy()
    assert renderer._difference(first, second)["different_pixels"] == 0
    second.putpixel((1, 1), (255, 0, 0, 255))
    changed = renderer._difference(first, second)
    assert changed["different_pixels"] == 1
    assert changed["max_channel_error"] == 255


def test_aggregate_showcase_writes_all_semantic_rows(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    output = tmp_path / "demo"
    output.mkdir(exist_ok=True)
    for filename in ("composite.png", "layer_paint.png", "layer_sponsors.png", "layer_numbers.png"):
        Image.new("RGBA", (64, 64), (255, 0, 0, 128)).save(output / filename)
    destination = tmp_path / "showcase.png"

    renderer.build_aggregate_showcase([output], destination)

    with Image.open(destination) as showcase:
        assert showcase.width > 700
        assert showcase.height > 1500
