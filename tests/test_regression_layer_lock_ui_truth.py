from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_pass_130_locked_layer_editor_controls_are_visibly_read_only():
    assert "const lockedControlAttr = l.locked ? ' disabled aria-disabled=\"true\"' : ''" in CANVAS
    assert "const lockedControlTitle = l.locked ? 'Layer is locked — unlock to edit' : ''" in CANVAS
    opacity = CANVAS.index('data-layer-opacity-control="${l.id}"')
    blend = CANVAS.index('data-layer-blend-control="${l.id}"')
    assert "${lockedControlAttr}" in CANVAS[opacity : opacity + 500]
    assert "${lockedControlAttr}" in CANVAS[blend : blend + 400]


def test_pass_130_destructive_row_actions_do_not_advertise_on_locked_layers():
    for action in ("mergeLayerDown", "deleteLayer", "addLayerOutline"):
        start = CANVAS.index(f'<button onclick="{action}')
        button = CANVAS[start : CANVAS.index("</button>", start)]
        assert "${lockedControlAttr}" in button
        assert "${lockedControlTitle" in button
    assert ".layer-act-btn:disabled" in CANVAS
    assert "cursor:not-allowed" in CANVAS


def test_pass_130_runtime_is_cache_busted():
    assert "spb93-layer-lock-ui-truth-20260717" in HTML
    assert "spb93-layer-reorder-command-lock-20260717" in HTML
