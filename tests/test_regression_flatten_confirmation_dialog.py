from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MODULE = (ROOT / "js" / "canvas" / "confirm-dialog.js").read_text(encoding="utf-8", errors="replace")


def test_flatten_uses_docked_nonblocking_confirmation_before_history_or_mutation():
    source = CANVAS[CANVAS.index("function flattenAllLayers(options)"):CANVAS.index("// Merge all visible layers")]
    warning = source.index("dialog.open({")
    history = source.index("_pushLayerStackUndo('flatten all')")
    mutation = source.index("_psdLayers.length = 0")
    assert warning < history < mutation
    assert "confirm(" not in source
    assert "flattenAllLayers({ confirmed: true })" in source
    assert "no layers were changed" in source


def test_docked_confirmation_is_cancel_first_escape_safe_and_keeps_source_visible():
    assert "background:rgba(0,0,0,.04)" in MODULE
    assert "left:12px" in MODULE
    assert "cancel.focus();" in MODULE
    assert "event.key === 'Escape'" in MODULE
    assert "if (event.target === overlay) close('cancel')" in MODULE
    assert "role', 'dialog'" in MODULE


def test_confirmation_module_is_loaded_and_all_runtime_copies_match():
    assert "js/canvas/confirm-dialog.js?v=spb93-docked-confirm-20260809a" in HTML
    for relative in (Path("js/canvas/confirm-dialog.js"), Path("paint-booth-3-canvas.js"), Path("paint-booth-v2.html")):
        assert (ROOT / relative).read_bytes() == (ROOT / "electron-app" / "server" / relative).read_bytes()
