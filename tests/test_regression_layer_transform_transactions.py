from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start = match.end()
    depth = 1
    index = start
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_99_transform_candidate_checks_pixels_dimensions_and_bbox():
    body = _function_body("_layerTransformCandidateDiffers")
    assert "sourceWidth !== candidate.width" in body
    assert "currentBbox.some" in body
    assert "before[i] !== after[i]" in body
    assert "return false" in body


def test_pass_99_one_commit_boundary_owns_history_and_refresh():
    body = _function_body("_commitDestructiveLayerTransform")
    no_op = body.index("if (!_layerTransformCandidateDiffers")
    history = body.index("_pushLayerUndo")
    mutation = body.index("layer.img = candidate")
    assert no_op < history < mutation
    assert "layer already matches" in body
    assert "return true" in body


def test_pass_99_every_flip_and_rotation_uses_transaction_boundary():
    for name in ("flipLayerH", "flipLayerV", "rotateLayer90", "rotateLayer90CCW", "rotateSelectedLayer180"):
        body = _function_body(name)
        assert "_commitDestructiveLayerTransform" in body, name
        assert "_pushLayerUndo" not in body, name
    assert "return rotateLayer90(layer.id) === true" in _function_body("rotateSelectedLayerCW")


def test_pass_99_locked_180_rotation_is_not_silent():
    body = _function_body("rotateSelectedLayer180")
    assert "if (layer.locked)" in body
    assert "is locked — unlock to rotate" in body


def test_pass_99_runtime_is_cache_busted():
    assert "spb93-layer-transform-transactions-20260717" in HTML
    assert "spb93-adjustment-selection-boundary-20260717" in HTML
