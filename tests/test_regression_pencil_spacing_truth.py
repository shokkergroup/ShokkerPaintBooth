"""SPB-93 Pass 106 — visible Pencil spacing controls actual dab spacing."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_pencil_interpolator_consumes_the_visible_spacing_slider():
    script = r"""
const fs=require('fs');
const text=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=text.indexOf('let _pencilLastX = null');
const end=text.indexOf("if (typeof window !== 'undefined')", start);
let spacing='25', count=0;
global.document={getElementById(id){return {value:id==='brushSize'?'10':spacing};}};
function paintPencil(){count++;}
eval(text.slice(start,end));
_pencilStrokeTo(0,0,false); _pencilStrokeTo(100,0,false);
const dense=count;
_resetPencilStroke(); count=0; spacing='200';
_pencilStrokeTo(0,0,false); _pencilStrokeTo(100,0,false);
process.stdout.write(JSON.stringify({dense,sparse:count}));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True,
                            capture_output=True, check=True)
    assert json.loads(result.stdout) == {"dense": 41, "sparse": 6}


def test_pencil_spacing_is_bounded_and_runtime_is_current():
    start = CANVAS.index("function _pencilStrokeTo")
    end = CANVAS.index("function _resetPencilStroke", start)
    source = CANVAS[start:end]
    assert "document.getElementById('brushSpacing')" in source
    assert "Math.max(1, Math.min(200" in source
    assert "radius * spacingPct / 100" in source
    assert "spb93-recolor-layer-sample-20260717" in HTML
    assert "spb93-pencil-spacing-truth-20260717" in HTML
    assert (ROOT / "paint-booth-3-canvas.js").read_bytes() == (
        ROOT / "electron-app/server/paint-booth-3-canvas.js"
    ).read_bytes()
