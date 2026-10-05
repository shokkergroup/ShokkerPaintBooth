"""Structural release gates for the standalone SHOKK DEMO Electron product."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "electron-demo"
PACKAGE = DEMO / "package.json"
PACKAGE_LOCK = DEMO / "package-lock.json"
PRODUCT_MANIFEST = ROOT / "demo" / "product-manifest.json"
MAIN = DEMO / "src" / "main.js"
PRELOAD = DEMO / "src" / "preload.js"
STAGER = DEMO / "stage.js"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_package_is_a_distinct_stage_only_product() -> None:
    demo = _json(PACKAGE)
    paid = _json(ROOT / "electron-app" / "package.json")
    build = demo["build"]

    assert demo["name"] == "shokker-paint-booth-shokk-demo"
    assert demo["main"] == ".stage/app/main.js"
    assert build["appId"] == "com.shokker.paintbooth.shokkdemo"
    assert build["appId"] != paid["build"]["appId"]
    assert build["productName"] == "Shokker Paint Booth - SHOKK DEMO"
    assert build["productName"] != paid["build"]["productName"]
    assert build["executableName"] == "ShokkerPaintBoothShokkDemo"

    nsis = build["nsis"]
    assert nsis["guid"] == "1af98625-2cd1-4d66-baf3-d878c7d2c90e"
    assert nsis["shortcutName"] == "Shokker Paint Booth - SHOKK DEMO"
    assert nsis["uninstallDisplayName"] == "Shokker Paint Booth - SHOKK DEMO"
    assert "SHOKK-DEMO" in build["win"]["artifactName"]

    assert build["files"]
    assert build["files"][0] == ".stage/app/**/*"
    assert "!node_modules/**/*.map" in build["files"]
    assert build["extraResources"]
    assert all(str(item["from"]).startswith(".stage/") for item in build["extraResources"])
    assert build["extraResources"][0]["to"] == "shokk-demo-server"

    publish = build["publish"]
    assert publish["url"].endswith("/shokk-demo")
    assert publish["url"] != paid["build"]["publish"]["url"]
    assert publish["channel"] == "shokk-demo"

    assert demo["scripts"]["stage"] == "node stage.js"
    assert demo["scripts"]["prestart"] == "npm run stage"
    assert demo["scripts"]["prebuild"] == "npm run stage"
    packaged_text = json.dumps(build).lower()
    for forbidden in ("license.html", "license-preload", "spb-license-secrets", "contributor"):
        assert forbidden not in packaged_text


def test_release_version_is_identical_across_manifest_package_and_lock() -> None:
    package = _json(PACKAGE)
    package_lock = _json(PACKAGE_LOCK)
    manifest = _json(PRODUCT_MANIFEST)
    version = manifest["product"]["version"]

    assert version == package["version"]
    assert version == package_lock["version"]
    assert version == package_lock["packages"][""]["version"]
    assert manifest["product"]["build_id"]


def test_stager_uses_only_the_dedicated_demo_builder_and_stage() -> None:
    source = STAGER.read_text(encoding="utf-8")

    assert "demo', 'build_demo_stage.py" in source
    assert "'--output', STAGE_DIR" in source
    assert "path.join(STAGE_DIR, 'server')" in source
    assert "path.join(STAGED_SERVER, 'demo_server.py')" in source
    assert "path.join(STAGE_DIR, 'app')" in source
    assert "fs.copyFileSync" in source
    assert "electron-app" not in source
    assert "server.py" not in source.replace("demo_server.py", "")
    assert "SPB_DEMO_PYTHON" in source
    assert "['-3']" in source


def test_main_process_has_independent_runtime_identity() -> None:
    source = MAIN.read_text(encoding="utf-8")

    assert "const SERVER_PORT = 59886;" in source
    assert "const SERVER_HOST = '127.0.0.1';" in source
    assert "com.shokker.paintbooth.shokkdemo.single-instance" in source
    assert "requestSingleInstanceLock({ identity: SINGLE_INSTANCE_ID })" in source
    assert "app.setPath('userData', USER_DATA_DIR)" in source
    assert "app.setPath('sessionData', CACHE_DIR)" in source
    assert "app.setAppLogsPath(LOG_DIR)" in source
    assert "appendSwitch('disk-cache-dir', CACHE_DIR)" in source
    assert "appendSwitch('autoplay-policy', 'no-user-gesture-required')" in source
    assert "partition: 'persist:shokk-demo-v1'" in source
    assert "path.join(process.resourcesPath, 'shokk-demo-server')" in source
    assert "path.resolve(__dirname, '..', 'server')" in source
    assert "path.join(serverDir, 'demo_server.py')" in source
    assert "if (app.isPackaged)" in source
    assert "Bundled demo Python is missing" in source
    assert "/api/demo/health" in source
    assert "payload.product === 'shokk-demo'" in source
    assert "PYTHONDONTWRITEBYTECODE: '1'" in source
    assert "X-SPB-Demo-Token" in source
    assert "webRequest.onBeforeSendHeaders" in source

    for forbidden in (
        "59876",
        "com.shokker.paintbooth.v6",
        "electron-app/server",
        "spb-license-secrets",
        "license-submit",
        "license-bypass",
        "contributor-build",
        "setAsDefaultProtocolClient",
        "shokker://",
    ):
        assert forbidden not in source


def test_browser_window_and_navigation_are_fail_closed() -> None:
    source = MAIN.read_text(encoding="utf-8")

    required_defaults = (
        "contextIsolation: true",
        "nodeIntegration: false",
        "sandbox: true",
        "webSecurity: true",
        "allowRunningInsecureContent: false",
        "webviewTag: false",
        "navigateOnDragDrop: false",
        "devTools: false",
    )
    for setting in required_defaults:
        assert setting in source

    assert "setPermissionRequestHandler" in source
    assert "setPermissionCheckHandler(() => false)" in source
    assert "webRequest.onBeforeRequest" in source
    assert "setWindowOpenHandler" in source
    assert "return { action: 'deny' }" in source
    assert "will-navigate" in source
    assert "will-attach-webview" in source
    assert "requireTrustedSender(event)" in source


def test_external_links_are_an_exact_three_url_allowlist() -> None:
    source = MAIN.read_text(encoding="utf-8")
    urls = set(re.findall(r"https://[^'\"`\s]+", source))

    assert urls == {
        "https://payhip.com/b/AHgpV",
        "https://discord.gg/GwXxyhwtDu",
        "https://shokkergroup.com",
    }
    assert "ALLOWED_EXTERNAL_URLS.has(url)" in source
    assert "ALLOWED_EXTERNAL_URLS.has(String(rawUrl || ''))" in source
    assert "^https?" not in source


def test_preload_exposes_only_the_demo_bridge() -> None:
    source = PRELOAD.read_text(encoding="utf-8")
    main_source = MAIN.read_text(encoding="utf-8")
    handles = set(re.findall(r"ipcMain\.handle\('([^']+)'", main_source))

    assert handles == {
        "shokk-demo:runtime-info",
        "shokk-demo:select-source-file",
        "shokk-demo:select-iracing-folder",
        "shokk-demo:open-external",
        "shokk-demo:reveal-path",
    }
    assert "exposeInMainWorld('shokkDemo'" in source
    for method in (
        "getRuntimeInfo",
        "selectSourceFile",
        "selectIRacingFolder",
        "openExternal",
        "revealPath",
    ):
        assert f"{method}:" in source

    for forbidden in (
        "electronAPI",
        "electronLicense",
        "ipcRenderer.send",
        "ipcRenderer.on",
        "list-dir",
        "open-path",
        "license",
        "contributor",
    ):
        assert forbidden not in source

    assert "approvedSourceFiles" in main_source
    assert "approvedRevealRoots" in main_source
    assert "standardIRacingRoots" in main_source
    assert "sourceApproved" in main_source
    assert "outputApproved" in main_source


@pytest.mark.parametrize("script", [STAGER, MAIN, PRELOAD])
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
