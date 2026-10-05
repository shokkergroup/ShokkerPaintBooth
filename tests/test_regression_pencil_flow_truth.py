from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_span(signature: str, next_marker: str) -> str:
    start = CANVAS.index(signature)
    end = CANVAS.index(next_marker, start)
    return CANVAS[start:end]


def test_pencil_consumes_flow_through_shared_dynamics_contract():
    pencil = _function_span("function paintPencil", "window.paintPencil")
    assert "getElementById('brushFlow')" in pencil
    assert "_resolveBrushDynamics(requestedSize, opacityBase, flow)" in pencil
    assert "const opacity = pencilDynamics.opacity" in pencil


def test_ui_never_claims_that_pencil_ignores_a_control_it_consumes():
    warning = _function_span("function maybeWarnFlowIgnored", "window.maybeWarnFlowIgnored")
    assert "var TOOLS_IGNORING_FLOW = [];" in warning
    assert "['pencil']" not in warning


def test_pass_52_runtime_is_cache_busted_and_mirrored():
    assert "spb93-pencil-flow-truth-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
