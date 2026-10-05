"""/api/native-dialog - the server-side Windows chooser behind the File Picker setting.

Owner 2026-09-05 ("BETA LAUNCH PREP"): the Settings toggle between SHOKKER BROWSER and
WINDOWS FILE EXPLORER did nothing in a browser tab because only the Electron preload
bridge could open a dialog. These tests pin the route contract with the PowerShell
child faked (no window is opened); the real dialog is exercised manually / by the
harness in the scratchpad, never in the suite.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import pytest
from flask import Flask

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server_routes import file_picker_routes  # noqa: E402

HEADERS = {"X-Shokker-Internal": "1"}


@pytest.fixture()
def client():
    app = Flask("spb-native-dialog-test")
    file_picker_routes.register_file_picker_routes(
        app, load_config=lambda: {}, logger=logging.getLogger("spb-test"),
    )
    app.testing = True
    with app.test_client() as test_client:
        yield test_client


class _Proc:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _fake_powershell(result_line, *, returncode=0, stderr=b"", capture=None):
    """Fake subprocess.run: write `result_line` where the real script would."""

    def run(cmd, **kwargs):
        env = kwargs["env"]
        if capture is not None:
            capture.update({"cmd": cmd, "env": env, "kwargs": kwargs})
        if result_line is not None:
            Path(env["SPB_DLG_OUT"]).write_text(result_line, encoding="utf-8")
        return _Proc(returncode=returncode, stderr=stderr)

    return run


@pytest.fixture(autouse=True)
def _windows_only(monkeypatch):
    monkeypatch.setattr(file_picker_routes.sys, "platform", "win32")


def test_requires_internal_header(client):
    response = client.post("/api/native-dialog", json={"mode": "file"})
    assert response.status_code == 403
    assert response.get_json()["success"] is False


def test_non_windows_reports_501(client, monkeypatch):
    monkeypatch.setattr(file_picker_routes.sys, "platform", "linux")
    response = client.post("/api/native-dialog", json={"mode": "file"}, headers=HEADERS)
    assert response.status_code == 501


def test_cancel_is_success_with_cancelled_flag(client, monkeypatch):
    monkeypatch.setattr(file_picker_routes.subprocess, "run", _fake_powershell("CANCEL"))
    response = client.post("/api/native-dialog", json={"mode": "folder", "title": "Choose your iRacing Car Folder"}, headers=HEADERS)
    assert response.status_code == 200
    body = response.get_json()
    assert body == {"success": True, "cancelled": True, "mode": "folder", "path": None}


def test_file_pick_validates_extension_and_passes_filter(client, monkeypatch, tmp_path):
    tga = tmp_path / "car.tga"
    tga.write_bytes(b"x")
    captured = {}
    monkeypatch.setattr(file_picker_routes.subprocess, "run", _fake_powershell(f"PATH:{tga}", capture=captured))
    response = client.post(
        "/api/native-dialog",
        json={"mode": "file", "title": "Choose a Source Paint", "filter": ".tga,.png,.jpg,.jpeg,.bmp", "startPath": str(tga)},
        headers=HEADERS,
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["success"] is True and body["cancelled"] is False
    assert os.path.normcase(body["path"]) == os.path.normcase(str(tga))
    env = captured["env"]
    assert env["SPB_DLG_MODE"] == "file"
    assert env["SPB_DLG_FILTER"] == "Paint files (*.tga;*.png;*.jpg;*.jpeg;*.bmp)|*.tga;*.png;*.jpg;*.jpeg;*.bmp"
    # a file startPath is reduced to its folder before it reaches the dialog
    assert os.path.normcase(env["SPB_DLG_START"]) == os.path.normcase(str(tmp_path))
    cmd = captured["cmd"]
    assert "-STA" in cmd and "-EncodedCommand" in cmd and "-NonInteractive" in cmd
    assert captured["kwargs"]["timeout"] == 15 * 60


def test_file_pick_rejects_unsupported_extension(client, monkeypatch, tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("x")
    monkeypatch.setattr(file_picker_routes.subprocess, "run", _fake_powershell(f"PATH:{bad}"))
    response = client.post("/api/native-dialog", json={"mode": "file", "filter": ".tga,.png"}, headers=HEADERS)
    assert response.status_code == 400
    assert "not a supported source file" in response.get_json()["error"]


def test_folder_pick_returns_existing_directory_only(client, monkeypatch, tmp_path):
    monkeypatch.setattr(file_picker_routes.subprocess, "run", _fake_powershell(f"PATH:{tmp_path}"))
    ok = client.post("/api/native-dialog", json={"mode": "folder"}, headers=HEADERS)
    assert ok.status_code == 200
    assert os.path.normcase(ok.get_json()["path"]) == os.path.normcase(str(tmp_path))

    monkeypatch.setattr(file_picker_routes.subprocess, "run", _fake_powershell(f"PATH:{tmp_path / 'missing'}"))
    missing = client.post("/api/native-dialog", json={"mode": "folder"}, headers=HEADERS)
    assert missing.status_code == 400


def test_powershell_failure_is_reported_not_swallowed(client, monkeypatch):
    monkeypatch.setattr(file_picker_routes.subprocess, "run", _fake_powershell("ERROR:Add-Type exploded"))
    response = client.post("/api/native-dialog", json={"mode": "folder"}, headers=HEADERS)
    assert response.status_code == 500
    assert "Add-Type exploded" in response.get_json()["error"]

    monkeypatch.setattr(file_picker_routes.subprocess, "run", _fake_powershell(None, returncode=1, stderr=b"boom\r\n"))
    response = client.post("/api/native-dialog", json={"mode": "folder"}, headers=HEADERS)
    assert response.status_code == 500
    assert "boom" in response.get_json()["error"]


def test_invalid_filter_tokens_are_dropped(client, monkeypatch, tmp_path):
    png = tmp_path / "car.png"
    png.write_bytes(b"x")
    captured = {}
    monkeypatch.setattr(file_picker_routes.subprocess, "run", _fake_powershell(f"PATH:{png}", capture=captured))
    response = client.post(
        "/api/native-dialog",
        json={"mode": "file", "filter": ".png, *.PNG, ../etc, .a|b, .tga"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert captured["env"]["SPB_DLG_FILTER"] == "Paint files (*.png;*.tga)|*.png;*.tga"


def test_powershell_source_is_self_contained():
    src = file_picker_routes.NATIVE_DIALOG_PS
    assert "FOS_PICKFOLDERS" in src and "OpenFileDialog" in src
    assert "System.Windows.Forms.FolderBrowserDialog" in src  # classic fallback
    assert src.count("'@") == 1 and src.count("@'") == 1  # exactly one C# here-string
    for line in src.splitlines():
        if line.strip() in ("@'", "'@"):
            assert line == line.strip(), "PowerShell here-string terminators must start at column 0"
