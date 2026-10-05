from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_gaussian_blur_keeps_color_saturated_across_transparent_edges():
    script = r"""
const fs=require('fs');
const text=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=text.indexOf('function applyGaussianBlur(radius)');
const end=text.indexOf('function applySharpen',start);
const pixels=new Uint8ClampedArray([
  0,0,0,0,
  255,0,0,255,
  0,0,0,0
]);
const imageData={data:pixels};
const ctx={getImageData(){return imageData;},putImageData(){}};
const target={canvas:{width:3,height:1},ctx};
function _getAdjustmentTarget(){return target;}
function _commitAdjustment(){return true;}
function showToast(){}
eval(text.slice(start,end));
applyGaussianBlur(1);
const out=[];
for(let i=0;i<pixels.length;i+=4) out.push(Array.from(pixels.slice(i,i+4)));
process.stdout.write(JSON.stringify(out));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    output = json.loads(result.stdout)
    assert any(pixel[3] > 0 for pixel in output)
    for red, green, blue, alpha in output:
        if alpha > 0:
            assert (red, green, blue) == (255, 0, 0)


def test_pass_59_source_contract_and_runtime_mirror():
    blur_start = CANVAS.index("function applyGaussianBlur(radius)")
    blur = CANVAS[blur_start:CANVAS.index("function applySharpen", blur_start)]
    assert "tmp[si] * sampleAlpha" in blur
    assert "rr / aa" in blur
    assert "spb93-premultiplied-gaussian-blur-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
