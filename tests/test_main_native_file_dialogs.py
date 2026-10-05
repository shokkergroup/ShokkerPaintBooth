"""Focused release gates for the paid app's native Windows file dialogs."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "electron-app" / "main.js").read_text(encoding="utf-8")
PRELOAD = (ROOT / "electron-app" / "preload.js").read_text(encoding="utf-8")
BRIDGE_PATH = ROOT / "js" / "spb-native-file-dialogs.js"
BRIDGE = BRIDGE_PATH.read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    match = re.search(rf"(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    assert match, name
    depth = 0
    for index in range(match.start(), len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0 and index > match.end():
                return source[match.start() : index + 1]
    raise AssertionError(name)


def _run_node(script: str) -> dict:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")
    result = subprocess.run(
        [node, "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_main_owns_fixed_dialog_contract_and_validates_results() -> None:
    assert "ipcMain.handle('select-source-paint'" in MAIN
    assert "ipcMain.handle('select-iracing-car-folder'" in MAIN
    assert "requireTrustedPaintBoothRenderer(event);" in MAIN
    assert "event.sender !== mainWindow.webContents" in MAIN
    assert "parsed.hostname === '127.0.0.1'" in MAIN
    assert "parsed.port === String(serverPort)" in MAIN
    assert "flat: Object.freeze(['tga', 'png', 'jpg', 'jpeg', 'bmp'])" in MAIN
    assert "layered: Object.freeze(['psd', 'ora', 'xcf'])" in MAIN
    assert "properties: ['openFile']" in MAIN
    assert "properties: ['openDirectory', 'createDirectory']" in MAIN
    assert MAIN.count("dialog.showOpenDialog(mainWindow, options)") >= 2
    assert "selectedExtension" in MAIN and "extensions.includes(selectedExtension)" in MAIN
    assert "fs.statSync(selected).isFile()" in MAIN
    assert "fs.statSync(selected).isDirectory()" in MAIN


def test_trusted_sender_gate_requires_main_window_and_exact_loopback_origin() -> None:
    gate = _function_source(MAIN, "requireTrustedPaintBoothRenderer")
    payload = _run_node(
        f"""
let serverPort = 59876;
const contents = {{getURL: () => 'http://127.0.0.1:59876/'}};
let mainWindow = {{isDestroyed: () => false, webContents: contents}};
{gate}
function verdict(event) {{
  try {{ requireTrustedPaintBoothRenderer(event); return 'allowed'; }}
  catch (error) {{ return error.message; }}
}}
const trusted = verdict({{sender: contents, senderFrame: {{url: 'http://127.0.0.1:59876/'}}}});
const wrongWindow = verdict({{sender: {{getURL: contents.getURL}}, senderFrame: {{url: 'http://127.0.0.1:59876/'}}}});
const wrongPort = verdict({{sender: contents, senderFrame: {{url: 'http://127.0.0.1:59877/'}}}});
mainWindow = {{isDestroyed: () => true, webContents: contents}};
const destroyed = verdict({{sender: contents, senderFrame: {{url: 'http://127.0.0.1:59876/'}}}});
console.log(JSON.stringify({{trusted, wrongWindow, wrongPort, destroyed}}));
"""
    )
    assert payload["trusted"] == "allowed"
    assert "did not come" in payload["wrongWindow"]
    assert "Untrusted" in payload["wrongPort"]
    assert "did not come" in payload["destroyed"]


def test_preload_exposes_bounded_fixed_methods_only() -> None:
    assert "'select-source-paint'" in PRELOAD
    assert "'select-iracing-car-folder'" in PRELOAD
    assert "selectSourcePaint:" in PRELOAD
    assert "selectIRacingCarFolder:" in PRELOAD
    assert "sourcePaintKind(kind)" in PRELOAD
    assert "boundedDialogPath(defaultPath)" in PRELOAD
    assert "pathValue.length <= 4096" in PRELOAD

    payload = _run_node(
        r"""
