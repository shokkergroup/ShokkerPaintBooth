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


def test_pass_120_clear_effects_refusals_precede_history_and_mutation():
    body = _function_body("clearAllLayerEffects")
    lock = body.index("if (layer.locked)")
    no_effects = body.index("if (!layer.effects)")
    transaction = body.index("_effectsSessionUndoPushed = true")
    mutation = body.index("layer.effects = null")
    apply_session = body.index("closeLayerEffects()")
    assert lock < no_effects < transaction < mutation < apply_session


def test_pass_120_clear_effects_returns_truthful_result():
    body = _function_body("clearAllLayerEffects")
    assert body.count("return false") >= 4
    assert "return true" in body
    assert "unlock to clear effects" in body
    assert "No layer effects to clear" in body


def test_pass_120_runtime_is_cache_busted():
    assert "spb93-effects-clear-transaction-20260717" in HTML
    assert "spb93-layer-delete-transaction-20260717" in HTML
