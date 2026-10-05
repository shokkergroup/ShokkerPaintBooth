"""SPB-93 Pass 33: atomic, reversible Clear All region-mask history."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def run_node(script: str) -> dict:
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return json.loads(result.stdout)


def test_batch_snapshot_undo_redo_is_atomic_and_survives_zone_reorder():
    payload = run_node(r"""
const api = require('./js/canvas/zone/zone-mask-history.js');
const zones = [
  {id:'paint', regionMask:new Uint8Array([10,20,30])},
  {id:'glass', regionMask:null},
  {id:'chrome', regionMask:new Uint8Array([40,50,60])},
];
const undo = api.capture(zones, [0,2], 'Clear all drawn regions');
zones[0].regionMask = null; zones[2].regionMask = null;
const redo = api.captureReciprocal(zones, undo);
zones.splice(0, zones.length, zones[2], zones[1], zones[0]);
const undone = api.restore(zones, undo);
const undoState = Object.fromEntries(zones.map(z => [z.id, z.regionMask ? Array.from(z.regionMask) : null]));
const redone = api.restore(zones, redo);
const redoState = Object.fromEntries(zones.map(z => [z.id, z.regionMask ? Array.from(z.regionMask) : null]));
process.stdout.write(JSON.stringify({
  undone, redone, undoState, redoState, count:undo.batchMasks.length, label:undo.label
}));
""")
    assert payload == {
        "undone": 2,
        "redone": 2,
        "undoState": {"chrome": [40, 50, 60], "glass": None, "paint": [10, 20, 30]},
        "redoState": {"chrome": None, "glass": None, "paint": None},
        "count": 2,
        "label": "Clear all drawn regions",
    }


def test_snapshots_are_deep_copies_and_invalid_or_duplicate_indexes_are_ignored():
    payload = run_node(r"""
const api = require('./js/canvas/zone/zone-mask-history.js');
const source = new Uint8Array([1,2,3]);
const zones = [{id:'a',regionMask:source}];
const entry = api.capture(zones,[0,0,-1,99],'x');
source[0]=255;
process.stdout.write(JSON.stringify({count:entry.batchMasks.length,saved:Array.from(entry.batchMasks[0].prevMask)}));
""")
    assert payload == {"count": 1, "saved": [1, 2, 3]}


def test_clear_all_validates_before_history_and_no_longer_uses_zone_config_undo():
    source = read("paint-booth-3-canvas.js")
    start = source.index("function clearAllRegions()")
    end = source.index("// ===== SPATIAL MASK", start)
    clear_all = source[start:end]
    assert "if (!affectedIndexes.length)" in clear_all
    assert clear_all.index("if (!affectedIndexes.length)") < clear_all.index("_pushZoneMaskBatchUndoSnapshot")
    assert clear_all.index("_pushZoneMaskBatchUndoSnapshot") < clear_all.index("zones[index].regionMask = null")
    assert "pushZoneUndo" not in clear_all
    assert "return true" in clear_all


def test_undo_redo_routes_batch_entries_in_tracked_and_legacy_paths():
    source = read("paint-booth-3-canvas.js")
    assert source.count("_applyZoneMaskBatchHistoryEntry(entry, redoStack)") == 2
    assert source.count("_applyZoneMaskBatchHistoryEntry(entry, undoStack)") == 2
    assert "_recordRedoAction('zone-mask')" in source
    assert "_recordUndoAction('zone-mask')" in source
    assert "if (maskEntry.batchMasks) return 'Undo: '" in source
    assert "if (redoMaskEntry.batchMasks) return 'Redo: '" in source


def test_module_loads_before_canvas_and_is_in_two_copy_manifest():
    module = "js/canvas/zone/zone-mask-history.js"
    html = read("paint-booth-v2.html")
    manifest = json.loads(read("scripts/runtime-sync-manifest.json"))["files"]
    assert html.index(f'<script src="{module}') < html.index('<script src="paint-booth-3-canvas.js')
    assert module in manifest


def test_batch_history_module_never_mutates_layer_or_source_pixel_buffers():
    source = read("js/canvas/zone/zone-mask-history.js")
    assert "regionMask" in source
    assert "_psdLayers" not in source
    assert "paintImageData" not in source
    assert "spatialMask" not in source
