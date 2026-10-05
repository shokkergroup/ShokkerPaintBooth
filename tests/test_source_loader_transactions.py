"""Focused guards for the flat/layered source-load transaction boundary."""

import json
import subprocess
from pathlib import Path


CANVAS_PATH = Path("paint-booth-3-canvas.js")


def _source() -> str:
    return CANVAS_PATH.read_text(encoding="utf-8")


def _between(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    finish = text.index(end, begin)
    return text[begin:finish]


def test_source_load_result_schema_and_generation_negative_control():
    """An older flat/PSD request must become non-current immediately."""
    source = _source()
    helpers = _between(
        source,
        "var _spbSourceLoadGeneration = 0;",
        "async function loadPaintPreviewFromServer(tgaPath) {",
    )
    script = f"""
global.window = {{}};
global._psdPath = null;
eval({json.dumps(helpers)});
const older = _spbBeginSourceLoad('C:/paint/older.tga', 'flat');
const newer = _spbBeginSourceLoad('C:/paint/newer.psd', 'layered');
_spbCommittedSourcePath = newer.requestedPath;
_spbCommittedSourceFingerprint = 'sha-newer';
const staleResult = _spbSourceLoadResult(older, false, {{ error: 'superseded by a newer source request' }});
const currentResult = _spbSourceLoadResult(newer, true, {{
  committedPath: newer.requestedPath,
  fingerprint: 'sha-newer'
}});
process.stdout.write(JSON.stringify({{
  olderCurrent: _spbIsCurrentSourceLoad(older),
  newerCurrent: _spbIsCurrentSourceLoad(newer),
  staleResult,
  currentResult,
  staleKeys: Object.keys(staleResult),
  currentKeys: Object.keys(currentResult)
}}));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(proc.stdout)
    expected_keys = [
        "ok",
        "requestedPath",
        "committedPath",
        "generation",
        "fingerprint",
        "error",
    ]
    assert result["olderCurrent"] is False
    assert result["newerCurrent"] is True
    assert result["staleKeys"] == expected_keys
    assert result["currentKeys"] == expected_keys
    assert result["staleResult"]["ok"] is False
    assert result["staleResult"]["committedPath"] == "C:/paint/newer.psd"
    assert result["staleResult"]["error"] == "superseded by a newer source request"
    assert result["currentResult"]["ok"] is True
    assert result["currentResult"]["error"] is None


def test_source_transaction_exports_full_document_rollback_hooks():
    source = _source()
    helpers = _between(
        source,
        "var _spbSourceLoadGeneration = 0;",
        "async function loadPaintPreviewFromServer(tgaPath) {",
    )
    snapshot = _between(
        source,
        "function _spbCaptureSourceDocumentState() {",
        "function _spbUpdateLoadedCanvasUi(canvas, width, height) {",
    )
    assert "captureDocumentState: function ()" in helpers
    assert "restoreDocumentState: function (snapshot)" in helpers
    assert "_spbSourceLoadGeneration += 1" in helpers
    assert "zonesRef:" in snapshot
    assert "selectedZoneIndex:" in snapshot
    assert "selectedLayerIds:" in snapshot
    assert "layerUndoEntries:" in snapshot
    assert "layerRedoEntries:" in snapshot
    assert "historySnapshotPerLayer:" in snapshot
    assert "freeTransformState:" in snapshot
    assert "freeTransformState = snapshot.freeTransformState" in snapshot
    assert "drawTransformHandles()" in snapshot
    assert "zones = snapshot.zonesRef" in snapshot
    assert "uiTextIds.has(id) ? el.textContent : null" in snapshot
    assert "if (state.text !== null) el.textContent = state.text" in snapshot
    assert "el.style.display = state.display;\n        el.textContent = state.text;" not in snapshot


def test_flat_loader_stages_decode_before_identity_and_restores_commit_faults():
    source = _source()
    body = _between(
        source,
        "async function loadPaintPreviewFromServer(tgaPath) {",
        "window.loadPaintPreviewFromServer = loadPaintPreviewFromServer;",
    )
    decode = body.index("await Promise.all([_spbDecodeImage(objectUrl), fingerprintPromise])")
    generation_gate = body.index("if (!_spbIsCurrentSourceLoad(transaction))", decode)
    snapshot = body.index("const previous = _spbCaptureSourceDocumentState()", generation_gate)
    draw = body.index("ctx.drawImage(img, 0, 0)", snapshot)
    identity = body.index("_spbCommittedSourcePath = normalizedPath", draw)
    setter = body.index("setCurrentSourcePaintFile(normalizedPath", identity)
    assert decode < generation_gate < snapshot < draw < identity < setter
    assert "_spbRestoreSourceDocumentState(previous)" in body
    assert "setCurrentSourcePaintFile(normalizedPath, { clearPSD: true" not in body
    assert "return _spbSourceLoadResult(transaction, false" in body
    assert body.index("showToast(`Preview loaded:") > setter


def test_psd_raster_and_decode_faults_cannot_publish_partial_state():
    source = _source()
    body = _between(
        source,
        "async function _doPSDImport(psdPath, importOptions) {",
        "function countLayers(layers)",
    )
    flatten = body.index("psdImportApi.flattenLayerTree")
    source_decode = body.index("await _decodePSDSourceComposite")
    raster_fetch = body.index("/api/psd-rasterize-all")
    raster_failure = body.index("throw new Error('layer rasterization failed", raster_fetch)
    raster_decode = body.index("await Promise.all(stagedLayers.map", raster_failure)
    snapshot = body.index("const previous = _spbCaptureSourceDocumentState()", raster_decode)
    live_pixels = body.index("_spbCompositeLayerStack(liveContext, stagedLayers)", snapshot)
    private_identity = body.index("_psdPath = normalizedPath", live_pixels)
    public_publish = body.index("_publishPSDDocumentState();", private_identity)

    assert flatten < source_decode < raster_fetch < raster_failure < raster_decode
    assert raster_decode < snapshot < live_pixels < private_identity < public_publish
    assert "_psdPath = normalizedPath" not in body[:snapshot]
    assert "_psdData = data" not in body[:snapshot]
    assert "_publishPSDDocumentState();" not in body[:snapshot]
    assert "_spbRestoreSourceDocumentState(previous)" in body
    assert "authoritative source composite was missing or could not be decoded" in body
    assert "superseded by a newer source request" in body
    assert "Previous source kept unchanged." in body


def test_psd_partial_layer_decode_is_truthful_and_source_safe():
    source = _source()
    body = _between(
        source,
        "async function _doPSDImport(psdPath, importOptions) {",
        "function countLayers(layers)",
    )
    assert "missingLayerNames.push" in body
    assert "missingLayers: missingLayerNames.slice()" in body
    assert "{ stageOnly: true }" in body
    assert "opened safely from its source composite" in body
    assert "ready with diagnostics:" in body
    assert "layers decoded; missing:" in body
    assert body.index("_activatePSDSourceCompositeFallback") < body.index("_psdPath = normalizedPath")


def test_change_file_read_and_decode_faults_are_visible_and_mutation_free():
    source = _source()
    body = _between(
        source,
        "function loadPaintImage(input) {",
        "// SHOKK / programmatic load:",
    )
    script = f"""
const assert = require('assert');
let mutations = 0;
const toasts = [];
global._spbBeginSourceLoad = () => ({{ generation: 1 }});
global._spbIsCurrentSourceLoad = () => true;
global.markFlatPaintLiveSource = () => {{ mutations += 1; }};
global.loadDecodedImageToCanvas = () => {{ mutations += 1; }};
global.clearPSDDocumentState = () => {{ mutations += 1; }};
global.showToast = (message, isError) => toasts.push({{ message: String(message), isError: !!isError }});
global.document = {{ getElementById() {{ throw new Error('document mutation should be unreachable'); }} }};
global.decodeTGA = () => {{ throw new Error('decode should be unreachable on read failure'); }};
global.Image = class {{}};
eval({json.dumps(body)});

global.FileReader = class {{
  readAsArrayBuffer() {{ this.onerror({{ target: this }}); }}
  readAsDataURL() {{ this.onerror({{ target: this }}); }}
}};
loadPaintImage({{ files: [{{ name: 'broken.tga' }}] }});
loadPaintImage({{ files: [{{ name: 'broken.png' }}] }});

global.FileReader = class {{
  readAsDataURL() {{ this.onload({{ target: {{ result: 'data:image/png;base64,broken' }} }}); }}
}};
global.Image = class {{
  set src(value) {{ this.onerror(new Error('synthetic decode fault')); }}
}};
loadPaintImage({{ files: [{{ name: 'undecodable.png' }}] }});

assert.strictEqual(mutations, 0);
assert.strictEqual(toasts.length, 3);
assert(toasts.every(item => item.isError));
assert(toasts.every(item => item.message.includes('current document was left unchanged')));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert proc.stdout == ""