const fs = require('fs');
const vm = require('vm');
const calls = [];
const exposed = {};
const electron = {
  contextBridge: {exposeInMainWorld(name, value) { exposed[name] = value; }},
  ipcRenderer: {
    invoke(...args) { calls.push(args); return Promise.resolve(null); },
    send() {}, on() {}, removeListener() {}
  },
  webFrame: {setVisualZoomLevelLimits() {}, setZoomFactor() {}}
};
const sandbox = {
  require(name) { if (name === 'electron') return electron; throw new Error(name); },
  process: {platform: 'win32'},
  window: {addEventListener() {}},
  console
};
vm.runInNewContext(fs.readFileSync('electron-app/preload.js', 'utf8'), sandbox);
(async () => {
  await exposed.electronAPI.selectSourcePaint('bogus', 'x'.repeat(5000));
  await exposed.electronAPI.selectSourcePaint('layered', ' C:\\Paints ');
  await exposed.electronAPI.selectIRacingCarFolder(' C:\\iRacing\\paint ');
  console.log(JSON.stringify(calls));
})().catch(error => { console.error(error); process.exit(1); });
"""
    )
    assert payload[0] == ["select-source-paint", {"kind": "flat", "defaultPath": ""}]
    assert payload[1] == ["select-source-paint", {"kind": "layered", "defaultPath": "C:\\Paints"}]
    assert payload[2] == ["select-iracing-car-folder", {"defaultPath": "C:\\iRacing\\paint"}]


def test_client_bridge_routes_both_modes_cancel_and_browser_fallback_only() -> None:
    payload = _run_node(
        r"""
const fs = require('fs');
const vm = require('vm');
const calls = [];
let sourceResult = 'C:\\Paints\\car.tga';
let rejectSource = false;
const storage = {spb_main_file_picker_mode: 'windows'};
const window = {
  openFilePicker(options) { calls.push(['legacy', options.title]); return 'legacy'; },
  showToast(message, kind) { calls.push(['native-error', message, kind]); },
  localStorage: { getItem(key) { return storage[key] || null; }, setItem(key, value) { storage[key] = value; } },
  electronAPI: {
    selectSourcePaint(kind, startPath) {
      calls.push(['source', kind, startPath]);
      return rejectSource ? Promise.reject(new Error('old preload')) : Promise.resolve(sourceResult);
    },
    selectIRacingCarFolder(startPath) {
      calls.push(['folder', startPath]);
      return Promise.resolve('C:\\Users\\Ricky\\Documents\\iRacing\\paint\\arca');
    }
  }
};
vm.runInNewContext(fs.readFileSync('js/spb-native-file-dialogs.js', 'utf8'), {window, document: {readyState: 'complete', getElementById() { return null; }}, console: {warn() {}, error() {}}});
(async () => {
  const picked = path => calls.push(['picked', path]);
  await window.openFilePicker({title: 'Choose a Source Paint', mode: 'file', startPath: 'C:\\Paints', onSelect: picked});
  sourceResult = 'C:\\Paints\\layers.psd';
  await window.openFilePicker({title: 'Open Layered File — .psd', mode: 'file', onSelect: picked});
  await window.openFilePicker({title: 'Select Your Car Paint (TGA / PNG / JPEG / PSD)', mode: 'file', onSelect: picked});
  await window.openFilePicker({title: 'Choose your iRacing Car Folder', mode: 'folder', startPath: 'C:\\iRacing', onSelect: picked});
  sourceResult = null;
  await window.openFilePicker({title: 'Select Source Paint TGA', mode: 'file', onSelect: picked});
  rejectSource = true;
  await window.openFilePicker({title: 'Select Source Paint TGA', mode: 'file', onSelect: picked});
  await window.openFilePicker({title: 'Choose a Reference Texture', mode: 'file', onSelect: picked});
  await Promise.resolve();
  await Promise.resolve();
  console.log(JSON.stringify(calls));
})().catch(error => { console.error(error); process.exit(1); });
"""
    )
    assert ["source", "flat", "C:\\Paints"] in payload
    assert ["source", "layered", ""] in payload
    assert ["source", "all", ""] in payload
    assert ["folder", "C:\\iRacing"] in payload
    assert ["legacy", "Select Source Paint TGA"] not in payload
    assert any(call[0] == "native-error" and "Windows File Explorer could not open" in call[1] for call in payload)
    assert ["legacy", "Choose a Reference Texture"] in payload
    assert payload.count(["picked", "C:\\Paints\\car.tga"]) == 1
    assert payload.count(["picked", "C:\\Paints\\layers.psd"]) == 2
    assert ["picked", "C:\\Users\\Ricky\\Documents\\iRacing\\paint\\arca"] in payload


def test_client_bridge_uses_server_dialog_in_a_browser_tab() -> None:
    """Owner 2026-09-05: the Settings toggle did nothing in a browser tab because only
    the Electron bridge could open a dialog. Without window.electronAPI, 'windows' mode
    must POST to /api/native-dialog; cancel picks nothing (and opens no second picker),
    a server error is reported, non-candidates and 'shokker' mode stay on the legacy picker."""
    payload = _run_node(
        r"""
