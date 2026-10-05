from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _between(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    end_index = source.index(end, start_index)
    return source[start_index:end_index]


def test_flat_document_clear_resets_private_public_layer_authority_and_routes_zone():
    body = _between(
        CANVAS,
        "function clearPSDDocumentState(reason, options) {",
        "window.clearPSDDocumentState = clearPSDDocumentState;",
    )

    assert "_settleActiveLayerStrokeBeforeTargetChange" in body
    assert "_psdLayers = [];" in body
    assert "_psdLayersLoaded = false;" in body
    assert "_psdData = null;" in body
    assert "_psdPath = null;" in body
    assert "_selectedLayerId = null;" in body
    assert "_publishPSDDocumentState();" in body
    assert "setToolbarEditMode('zone', { silent: true, forceUiRefresh: true" in body


def test_interactive_file_callbacks_commit_or_restore_before_clearing_outgoing_document():
    # The source transaction replaced pre-decode cleanup. Execute all four
    # actual PNG/TGA callback paths, with successful and failed publication.
    import subprocess
    subprocess.run(["node", "tests/source_file_commit_contract.cjs"], cwd=ROOT,
                   check=True, capture_output=True, text=True)


def test_decoded_and_programmatic_flat_loaders_share_the_source_commit_facade():
    data = (ROOT / "paint-booth-1-data.js").read_text(encoding="utf-8")
    decoded = _between(data, "function loadDecodedImageToCanvas(", "// =============================================================================")
    facade = _between(CANVAS, "function _spbCommitSourceFile(", "function _spbTransitionSourceMasks(")
    assert "_spbCommitSourceFile(width, height," in decoded
    assert "SPBSourceFileCommit.run" in facade
    assert "clearPSDDocumentState('direct source import'" in facade


def test_layered_import_keeps_psd_gimp_openraster_extensions_and_new_bundle_token():
    import_block = _between(CANVAS, "async function importPSD() {", "function _decodePSDSourceComposite")
    assert "filter: '.psd,.ora,.xcf'" in import_block
    assert "/\\.(psd|ora|xcf)$/i" in CANVAS
    import re
    assert re.search(r'<script src="paint-booth-3-canvas\.js\?v=[^"\s]+"></script>', HTML)
