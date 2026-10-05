"""SPB-93 T39: Layer names edit inline like Photoshop, without prompt()."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _body(start_marker: str, end_marker: str) -> str:
    start = CANVAS.index(start_marker)
    end = CANVAS.index(end_marker, start)
    return CANVAS[start:end]


def test_layer_rename_uses_inline_editor_not_blocking_browser_prompt():
    begin = _body("function renameLayer(layerId)", "function commitLayerRename(")
    assert "prompt(" not in begin
    assert "_layerRenameEditingId = layerId" in begin
    assert "renderLayerPanel()" in begin
    assert "_focusLayerRenameEditor(layerId)" in begin

    assert 'class="layer-name-editor"' in CANVAS
    assert 'maxlength="64"' in CANVAS
    assert 'aria-label="Rename layer ${_safeName}"' in CANVAS
    assert "event.key==='Enter'" in CANVAS
    assert "commitLayerRename('${l.id}',this.value)" in CANVAS
    assert "event.key==='Escape'" in CANVAS
    assert "cancelLayerRename('${l.id}')" in CANVAS
    assert "setTimeout(() => commitLayerRename" in CANVAS


def test_inline_rename_is_one_truthful_layer_history_transaction():
    commit = _body("function commitLayerRename(layerId, raw)", "function cancelLayerRename(")
    assert "if (!layer || _layerRenameEditingId !== layerId) return false" in commit
    assert "[\\x00-\\x1f]" in commit
    assert "slice(0, 64)" in commit
    assert "Another layer already uses that name" in commit
    assert commit.index("_pushLayerStackUndo('rename layer')") < commit.index("layer.name = newName")
    assert "_layerRenameEditingId = null" in commit

    cancel = _body("function cancelLayerRename(layerId)", "window.renameLayer = renameLayer")
    assert "_pushLayerStackUndo" not in cancel
    assert "_layerRenameEditingId = null" in cancel


def test_inline_rename_runtime_is_cache_busted_and_packaged():
    assert "paint-booth-3-canvas.js?v=spb93-tool-gauntlet-20260808" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
