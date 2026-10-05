import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
PLACEMENT = (ROOT / "js" / "zones" / "zone-placement-controls.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
MANIFEST = (ROOT / "scripts" / "runtime-sync-manifest.json").read_text(encoding="utf-8")


def test_latest_async_pump_runs_one_request_and_then_only_one_pending_request():
    script = r"""
(async function () {
  const api = require('./js/canvas/latest-async-pump.js');
  const releases = [];
  let calls = 0;
  const pump = api.create(async () => {
    calls++;
    await new Promise((resolve) => releases.push(resolve));
  });
  pump.request();
  await new Promise((resolve) => setTimeout(resolve, 5));
  pump.request();
  pump.request();
  const duringFirst = calls;
  releases.shift()();
  await new Promise((resolve) => setTimeout(resolve, 5));
  const afterFirst = calls;
  releases.shift()();
  await new Promise((resolve) => setTimeout(resolve, 5));
  process.stdout.write(JSON.stringify({ duringFirst, afterFirst, finalCalls: calls, pending: pump.hasPending() }));
})();
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    proof = json.loads(result.stdout)
    assert proof == {"duringFirst": 1, "afterFirst": 2, "finalCalls": 2, "pending": False}


def test_both_zone_placement_drag_paths_request_interactive_preview_without_trailing_debounce():
    setup = CANVAS[
        CANVAS.index("function setupCanvasHandlers(canvas)") :
        CANVAS.index("// ===== CACHED CANVAS RECT")
    ]
    assert "triggerPreviewRender({ interactive: true });" in setup
    assert "placementPreviewTimer" not in setup
    assert "triggerPreviewRender({ interactive: true });" in PLACEMENT
    assert "placementOverlayPreviewTimer" not in PLACEMENT


def test_overlay_placement_click_jitter_does_not_create_fake_undo_or_preview():
    down = PLACEMENT[
        PLACEMENT.index("placementOverlayDragStart = {") :
        PLACEMENT.index("function onPlacementOverlayMove(e)")
    ]
    move = PLACEMENT[
        PLACEMENT.index("function onPlacementOverlayMove(e)") :
        PLACEMENT.index("function onPlacementOverlayUp()")
    ]
    up = PLACEMENT[
        PLACEMENT.index("function onPlacementOverlayUp()") :
        PLACEMENT.index("function setPercentOffset")
    ]
    assert "pushZoneUndo" not in down
    assert move.index("if (screenDistance < 4) return;") < move.index("pushZoneUndo('', true);")
    assert move.index("pushZoneUndo('', true);") < move.index("zone.patternOffsetX = nx;")
    assert "if (didMove) triggerPreviewRender({ interactive: true });" in up


def test_interactive_preview_pump_is_loaded_packaged_and_bypasses_settle_debounce():
    module_token = "js/canvas/latest-async-pump.js?v=spb93-latest-async-preview-20260808a"
    placement_token = "js/zones/zone-placement-controls.js?v=spb93-interactive-placement-preview-20260808a"
    assert module_token in HTML
    assert placement_token in HTML
    assert HTML.index(module_token) < HTML.index('<script src="paint-booth-3-canvas.js?v=')
    assert '"js/canvas/latest-async-pump.js"' in MANIFEST

    trigger = CANVAS[
        CANVAS.index("function triggerPreviewRender(options)") :
        CANVAS.index("function _previewEmptyState()")
    ]
    interactive = trigger.index("if (options && options.interactive)")
    normal_debounce = trigger.index("_schedulePreviewStages();")
    assert interactive < normal_debounce
    assert "_interactivePreviewPump.request();" in trigger
