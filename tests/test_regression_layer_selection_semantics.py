from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str, next_name: str) -> str:
    start = CANVAS.index(f"function {name}")
    end = CANVAS.index(f"function {next_name}", start)
    return CANVAS[start:end]


def test_selecting_active_layer_is_idempotent_and_deselect_is_explicit():
    select_body = _function_body("selectPSDLayer(", "deselectPSDLayer(")
    deselect_body = _function_body("deselectPSDLayer(noToast)", "_escapeContextHtml(str)")

    assert "_selectedLayerId = layerId;" in select_body
    assert "(_selectedLayerId === layerId) ? null : layerId" not in select_body
    assert "if (_selectedLayerId !== layerId) _settleActiveLayerStrokeBeforeTargetChange();" in select_body
    assert "_selectedLayerId = null;" not in select_body
    assert "_selectedLayerId = null;" in deselect_body
    assert "setToolbarEditMode('zone'" in deselect_body


def test_stale_layer_id_refuses_without_changing_selection():
    select_body = _function_body("selectPSDLayer(", "deselectPSDLayer(")
    target_check = select_body.index("if (!targetLayer)")
    assignment = select_body.index("_selectedLayerId = layerId;")

    assert target_check < assignment
    assert "return false;" in select_body[target_check:assignment]
    assert "return true;" in select_body[assignment:]
    assert re.search(r'<script src="paint-booth-3-canvas\.js\?v=[^"\s]+"></script>', HTML)
