from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    depth = 1
    index = match.end()
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[match.start() : index]


def _function_body(name: str) -> str:
    source = _function_source(name)
    return source[source.index("{") + 1 : -1]


def test_pass_131_alpha_lock_is_visible_and_keyboard_operable_in_layer_panel():
    assert 'class="layer-alpha-lock-toggle"' in CANVAS
    assert 'aria-pressed="${alphaLocked ? \'true\' : \'false\'}"' in CANVAS
    assert "toggleLayerAlphaLock('${l.id}')" in CANVAS
    assert "Lock transparent pixels — paint only inside existing Layer art" in CANVAS
    assert '.layer-alpha-lock-toggle:focus-visible' in CANVAS


def test_pass_131_shared_layer_stroke_path_enforces_lock_live_and_at_commit():
    init = _function_body("_initLayerPaintCanvas")
    flush = _function_body("_flushPaintImageDataToCurrentSurface")
    commit = _function_body("_commitLayerPaint")
    selection = _function_body("_activeSelectionMask")
    assert "if (layer.alphaLock)" in init
    assert "_buildLayerAlphaLockMasks(paintImageData.data, zoneSelection)" in init
    assert "return _activeLayerAlphaLockMask" in selection
    assert "_activeLayerAlphaLockMask" not in flush
    assert "window.SPBPaintCommitBounds.analyze(" in commit
    assert "imgData, originalPixels, originalX, originalY, alphaLockOriginal" in commit
    helper = (ROOT / "js/canvas/layer/paint-commit-bounds.js").read_text(encoding="utf-8")
    assert helper.index("active.data[i * 4 + 3] = originalAlpha[i]") < helper.index("const bounds = alphaBounds(active)")
    assert "_activeLayerCtx.putImageData(imgData, 0, 0)" in commit
    assert commit.count("_activeLayerAlphaLockMask = null") >= 4


def test_pass_131_alpha_lock_mask_intersects_existing_art_with_soft_selection():
    source = _function_source("_buildLayerAlphaLockMasks")
    script = f"""
const before = new Uint8ClampedArray([10,20,30,255, 40,50,60,128, 70,80,90,0]);
{source}
function same(a,b) {{ return a.length === b.length && a.every((v,i) => v === b[i]); }}
const unlocked = _buildLayerAlphaLockMasks(before, null);
if (!same(Array.from(unlocked.originalAlpha), [255,128,0])) throw new Error('exact alpha was not retained');
if (!same(Array.from(unlocked.paintMask), [255,255,0])) throw new Error('transparent pixels were not excluded');
const selected = _buildLayerAlphaLockMasks(before, new Uint8ClampedArray([64,128,255]));
if (!same(Array.from(selected.paintMask), [64,128,0])) throw new Error('selection intersection failed');
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_pass_131_alpha_lock_blocks_eraser_and_clear_before_mutation():
    begin = _function_body("_beginLayerPixelStroke")
    clear = _function_body("_clearLayerWithEraser")
    assert begin.index("layer.alphaLock") < begin.index("_initLayerPaintCanvas()")
    assert "turn α off before erasing" in begin
    assert clear.index("if (layer.alphaLock)") < clear.index("_pushLayerUndo")
    assert "turn α off before clearing" in clear


def test_pass_131_toggle_is_undoable_and_duplicates_preserve_alpha_lock():
    toggle_start = CANVAS.index("window.toggleLayerAlphaLock = function toggleLayerAlphaLock")
    toggle_end = CANVAS.index("window.isLayerAlphaLocked", toggle_start)
    toggle = CANVAS[toggle_start:toggle_end]
    assert toggle.index("_pushLayerStackUndo('Toggle alpha lock')") < toggle.index("L.alphaLock = !L.alphaLock")
    assert "return true" in toggle
    assert CANVAS.count("alphaLock: !!layer.alphaLock") >= 2


def test_pass_131_runtime_is_cache_busted():
    assert "spb93-layer-alpha-lock-20260717" in HTML
    assert "spb93-layer-lock-ui-truth-20260717" in HTML
