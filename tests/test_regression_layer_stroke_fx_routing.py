"""SPB-93 T44: the Layer rail routes outline work to transactional Stroke FX."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start, depth, index = match.start(), 0, match.start()
    while index < len(CANVAS):
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
            if depth == 0 and index > match.end():
                return CANVAS[start : index + 1]
        index += 1
    raise AssertionError(name)


def test_t44_rail_uses_layer_style_stroke_instead_of_baking_pixels():
    panel = _function_source("renderLayerPanel")
    assert "openLayerEffects('${l.id}', 'stroke')" in panel
    assert ">STROKE FX</button>" in panel
    assert "non-destructive Stroke" in panel
    assert "addLayerOutline('${l.id}'" not in panel


def test_t44_stroke_shortcut_focuses_without_mutating_or_publishing_history():
    effects = _function_source("openLayerEffects")
    assert "function openLayerEffects(layerId, focusEffect)" in effects
    assert "if (focusEffect === 'stroke')" in effects
    assert "document.getElementById('fxStrokeEnabled')" in effects
    assert "strokeToggle.scrollIntoView" in effects
    assert "strokeToggle.focus" in effects
    assert "_pushLayer" not in effects
    assert "layer.effects =" not in effects


def test_t44_destructive_outline_api_remains_guarded_for_compatibility():
    outline = _function_source("addLayerOutline")
    assert "if (layer.locked)" in outline
    assert "_pushLayerUndo(layer, 'add outline')" in outline
    assert "return true" in outline


def test_t44_runtime_is_cache_busted_and_mirrored():
    assert "paint-booth-3-canvas.js?v=spb-revsig-20260831a" in HTML
    assert (ROOT / "electron-app/server/paint-booth-3-canvas.js").read_bytes() == (ROOT / "paint-booth-3-canvas.js").read_bytes()
    assert (ROOT / "electron-app/server/paint-booth-v2.html").read_bytes() == (ROOT / "paint-booth-v2.html").read_bytes()
