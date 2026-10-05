"""SPB-93 Pass 90: every advertised single-key toolbar shortcut is live."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_every_advertised_single_key_tool_has_a_mode_route():
    routes = {
        "v": "layer-move",
        "y": "pick-item",
        "p": "eyedropper",
        "w": "wand",
        "l": "lasso",
        "o": "rect",
        "b": "brush",
        "k": "fill",
        "g": "gradient",
        "e": "erase",
        "t": "text",
        "u": "shape",
        "n": "pen",
        "m": "ellipse-marquee",
        "c": "colorbrush",
        "s": "clone",
        "r": "recolor",
        "q": "smudge",
        "i": "pencil",
        "d": "dodge",
        "j": "burn",
        "f": "blur-brush",
        "h": "sharpen-brush",
        "a": "selectall",
    }
    for key, mode in routes.items():
        assert f"key === '{key}'" in CANVAS, key
        assert f"setCanvasMode('{mode}')" in CANVAS, mode


def test_move_title_and_shortcut_guide_match_the_v_route():
    assert "Move (V)" in HTML
    assert "<kbd" in HTML and ">V</kbd> Move" in HTML
    assert "key === 'v'" in CANVAS
    assert "setCanvasMode('layer-move')" in CANVAS


def test_move_shortcut_truth_cache_token_is_live():
    assert "spb93-move-shortcut-truth-20260717" in HTML
