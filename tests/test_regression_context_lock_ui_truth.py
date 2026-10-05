"""SPB-93 Pass 140: locked Layer context actions look read-only before click."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start, depth, index = match.end(), 1, match.end()
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_140_context_button_removes_click_handler_when_disabled():
    helper = _function_body("_contextActionButton")
    assert "disabled aria-disabled=\"true\"" in helper
    assert "disabled ? ' disabled" in helper
    assert "opacity:.38;cursor:not-allowed;" in helper
    assert "Layer is locked" in helper


def test_pass_140_all_layer_pixel_mutation_actions_receive_lock_state():
    render = _function_body("renderContextActionBar")
    for label in (
        "Transform Selection", "Transform Layer", "Rotate 180°",
        "Pick Item", "-90°", "+90°", "180°", "Flip Layer H", "Flip Layer V",
    ):
        pattern = re.compile(rf"_contextActionButton\('{re.escape(label)}'.*?selectedLayer\.locked\)")
        assert pattern.search(render), label
    # Read-only inspection/Zone-mask actions remain useful on a locked Layer.
    fx_line = next(line for line in render.splitlines() if "_contextActionButton('FX'" in line)
    mask_line = next(line for line in render.splitlines() if "_contextActionButton('Zone Mask" in line)
    assert "selectedLayer.locked" not in fx_line and "selectedLayer.locked" not in mask_line


def test_pass_140_runtime_is_cache_busted_and_mirrored():
    assert "spb93-context-lock-ui-truth-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
