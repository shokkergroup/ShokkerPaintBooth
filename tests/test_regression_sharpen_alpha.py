from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_sharpen_does_not_treat_transparency_as_black_edge_detail():
    script = r"""
const fs=require('fs');
const text=fs.readFileSync('paint-booth-3-canvas.js','utf8');
const start=text.indexOf('function applySharpen(amount)');
const end=text.indexOf('function applyNoiseAdd',start);
const pixels=new Uint8ClampedArray(9*4);
pixels[16]=100; pixels[17]=50; pixels[18]=25; pixels[19]=255;
const imageData={data:pixels};
const ctx={getImageData(){return imageData;},putImageData(){}};
const target={canvas:{width:3,height:3},ctx};
function _getAdjustmentTarget(){return target;}
function _commitAdjustment(){return true;}
function showToast(){}
eval(text.slice(start,end));
applySharpen(50);
process.stdout.write(JSON.stringify(Array.from(pixels.slice(16,20))));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert json.loads(result.stdout) == [100, 50, 25, 255]


def test_pass_60_source_contract_and_runtime_mirror():
    start = CANVAS.index("function applySharpen(amount)")
    sharpen = CANVAS[start:CANVAS.index("function applyNoiseAdd", start)]
    assert "const weight = upA + downA + leftA + rightA" in sharpen
    assert "if (weight <= 0) continue" in sharpen
    assert "spb93-alpha-aware-sharpen-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
