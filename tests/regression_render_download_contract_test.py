import base64
import io
import zipfile

from PIL import Image


def _tiny_png_base64():
    img = Image.new("RGBA", (2, 2), (255, 0, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_zip_render_keeps_advertised_tga_downloads_and_scrubs_gear_readme(app_client, tmp_path):
    output_dir = tmp_path / "render_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    response = app_client.post(
        "/render",
        json={
            "paint_image_base64": _tiny_png_base64(),
            "zones": [{"name": "QA ZIP proof", "color": "#ff00ff", "finish": "gloss", "opacity": 1}],
            "iracing_id": "23371",
            "use_custom_number": True,
            "live_link": False,
            "export_zip": True,
            "output_dir": str(output_dir),
            "settings": {},
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    paint_url = data["download_urls"]["car_num_23371"]
    spec_url = data["download_urls"]["car_spec_23371"]
    zip_url = data["export_zip_url"]

    paint_response = app_client.get(paint_url)
    spec_response = app_client.get(spec_url)
    zip_response = app_client.get(zip_url)

    assert paint_response.status_code == 200
    assert spec_response.status_code == 200
    assert zip_response.status_code == 200

    with zipfile.ZipFile(io.BytesIO(zip_response.data)) as package:
        names = set(package.namelist())
        assert "car_num_23371.tga" in names
        assert "car_spec_23371.tga" in names
        readme = package.read("README.txt").decode("utf-8")

    assert "helmet_spec_23371.tga" not in readme
    assert "suit_spec_23371.tga" not in readme
    assert "car_num_23371.tga" in readme
    assert "car_spec_23371.tga" in readme


def test_zip_export_url_percent_encodes_active_car_spaces(app_client, server_module, monkeypatch, tmp_path):
    output_dir = tmp_path / "render_output_space_url"
    output_dir.mkdir(parents=True, exist_ok=True)

    real_load_config = server_module.load_config

    def load_config_with_spaced_active_car():
        cfg = real_load_config()
        cfg["active_car"] = "trucks silverado2019"
        return cfg

    monkeypatch.setattr(server_module, "load_config", load_config_with_spaced_active_car)

    response = app_client.post(
        "/render",
        json={
            "paint_image_base64": _tiny_png_base64(),
            "zones": [{"name": "QA ZIP URL proof", "color": "#ff00ff", "finish": "gloss", "opacity": 1}],
            "iracing_id": "23371",
            "use_custom_number": True,
            "live_link": False,
            "export_zip": True,
            "output_dir": str(output_dir),
            "settings": {},
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["export_zip_url"].endswith(".zip")
    assert " " not in data["export_zip_url"]
    assert "%20" in data["export_zip_url"]

    zip_response = app_client.get(data["export_zip_url"])
    assert zip_response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(zip_response.data)) as package:
        assert "README.txt" in set(package.namelist())


def test_render_ignores_retired_helmet_and_suit_payload_fields(app_client, tmp_path):
    output_dir = tmp_path / "gear_scrub_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    response = app_client.post(
        "/render",
        json={
            "paint_image_base64": _tiny_png_base64(),
            "zones": [{"name": "QA gear scrub", "color": "#00ffff", "finish": "gloss", "opacity": 1}],
            "iracing_id": "24444",
            "use_custom_number": True,
            "helmet_paint_file": str(output_dir / "fake_helmet.tga"),
            "suit_paint_file": str(output_dir / "fake_suit.tga"),
            "output_dir": str(output_dir),
            "settings": {},
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["includes"]["helmet"] is False
    assert data["includes"]["suit"] is False
    assert not any("helmet" in key or "suit" in key for key in data["download_urls"])
    assert not any(path.name.startswith(("helmet", "suit")) for path in output_dir.glob("*.tga"))


def test_zone_spec_source_only_renders_imported_spec_inside_zone(app_client, tmp_path):
    output_dir = tmp_path / "zone_spec_source_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    spec_source = tmp_path / "external_zone_spec.tga"
    Image.new("RGBA", (2, 2), (245, 4, 16, 255)).save(spec_source)

    response = app_client.post(
        "/render",
        json={
            "paint_image_base64": _tiny_png_base64(),
            "zones": [
                {
                    "name": "Imported spec only",
                    "color": "#ff00ff",
                    "zone_spec_map": str(spec_source),
                    "zone_spec_map_strength": 1.0,
                    "intensity": "100",
                }
            ],
            "iracing_id": "25555",
            "use_custom_number": True,
            "live_link": False,
            "output_dir": str(output_dir),
            "settings": {},
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    spec_response = app_client.get(data["download_urls"]["car_spec_25555"])
    assert spec_response.status_code == 200
    rendered = Image.open(io.BytesIO(spec_response.data)).convert("RGBA")
    assert rendered.size == (2, 2)
    pixels = [rendered.getpixel((x, y)) for y in range(rendered.height) for x in range(rendered.width)]
    assert set(pixels) == {(245, 4, 16, 255)}


def test_preview_render_accepts_live_canvas_payload_without_paint_file(app_client):
    response = app_client.post(
        "/preview-render",
        json={
            "paint_image_base64": _tiny_png_base64(),
            "zones": [
                {
                    "name": "Live canvas preview proof",
                    "color": "#ff00ff",
                    "finish": "gloss",
                    "intensity": "100",
                }
            ],
            "preview_scale": 1.0,
            "settings": {},
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["paint_preview"].startswith("data:image/png;base64,")
    assert data["spec_preview"].startswith("data:image/png;base64,")


def test_save_to_keep_copies_current_id_outputs_not_stale_folder_tgas(app_client, tmp_path):
    output_dir = tmp_path / "keep_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    for name in (
        "car_num_11111.tga",
        "car_spec_11111.tga",
        "car_num_22222.tga",
        "car_spec_22222.tga",
        "helmet_11111.tga",
        "suit_11111.tga",
        "paint_base.tga",
        "spec_metallic.tga",
    ):
        (output_dir / name).write_bytes(b"qa-tga")

    response = app_client.post(
        "/save-render-to-keep",
        json={"output_dir": str(output_dir), "iracing_id": "11111"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    saved = data["saved_files"]
    assert any(name.startswith("car_num_11111_") for name in saved)
    assert any(name.startswith("car_spec_11111_") for name in saved)
    assert any(name.startswith("paint_base_") for name in saved)
    assert any(name.startswith("spec_metallic_") for name in saved)

    assert not any("22222" in name for name in saved)
    assert not any(name.startswith("helmet_") or name.startswith("suit_") for name in saved)
