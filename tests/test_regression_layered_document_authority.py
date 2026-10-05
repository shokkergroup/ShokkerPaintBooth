import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
MANIFEST = (ROOT / "scripts/runtime-sync-manifest.json").read_text(encoding="utf-8")


def test_layered_import_chooses_photoshop_style_initial_target_and_safe_fallback():
    script = r"""
const api = require('./js/canvas/layer/document-capability.js');
const img = {};
const layers = [
  {id:'bottom', img, visible:true, locked:false},
  {id:'middle', img, visible:true, locked:false},
  {id:'top-locked', img, visible:true, locked:true}
];
const normal = api.chooseInitialLayer(layers, null);
layers.push({id:'hidden-editable', img, visible:false, locked:false});
const visibleWins = api.chooseInitialLayer(layers, null);
const fallback = api.chooseInitialLayer([
  {id:'hidden', img, visible:false, locked:false},
  {id:'source', img, visible:true, locked:true, importSafetyBase:true}
], {active:true});
process.stdout.write(JSON.stringify({normal:normal.id, visibleWins:visibleWins.id, fallback:fallback.id}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True
    )
    assert json.loads(result.stdout) == {
        "normal": "middle",
        "visibleWins": "middle",
        "fallback": "source",
    }


def test_private_and_public_layer_document_state_publish_together():
    publish_start = CANVAS.index("function _publishPSDDocumentState()")
    publish_end = CANVAS.index("window._publishPSDDocumentState", publish_start)
    publish = CANVAS[publish_start:publish_end]
    importer_start = CANVAS.index("async function _doPSDImport(psdPath)")
    importer_end = CANVAS.index("function countLayers", importer_start)
    importer = CANVAS[importer_start:importer_end]

    for field in (
        "window._psdData = _psdData",
        "window._psdPath = _psdPath",
        "window._psdLayers = _psdLayers",
        "window._psdLayersLoaded = !!_psdLayersLoaded",
        "window._psdImportSafety = _psdImportSafety",
        "window._selectedLayerId = _selectedLayerId",
    ):
        assert field in publish

    assert importer.count("_publishPSDDocumentState();") >= 5
    assert "documentCapability.chooseInitialLayer(_psdLayers, _psdImportSafety)" in importer
    assert "_selectedLayerId = initialLayer ? initialLayer.id : null;" in importer
    assert "setToolbarEditMode(_psdImportSafety ? 'zone' : 'layer'" in importer


def test_layer_document_capability_runtime_is_loaded_and_packaged():
    assert "js/canvas/layer/document-capability.js?v=spb93-layer-document-authority-20260808a" in HTML
    assert "paint-booth-3-canvas.js?v=spb93-tool-gauntlet-20260808ab" in HTML
    assert '"js/canvas/layer/document-capability.js"' in MANIFEST

    for relative in (
        "js/canvas/layer/document-capability.js",
        "paint-booth-3-canvas.js",
        "paint-booth-v2.html",
    ):
        assert (ROOT / relative).read_bytes() == (ROOT / "electron-app/server" / relative).read_bytes()
