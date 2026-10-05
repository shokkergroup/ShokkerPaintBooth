"""SPB-93 Pass 135: Layer rail controls follow native painter interactions."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_pass_135_layer_name_double_click_renames_without_opening_effects():
    assert 'class="layer-name"' in CANVAS
    assert 'ondblclick="event.stopPropagation(); renameLayer(\'${l.id}\')"' in CANVAS
    assert "Double-click to rename" in CANVAS
    # The row remains the wider effects hit target, while the name consumes its
    # own double click first.
    assert 'ondblclick="event.stopPropagation(); openLayerEffects(\'${l.id}\')"' in CANVAS


def test_pass_135_lock_and_fx_icons_are_real_keyboard_focusable_buttons():
    assert '<button type="button" class="layer-lock-toggle"' in CANVAS
    assert 'aria-pressed="${l.locked ? \'true\' : \'false\'}"' in CANVAS
    assert '<button type="button" class="layer-fx-toggle"' in CANVAS
    assert 'aria-label="Open effects for ${_safeName}"' in CANVAS
    assert ".layer-lock-toggle:focus-visible" in CANVAS
    assert ".layer-fx-toggle:focus-visible" in CANVAS
    assert '<span style="cursor:pointer;font-size:9px;color:${l.locked' not in CANVAS


def test_pass_135_runtime_is_cache_busted_and_mirrored():
    assert "spb93-layer-rail-native-controls-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
