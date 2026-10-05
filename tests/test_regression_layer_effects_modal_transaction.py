from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
SERVER_CANVAS = (ROOT / "electron-app/server/paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
SERVER_HTML = (ROOT / "electron-app/server/paint-booth-v2.html").read_text(encoding="utf-8")


def _body(source: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    assert match, name
    start = match.end()
    depth = 1
    index = start
    while index < len(source) and depth:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return source[start:index - 1]


def test_root_and_packaged_layer_effects_are_identical():
    assert CANVAS == SERVER_CANVAS
    assert HTML == SERVER_HTML


def test_live_preview_does_not_publish_history_until_apply():
    update = _body(CANVAS, "updateLayerEffect")
    apply = _body(CANVAS, "closeLayerEffects")
    assert "_pushLayerStackUndo" not in update
    assert "_effectsSessionUndoPushed = true" in update
    assert "_scheduleEffectsRecomposite()" in update
    assert "_pushCapturedLayerStackUndo(_effectsSessionBefore, 'layer effects')" in apply


def test_cancel_restores_pre_dialog_effects_without_history_or_redo_mutation():
    cancel = _body(CANVAS, "cancelLayerEffects")
    assert "_effectsSessionBefore.snapshot.find" in cancel
    assert "layer.effects = saved && saved.effects" in cancel
    assert "recompositeFromLayers()" in cancel
    assert "_pushLayerStackUndo" not in cancel
    assert "_clearAllRedos" not in cancel


def test_effects_dialog_is_docked_with_source_visible_and_real_apply_cancel():
    start = HTML.index('<div id="layerEffectsDialog"')
    end = HTML.index("<!-- Keyboard Shortcut Overlay -->", start)
    dialog = HTML[start:end]
    assert "background:rgba(0,0,20,0.06)" in dialog
    assert "backdrop-filter:none" in dialog
    assert "top:88px; left:12px" in dialog
    assert "Live preview on SOURCE" in dialog
    assert 'onclick="cancelLayerEffects()"' in dialog
    assert ">Cancel</button>" in dialog
    assert ">Apply</button>" in dialog


def test_escape_cancels_layer_effects_preview():
    assert "_spbLayerEffectsEscapeBound" in CANVAS
    assert "event.key !== 'Escape'" in CANVAS
    assert "cancelLayerEffects();" in CANVAS
    assert "paint-booth-3-canvas.js?v=spb93-tool-gauntlet-20260808" in HTML
