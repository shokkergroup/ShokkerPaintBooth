"""SPB-93 Pass 83: Recolor softness follows the selected brush footprint."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _span(function_name: str) -> str:
    start = CANVAS.index(f"function {function_name}")
    next_function = CANVAS.find("\nfunction ", start + 10)
    return CANVAS[start : next_function if next_function >= 0 else len(CANVAS)]


def test_recolor_softness_uses_shape_relative_distance():
    source = _span("paintRecolor")
    assert "const shapeDist2 = footprint.distanceSquared(dx, dy);" in source
    assert "_brushFalloff(shapeDist2, radius, hardness)" in source
    assert "_brushFalloff(pixDist2, radius, hardness)" not in source


def test_recolor_still_uses_raw_distance_only_for_footprint_membership():
    source = _span("paintRecolor")
    assert "const pixDist2 = dx * dx + dy * dy;" in source
    assert "footprint.contains(dx, dy, pixDist2)" in source


def test_recolor_shape_falloff_cache_token_is_live():
    assert "spb93-recolor-shape-falloff-20260717" in HTML
