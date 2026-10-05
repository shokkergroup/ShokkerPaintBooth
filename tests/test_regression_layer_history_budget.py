import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
MODULE = ROOT / "js/canvas/layer/history-budget.js"


def _run_budget(entry_sizes, *, min_entries=5, max_entries=30, byte_budget=96 * 1024 * 1024):
    script = r"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const sizes = JSON.parse(process.argv[2]);
const stack = sizes.map((size, index) => ({
  type: 'image',
  label: 'edit ' + index,
  imgCanvas: { width: size, height: 1 }
}));
const evicted = [];
const sandbox = {};
vm.runInNewContext(source, sandbox);
const result = sandbox.SPBLayerHistoryBudget.trim(stack, {
  minEntries: Number(process.argv[3]),
  maxEntries: Number(process.argv[4]),
  byteBudget: Number(process.argv[5]),
  onEvict(entry) { evicted.push(entry.label); }
});
process.stdout.write(JSON.stringify({ result, labels: stack.map(e => e.label), evicted }));
"""
    result = subprocess.run(
        [
            "node", "-e", script, str(MODULE), json.dumps(entry_sizes),
            str(min_entries), str(max_entries), str(byte_budget),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_small_cropped_layer_edits_keep_more_than_the_old_five_step_cap():
    payload = _run_budget([120_000] * 8)
    assert payload["result"]["entries"] == 8
    assert payload["evicted"] == []


def test_full_canvas_edits_stay_inside_the_memory_budget_without_dropping_below_five():
    # entryBytes multiplies width * height * 4; these model ten 2048² RGBA snapshots.
    payload = _run_budget([2048 * 2048] * 10)
    assert payload["result"]["entries"] == 6
    assert payload["result"]["bytes"] == 96 * 1024 * 1024
    assert payload["evicted"] == ["edit 0", "edit 1", "edit 2", "edit 3"]


def test_stack_snapshot_does_not_charge_images_still_retained_by_the_live_document():
    script = r"""
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const sandbox = {};
vm.runInNewContext(source, sandbox);
const liveA = { width: 2048, height: 2048 };
const liveB = { width: 2048, height: 2048 };
const stack = [{ type: 'stack', snapshot: [{ img: liveA }, { img: liveB }], label: 'add blank layer' }];
for (let i = 0; i < 8; i++) stack.push({ type: 'image', imgCanvas: { width: 300, height: 100 }, label: 'brush ' + i });
const result = sandbox.SPBLayerHistoryBudget.trim(stack, {
  minEntries: 5,
  maxEntries: 30,
  byteBudget: 96 * 1024 * 1024,
  retainedSources: [liveA, liveB]
});
process.stdout.write(JSON.stringify({ result, labels: stack.map(e => e.label) }));
"""
    result = subprocess.run(
        ["node", "-e", script, str(MODULE)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["result"]["entries"] == 9
    assert payload["labels"][0] == "add blank layer"


def test_runtime_wires_budget_before_canvas_and_prunes_matching_visible_history():
    token = "js/canvas/layer/history-budget.js?v=spb93-adaptive-layer-history-20260808b"
    assert token in HTML
    assert HTML.index(token) < HTML.index('src="paint-booth-3-canvas.js?v=')
    assert "var _LAYER_UNDO_MIN = 5;" in CANVAS
    assert "var _LAYER_UNDO_MAX = 30;" in CANVAS
    assert "var _LAYER_UNDO_BYTE_BUDGET = 96 * 1024 * 1024;" in CANVAS
    # Image, normal stack, captured modal stack, and both Redo branches trim.
    assert CANVAS.count("_trimLayerUndoHistory();") == 5
    assert "retainedSources: _currentLayerHistoryRetainedSources()" in CANVAS
    assert "window._discardOldestUndoAction = _discardOldestUndoAction" in CANVAS
    assert "window._discardOldestUndoAction('layer')" in CANVAS


def test_new_runtime_module_is_byte_identical_in_the_packaged_tree():
    packaged = ROOT / "electron-app/server/js/canvas/layer/history-budget.js"
    assert MODULE.read_bytes() == packaged.read_bytes()
