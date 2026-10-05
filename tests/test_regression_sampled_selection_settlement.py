import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS_PATH = ROOT / "paint-booth-3-canvas.js"
HTML_PATH = ROOT / "paint-booth-v2.html"
CANVAS = CANVAS_PATH.read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    marker = f"function {name}("
    start = CANVAS.index(marker)
    brace = CANVAS.index("{", start)
    depth = 0
    for index in range(brace, len(CANVAS)):
        char = CANVAS[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return CANVAS[start:index + 1]
    raise AssertionError(f"Unterminated function: {name}")


def test_sampled_selection_settlement_updates_apply_area_and_refreshes_once():
    settlement = _function_source("_settleSampledZoneSelection")
    script = f"""
const zones = [{{ useRegion: false }}];
let activations = 0;
let refreshes = 0;
function autoActivateZoneApplyArea(index, sourceTool) {{
  activations++;
  zones[index].useRegion = true;
  return true;
}}
function _refreshZoneMaskHistoryUI() {{ refreshes++; }}
{settlement}
const selected = _settleSampledZoneSelection(0, 'wand', 652);
const afterSelected = {{ selected, useRegion: zones[0].useRegion, activations, refreshes }};
const empty = _settleSampledZoneSelection(0, 'wand', 0);
process.stdout.write(JSON.stringify({{
  afterSelected,
  afterEmpty: {{ empty, useRegion: zones[0].useRegion, activations, refreshes }}
}}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["afterSelected"] == {
        "selected": True,
        "useRegion": True,
        "activations": 1,
        "refreshes": 1,
    }
    assert data["afterEmpty"] == {
        "empty": False,
        "useRegion": False,
        "activations": 1,
        "refreshes": 2,
    }


def test_all_sampled_zone_selection_tools_use_the_canonical_settlement():
    wand = _function_source("applySampledColorSelection")
    edge = _function_source("applyEdgeRegionSelection")
    grab = _function_source("applyObjectGrabSelection")

    assert "_settleSampledZoneSelection(targetIndex, 'wand', selection.selectedPixels);" in wand
    assert "_settleSampledZoneSelection(targetIndex, 'edge', selection.selectedPixels);" in edge
    assert "_settleSampledZoneSelection(targetIndex, 'grab', selection.selectedPixels);" in grab
    for source in (wand, edge, grab):
        assert "if (typeof triggerPreviewRender" not in source


def test_zone_mask_history_captures_and_restores_apply_area_activation():
    assert CANVAS.count("prevUseRegion: !!zone.useRegion") >= 4
    assert CANVAS.count(
        "if ('prevUseRegion' in entry) zone.useRegion = !!entry.prevUseRegion;"
    ) >= 4


def test_canvas_cache_token_carries_sampled_selection_settlement_fix():
    html = HTML_PATH.read_text(encoding="utf-8")
    assert "paint-booth-3-canvas.js?v=spb-revsig-20260831a" in html
