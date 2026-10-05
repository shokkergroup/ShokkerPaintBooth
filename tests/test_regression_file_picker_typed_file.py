from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
SERVER_CANVAS = (ROOT / "electron-app/server/paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")
SERVER_HTML = (ROOT / "electron-app/server/paint-booth-v2.html").read_text(encoding="utf-8")


def _body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start = match.end()
    depth = 1
    index = start
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start:index - 1]


def test_typed_file_path_bypasses_directory_scan_and_selects_directly():
    body = _body("filePickerGoTypedPath")
    match = body.index("_filePickerTypedPathIsAllowedFile(path)")
    select = body.index("filePickerSelect()")
    navigate = body.index("filePickerNavigate(path)")
    assert match < select < navigate
    assert "_filePickerSelectedPath = path" in body
    assert "filePickerSelectBtn').disabled = false" in body


def test_typed_layered_filters_accept_psd_ora_xcf_suffix_list():
    body = _body("_filePickerTypedPathIsAllowedFile")
    assert ".split(/[,;|\\s]+/)" in body
    assert "suffix.startsWith('.')" in body
    assert "lower.endsWith(normalized)" in body


def test_enter_and_go_share_the_truthful_typed_path_controller():
    picker_start = HTML.index('id="filePickerPath"')
    picker_end = HTML.index("<!-- ===== TOAST ===== -->", picker_start)
    picker = HTML[picker_start:picker_end]
    assert "event.preventDefault();filePickerGoTypedPath();" in picker
    assert 'onclick="filePickerGoTypedPath();"' in picker
    assert "filePickerNavigate(v)" not in picker


def test_layered_import_labels_the_real_psd_xcf_or_ora_format():
    body = _body("_doPSDImport")
    assert "['PSD', 'XCF', 'ORA'].includes(layeredExt)" in body
    assert "`${layeredLabel} ready:" in body
    assert "'Loading ' + layeredLabel" in body
    assert "PSD/XCF/ORA</button>" in HTML
    assert 'aria-label="Import layered PSD, XCF, or ORA file"' in HTML


def test_typed_file_runtime_pairs_and_cache_token_match():
    assert CANVAS == SERVER_CANVAS
    assert HTML == SERVER_HTML
    assert "paint-booth-3-canvas.js?v=spb93-tool-gauntlet-20260808ab" in HTML
