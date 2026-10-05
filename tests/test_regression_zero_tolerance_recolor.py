"""SPB-93 Pass 110: zero tolerance remains a truthful exact-match mode."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _span(start_marker, end_marker):
    start = CANVAS.index(start_marker)
    return CANVAS[start : CANVAS.index(end_marker, start)]


def test_recolor_brush_handles_exact_match_at_zero_without_nan():
    source = _span("function paintRecolor(x, y)", "window.paintRecolor")
    assert "const invToleranceDistance = tol2 > 0 ? 1 / Math.sqrt(tol2) : 0" in source
    assert "const match = tol2 > 0 ? 1 - Math.sqrt(dist2) * invToleranceDistance : 1" in source
    assert "Math.sqrt(dist2) / Math.sqrt(tol2)" not in source


def test_adjustment_color_replace_accepts_zero_as_exact_match():
    single = _span("function autoColorReplace(", "function autoColorReplaceAllLayers")
    all_layers = _span("function autoColorReplaceAllLayers", "window.autoColorReplaceAllLayers")
    for source in (single, all_layers):
        assert "_normalizeColorTolerance(tolerance, 40)" in source
        assert "const invSqrtTol = tol2 > 0 ? 1 / Math.sqrt(tol2) : 0" in source
        assert "const blend = tol2 > 0 ? 1 - Math.sqrt(dist2) * invSqrtTol : 1" in source
        assert "Math.max(1" not in source


def test_zero_tolerance_math_replaces_only_exact_rgb_matches_at_full_strength():
    tolerance = 0
    tolerance_squared = tolerance * tolerance * 3
    cases = {
        (0, 0, 0): 1.0,
        (1, 0, 0): None,
        (0, -1, 0): None,
    }
    for delta, expected in cases.items():
        distance_squared = sum(channel * channel for channel in delta)
        if distance_squared > tolerance_squared:
            blend = None
        else:
            blend = 1.0 if tolerance_squared == 0 else 1.0 - (
                distance_squared / tolerance_squared
            ) ** 0.5
        assert blend == expected


def test_pass_110_runtime_token_and_mirror_are_current():
    assert "spb93-zero-tolerance-recolor-20260717" in HTML
    assert (ROOT / "paint-booth-3-canvas.js").read_bytes() == (
        ROOT / "electron-app/server/paint-booth-3-canvas.js"
    ).read_bytes()