const fs = require('fs');
const vm = require('vm');
const calls = [];
const storage = {spb_main_file_picker_mode: 'windows'};
const responses = [
  {ok: true, status: 200, body: {success: true, cancelled: true, path: null}},
  {ok: true, status: 200, body: {success: true, cancelled: false, path: 'C:\\Paints\\car.tga'}},
  {ok: false, status: 409, body: {success: false, error: 'A Windows File Explorer window is already open. Finish or cancel it first.'}},
  {ok: true, status: 200, body: {success: true, cancelled: false, path: 'C:\\Users\\Ricky\\Documents\\iRacing\\paint\\arca'}},
];
const window = {
  openFilePicker(options) { calls.push(['legacy', options.title]); return 'legacy'; },
  showToast(message, kind) { calls.push(['toast', message, kind]); },
  localStorage: { getItem(key) { return storage[key] || null; }, setItem(key, value) { storage[key] = value; } },
  fetch(url, init) {
    const body = JSON.parse(init.body);
    calls.push(['fetch', url, init.method, init.headers['X-Shokker-Internal'], body.mode, body.title, body.filter, body.startPath]);
    const next = responses.shift();
    return Promise.resolve({ ok: next.ok, status: next.status, json() { return Promise.resolve(next.body); } });
  }
};
vm.runInNewContext(fs.readFileSync('js/spb-native-file-dialogs.js', 'utf8'), {window, document: {readyState: 'complete', getElementById() { return null; }}, console: {warn() {}, error() {}}});
(async () => {
  const picked = path => calls.push(['picked', path]);
  const tick = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
  await window.openFilePicker({title: 'Choose a Source Paint', mode: 'file', filter: '.tga,.png', startPath: 'C:\\Paints', onSelect: picked}); await tick();
  await window.openFilePicker({title: 'Choose a Source Paint', mode: 'file', filter: '.tga,.png', startPath: 'C:\\Paints', onSelect: picked}); await tick();
  await window.openFilePicker({title: 'Open Layered Paint', mode: 'file', onSelect: picked}); await tick();
  await window.openFilePicker({title: 'Choose your iRacing Car Folder', mode: 'folder', startPath: 'C:\\iRacing', onSelect: picked}); await tick();
  await window.openFilePicker({title: 'Choose a Reference Texture', mode: 'file', onSelect: picked}); await tick();
  window.setMainFilePickerMode('shokker');
  await window.openFilePicker({title: 'Choose a Source Paint', mode: 'file', onSelect: picked}); await tick();
  console.log(JSON.stringify(calls));
})().catch(error => { console.error(error); process.exit(1); });
"""
    )
    fetches = [call for call in payload if call[0] == "fetch"]
    assert len(fetches) == 4
    assert fetches[0][1:] == ["/api/native-dialog", "POST", "1", "file", "Choose a Source Paint", ".tga,.png", "C:\\Paints"]
    assert fetches[3][4:6] == ["folder", "Choose your iRacing Car Folder"]
    assert payload.count(["picked", "C:\\Paints\\car.tga"]) == 1
    assert ["picked", "C:\\Users\\Ricky\\Documents\\iRacing\\paint\\arca"] in payload
    assert any(call[0] == "toast" and "Windows File Explorer could not open" in call[1] and "already open" in call[1] for call in payload)
    assert ["legacy", "Choose a Reference Texture"] in payload
    assert payload.count(["legacy", "Choose a Source Paint"]) == 1
    assert not any(call[0] == "legacy" and call[1] in ("Open Layered Paint", "Choose your iRacing Car Folder") for call in payload)


def test_main_file_picker_setting_persists_and_routes_header_actions() -> None:
    payload = _run_node(
        r"""
