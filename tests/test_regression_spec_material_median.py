"""SPB-93 Pass 116: robust local sampling for noisy M/R/CC/A maps."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def test_local_median_rejects_single_flake_outlier_without_changing_point_mode():
    script = r"""
const api = require('./js/canvas/zone/spec-material-sampler.js');
const data = [];
for (let i=0;i<25;i++) data.push(40,80,120,255);
data.splice((12*4),4, 250,5,240,20);
const image={width:5,height:5,data:new Uint8ClampedArray(data)};
console.log(JSON.stringify({
  point:api.sampleMedianAt(image,2,2,1),
  median3:api.sampleMedianAt(image,2,2,3),
  median5:api.sampleMedianAt(image,2,2,5),
  invalid:api.normalizeSampleSize(7)
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    payload = json.loads(result.stdout)
    assert payload["point"] == {"x": 2, "y": 2, "m": 250, "r": 5, "cc": 240, "a": 20}
    for key, size in (("median3", 3), ("median5", 5)):
        assert payload[key] == {
            "x": 2, "y": 2, "sampleSize": size,
            "m": 40, "r": 80, "cc": 120, "a": 255,
        }
    assert payload["invalid"] == 1


def test_inspector_offers_point_and_robust_local_material_sampling():
    assert 'id="specMaterialSampleSize"' in HTML
    assert '<option value="1" selected>Point</option>' in HTML
    assert '<option value="3">3×3 Median</option>' in HTML
    assert '<option value="5">5×5 Median</option>' in HTML
    assert "local median rejects isolated flake and texture outliers" in HTML


def test_pass_116_module_token_and_runtime_mirrors_are_current():
    assert "spec-material-sampler.js?v=spb93-spec-tools-live-preview-20260808a" in HTML
    server = ROOT / "electron-app/server"
    for relative in ("paint-booth-v2.html", "js/canvas/zone/spec-material-sampler.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
