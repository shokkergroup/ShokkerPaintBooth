from pathlib import Path
import struct


REPO = Path(__file__).resolve().parents[1]
STATE_JS = REPO / "paint-booth-2-state-zones.js"
SHOKK_JS = REPO / "paint-booth-7-shokk.js"


def test_default_assets_endpoint_returns_packaged_sources(app_client):
    response = app_client.get("/api/default-assets")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True

    assets = data["assets"]
    starter = Path(assets["starter_psd"])
    blank = Path(assets["blank_canvas_tga"])
    assert starter.is_file()
    assert starter.suffix.lower() == ".psd"
    assert blank.is_file()
    assert blank.name == "blank_canvas_2048_white.tga"


def test_packaged_blank_canvas_is_white_2048_tga(app_client):
    data = app_client.get("/api/default-assets").get_json()
    blank = Path(data["assets"]["blank_canvas_tga"])
    raw = blank.read_bytes()

    assert len(raw) >= 18 + (2048 * 2048 * 3)
    width = struct.unpack_from("<H", raw, 12)[0]
    height = struct.unpack_from("<H", raw, 14)[0]
    bits_per_pixel = raw[16]

    assert (width, height) == (2048, 2048)
    assert bits_per_pixel == 24
    assert raw[18:21] == b"\xff\xff\xff"
    assert raw[-3:] == b"\xff\xff\xff"


def test_preview_tga_can_load_packaged_blank_canvas(app_client):
    data = app_client.get("/api/default-assets").get_json()
    blank_path = data["assets"]["blank_canvas_tga"]
    response = app_client.post("/preview-tga", json={"path": blank_path})

    assert response.status_code == 200
    assert response.mimetype == "image/png"


def test_first_launch_default_no_longer_depends_on_developer_machine_path():
    src = STATE_JS.read_text(encoding="utf-8")

    assert "C:/1Shokker Paint Car Examples" not in src
    assert "/api/default-assets" in src
    assert "_spbResolveRestorePaintFile" in src
    assert "_spbCheckLocalPaintFile" in src


def test_blank_canvas_uses_path_based_source_loader():
    src = SHOKK_JS.read_text(encoding="utf-8")

    assert "blank_canvas_tga" in src
    assert "loadPaintPreviewFromServer(blankPath)" in src
    assert "setCurrentSourcePaintFile(blankPath" in src
    assert "mode=json" in src
