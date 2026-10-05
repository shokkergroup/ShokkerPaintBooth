"""SPB-93 Pass 80: Pattern Brush selection is race-safe and fail-safe."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_load_generation_helper_rejects_stale_pattern_completions():
    start = CANVAS.index("function _isPatternBrushLoadCurrent")
    helper = CANVAS[start : CANVAS.index("function _installPatternBrushTexture", start)]
    script = f"""
var _patternBrushLoadToken = 4;
var _patternBrushName = 'crosshatch';
{helper}
console.log(JSON.stringify({{
  current: _isPatternBrushLoadCurrent(4, 'crosshatch'),
  oldToken: _isPatternBrushLoadCurrent(3, 'crosshatch'),
  oldName: _isPatternBrushLoadCurrent(4, 'carbon')
}}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == {"current": True, "oldToken": False, "oldName": False}


def test_loader_clears_old_texture_and_guards_server_and_image_completion():
    start = CANVAS.index("function loadPatternBrush")
    loader = CANVAS[start : CANVAS.index("// Cached texture data", start)]
    assert "const token = ++_patternBrushLoadToken" in loader
    assert loader.index("_patternBrushTexture = null") < loader.index("fetch('/api/render-pattern-tile'")
    assert "if (!_isPatternBrushLoadCurrent(token, patternName)) return false" in loader
    assert "if (!r.ok) throw new Error" in loader
    assert "if (!data || !data.image) throw new Error" in loader
    assert "img.onerror" in loader
    assert "_buildProceduralPatternBrush(patternName)" in loader
    assert "Promise.resolve(false)" in loader


def test_strokes_wait_instead_of_silently_using_solid_or_previous_texture():
    start = CANVAS.index("function paintColorBrush")
    brush = CANVAS[start : CANVAS.index("function paintRecolor", start)]
    assert "if (_patternBrushLoadingName && _patternBrushName !== 'none')" in brush
    assert brush.index("return false") < brush.index("const data = paintImageData.data")
    assert "Pattern brush is still loading" in brush


def test_pass_80_runtime_is_cache_busted_and_mirrored():
    assert "spb93-pattern-brush-loading-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