const fs = require('fs');
const vm = require('vm');
const calls = [];
const storage = {};
const pickerControl = { value: '' };
const window = {
  openFilePicker(options) { calls.push(['shokker', options.title]); return 'shokker'; },
  localStorage: { getItem(key) { return storage[key] || null; }, setItem(key, value) { storage[key] = value; } },
  showToast(message) { calls.push(['toast', message]); },
  electronAPI: {
    selectSourcePaint(kind) { calls.push(['windows-source', kind]); return Promise.resolve('C:\\Paints\\car.tga'); },
    selectIRacingCarFolder() { calls.push(['windows-folder']); return Promise.resolve(null); }
  }
};
const document = { readyState: 'complete', getElementById(id) { return id === 'mainFilePickerMode' ? pickerControl : null; } };
vm.runInNewContext(fs.readFileSync('js/spb-native-file-dialogs.js', 'utf8'), {window, document, console: {warn() {}, error() {}}});
(async () => {
  const initial = window.getMainFilePickerMode();
  window.selectMainSourcePaint();
  const setWindows = window.setMainFilePickerMode('windows');
  window.selectMainSourcePaint();
  await Promise.resolve();
  await Promise.resolve();
  const setShokker = window.setMainFilePickerMode('unexpected');
  window.selectMainIRacingFolder();
  console.log(JSON.stringify({initial, setWindows, setShokker, stored: storage.spb_main_file_picker_mode, control: pickerControl.value, calls}));
})().catch(error => { console.error(error); process.exit(1); });
"""
    )
    assert payload["initial"] == "shokker"
    assert payload["setWindows"] == "windows"
    assert payload["setShokker"] == "shokker"
    assert payload["stored"] == "shokker"
    assert payload["control"] == "shokker"
    assert ["shokker", "Choose a Source Paint"] in payload["calls"]
    assert ["windows-source", "flat"] in payload["calls"]
    assert ["shokker", "Choose your iRacing Car Folder"] in payload["calls"]


def test_bridge_is_staged_after_canvas_and_runtime_copy_matches() -> None:
    runtime_bridge = ROOT / "electron-app" / "server" / "js" / "spb-native-file-dialogs.js"
    assert BRIDGE_PATH.read_bytes() == runtime_bridge.read_bytes()
    tag = '<script src="js/spb-native-file-dialogs.js?v=spb-native-file-dialogs-20260905a"></script>'
    for relative in ("paint-booth-v2.html", "electron-app/server/paint-booth-v2.html"):
        html = (ROOT / relative).read_text(encoding="utf-8")
        assert tag in html
        assert html.index("paint-booth-3-canvas.js?v=") < html.index(tag)
        assert 'onclick="if(window.selectMainSourcePaint)window.selectMainSourcePaint();else openPaintFilePicker()"' in html
        assert 'onclick="if(window.selectMainIRacingFolder)window.selectMainIRacingFolder();else openOutputFolderPicker()"' in html
        assert 'Browse Source Paint in Windows File Explorer' in html
        assert 'Browse iRacing Car Folder in Windows File Explorer' in html


def test_bridge_exposes_direct_main_header_dialogs() -> None:
    for required in (
        "window.tryOpenNativeFilePicker = tryOpenNativeFilePicker;",
        "window.getMainFilePickerMode = getMainFilePickerMode;",
        "window.setMainFilePickerMode = setMainFilePickerMode;",
        "ensureFilePickerSettingControl",
        "Shokker Browser — image previews",
        "Windows File Explorer",
        "window.selectMainSourcePaint = selectMainSourcePaint;",
        "window.selectMainIRacingFolder = selectMainIRacingFolder;",
        "window.selectMainLayeredPaint = selectMainLayeredPaint;",
        "title: 'Choose a Source Paint'",
        "title: 'Choose your iRacing Car Folder'",
        "title: 'Open Layered Paint'",
    ):
        assert required in BRIDGE


@pytest.mark.parametrize(
    "script",
    [
        ROOT / "electron-app" / "main.js",
        ROOT / "electron-app" / "preload.js",
        BRIDGE_PATH,
        ROOT / "electron-app" / "server" / "js" / "spb-native-file-dialogs.js",
    ],
)
def test_javascript_sources_parse(script: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is unavailable")
    result = subprocess.run(
        [node, "--check", str(script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
