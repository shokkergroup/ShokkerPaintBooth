"""SPB-93 Pass 40: pasted layers never masquerade as transform lifts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = "js/canvas/layer/clipboard-layer.js"
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")
MANIFEST = json.loads((ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8"))


def _node(script: str):
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def _span(start: str, end: str) -> str:
    start_index = CANVAS.index(start)
    return CANVAS[start_index : CANVAS.index(end, start_index)]


def test_only_explicit_transform_lifts_retain_a_source_layer_link():
    data = _node(
        r"""
const api=require('./js/canvas/layer/clipboard-layer.js');
const copied={sourceLayerId:'paint-layer-7'};
process.stdout.write(JSON.stringify({
  paste:api.linkedSourceLayerId(copied,{}),
  viaCopy:api.linkedSourceLayerId(copied,{linkSourceLayer:false}),
  transform:api.linkedSourceLayerId(copied,{linkSourceLayer:true}),
  missing:api.linkedSourceLayerId({}, {linkSourceLayer:true}),
  invalid:api.linkedSourceLayerId({sourceLayerId:42},{linkSourceLayer:true})
}));
"""
    )
    assert data == {
        "paste": None,
        "viaCopy": None,
        "transform": "paint-layer-7",
        "missing": None,
        "invalid": None,
    }


def test_layer_creation_requires_opt_in_and_only_transform_selection_opts_in():
    creator = _span("function _createLayerFromClipboardData", "function _clearSelectionFromLayer")
    assert "SPBClipboardLayer.linkedSourceLayerId(data, opts)" in creator
    assert "opts.linkSourceLayer === true" in creator

    pasted = _span("function pasteAsLayer", "function applyAutoFeatherToSelection")
    via_copy = _span("function newLayerViaCopy", "function addLayerFromFile")
    lifted = _span("function liftSelectionToNewLayer", "function transformSelectedLayerRegion")
    assert "linkSourceLayer" not in pasted
    assert "linkSourceLayer" not in via_copy
    assert "linkSourceLayer: true" in lifted


def test_clipboard_contract_is_loaded_before_canvas_and_packaged():
    tag = f"{MODULE}?v=spb93-selection-aware-paste-20260716"
    assert tag in HTML
    assert HTML.index(tag) < HTML.index("paint-booth-3-canvas.js?v=")
    assert "spb93-selection-aware-paste-20260716" in HTML
    assert MODULE in MANIFEST["files"]


def test_root_and_packaged_clipboard_runtime_are_byte_identical():
    for relative in (MODULE, "paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (
            ROOT / "electron-app" / "server" / relative
        ).read_bytes()
