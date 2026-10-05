from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_active_tool_options_use_one_stable_horizontal_rail():
    css = (ROOT / "css" / "spb-tool-options-rail.css").read_text(encoding="utf-8")
    html = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")

    assert "spb-tool-options-rail.css?v=spb-tool-rail-20260809b" in html
    assert "SPB-93 / 2026-08-09" in css
    assert "height: 78px !important" in css
    assert "flex-wrap: nowrap !important" in css
    assert "overflow-x: auto !important" in css
    assert "overflow-y: hidden !important" in css
    assert "scrollbar-gutter: stable" in css


def test_tool_specific_and_context_controls_cannot_shrink_or_wrap_out_of_reach():
    css = (ROOT / "css" / "spb-tool-options-rail.css").read_text(encoding="utf-8")

    assert "#toolSpecificOptions > *" in css
    assert "#contextActionsBar > *" in css
    assert "flex-shrink: 0 !important" in css
    assert "#toolOptionsBar > #toolSpecificOptions," in css
    assert "#toolOptionsBar > #contextActionsBar {" in css
    assert "min-width: max-content !important" in css
    assert "flex: 0 0 auto !important" in css
