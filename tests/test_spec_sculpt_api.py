"""Flask integration smoke tests for Spec Sculpt API routes."""

from __future__ import annotations

import io
import json
import os
import re
import uuid
import base64
from pathlib import Path

import numpy as np
from PIL import Image

from engine.registry import BASE_REGISTRY


def test_spec_sculpt_server_keeps_every_easy_preview_cache_entry(server_module):
    easy_client = (
        Path(__file__).resolve().parents[1] / "js" / "features" / "spb-easy-sculpt.js"
    ).read_text(encoding="utf-8")
    match = re.search(r"previewCacheOrder\.length > (\d+)", easy_client)
    assert match is not None
    assert server_module.SPEC_SCULPT_JOBS_RETENTION >= int(match.group(1))


def test_spec_sculpt_analyze_json_paint_file(app_client, tmp_paint_file):
    response = app_client.post(
        "/api/spec-sculpt/analyze",
        json={"paint_file": tmp_paint_file},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["original_resolution"] == [64, 64]
    assert data["is_exact_2048"] is False
    assert data["easy_eligible"] is False
    assert data.get("preview_data_url", "").startswith("data:image/jpeg;base64,")


def test_spec_sculpt_analyze_sanitizes_browser_upload_name(app_client):
    payload = io.BytesIO()
    Image.new("RGB", (64, 64), (25, 90, 170)).save(payload, format="PNG")
    payload.seek(0)
    response = app_client.post(
        "/api/spec-sculpt/analyze",
        data={"paint_file": (payload, "nested/path/paint.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.get_json()["filename"] == "paint.png"


def test_spec_sculpt_browser_upload_is_not_rejected_at_the_global_16mb_limit(
    app_client,
    monkeypatch,
    server_module,
    tmp_path,
):
    # A normal layered 2048 PSD can be much larger than 16 MB. Invalid bytes are
    # sufficient here: the image decoder may reject them, but the request must
    # reach that decoder instead of dying at Flask's unrelated global ceiling.
    upload_temp = tmp_path / f"large_upload_{uuid.uuid4().hex}"
    upload_temp.mkdir()
    monkeypatch.setattr(server_module, "SPB_TEMP_FOLDER", str(upload_temp))
    payload = io.BytesIO(b"not-a-real-psd" + b"x" * (17 * 1024 * 1024))
    response = app_client.post(
        "/api/spec-sculpt/analyze",
        data={"paint_file": (payload, "large-template.psd")},
        content_type="multipart/form-data",
    )
    assert response.status_code != 413
    assert list(upload_temp.iterdir()) == []


def test_spec_sculpt_preview_does_not_require_iracing_identity(app_client, tmp_paint_file):
    response = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": tmp_paint_file,
            "save_tga": False,
            "strict2048": False,
            "mode": "zoned",
            "zoned_drama": 1.0,
            "preview_tex_size": 512,
            "seed": 811,
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["success"] is True
    assert data["sculpt"]["mode"] == "zoned"
    assert data["sculpt"]["zoned_drama"] == 1.0
    assert data["previews"]["composite"].startswith("data:image/png;base64,")


def test_easy_preview_composes_multiple_named_color_materials(app_client, tmp_path):
    paint = np.zeros((64, 64, 3), dtype=np.uint8)
    paint[:, :32] = [230, 25, 25]
    paint[:, 32:] = [20, 40, 225]
    path = tmp_path / "two_color_paint.png"
    Image.fromarray(paint, mode="RGB").save(path)
    response = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": str(path),
            "save_tga": False,
            "strict2048": False,
            "preview_tex_size": 512,
            "mode": "zoned",
            "seed": 9551,
            "material_impact": "bold",
            "easy_color_layers": [
                {
                    "slot_id": "red",
                    "color": [230, 25, 25],
                    "tolerance": 18,
                    "kind": "preset",
                    "look_id": "mirror_chrome",
                    "material_scale": 0.5,
                },
                {
                    "slot_id": "blue",
                    "color": [20, 40, 225],
                    "tolerance": 18,
                    "kind": "preset",
                    "look_id": "matte_silk",
                    "material_scale": 0.75,
                },
            ],
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    sculpt = response.get_json()["sculpt"]
    assert sculpt["material_impact"] == "bold"
    report = sculpt["easy_color_layers"]
    assert [row["slot_id"] for row in report] == ["red", "blue"]
    assert all(row["matched"] is True for row in report)
    assert all(45 < row["coverage_pct"] < 55 for row in report)
    assert all(len(row["material_means"]) == 3 for row in report)
    assert all(len(row["material_deviations"]) == 3 for row in report)
    assert all(0.0 <= value <= 1.0 for row in report for value in row["material_means"])


def test_spec_sculpt_batch_previews_signature_modes_on_the_loaded_paint(app_client, tmp_paint_file):
    response = app_client.post(
        "/api/spec-sculpt/batch",
        json={
            "paint_file": tmp_paint_file,
            "preview_size": 192,
            "seed": 811,
            "variations": [
                {"label": "Smart Materials", "mode": "zoned"},
                {"label": "FRACTURE", "mode": "fracture"},
                {"label": "Candy Depth", "mode": "candy_depth"},
            ],
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["success"] is True
    assert [row["mode"] for row in data["variations"]] == ["zoned", "fracture", "candy_depth"]
    assert all(
        row["previews"].get("render", "").startswith("data:image/png;base64,")
        for row in data["variations"]
    )


def test_exact_recommendation_tile_tracks_the_clicked_material_recipe(app_client, tmp_paint_file):
    seed = 424242
    scale = 0.55
    batch = app_client.post(
        "/api/spec-sculpt/batch",
        json={
            "paint_file": tmp_paint_file,
            "preview_size": 192,
            "seed": seed,
            "chromatic_shift": True,
            "variations": [
                {
                    "label": "Mirror Chrome",
                    "presets": [["mirror_chrome", 1]],
                    "seed": seed,
                    "material_scale": scale,
                    "exact": True,
                }
            ],
        },
        content_type="application/json",
    )
    clicked = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": tmp_paint_file,
            "save_tga": False,
            "strict2048": False,
            "preview_tex_size": 512,
            "seed": seed,
            "chromatic_shift": True,
            "preset_stack": [{"id": "mirror_chrome", "weight": 100}],
            "material_scale": scale,
        },
        content_type="application/json",
    )
    assert batch.status_code == 200, batch.get_data(as_text=True)
    assert clicked.status_code == 200, clicked.get_data(as_text=True)
    batch_row = batch.get_json()["variations"][0]
    batch_map = batch_row["previews"]["composite"]
    clicked_map = clicked.get_json()["previews"]["composite"]
    assert batch_row["seed"] == seed
    assert batch_row["presets"] == [["mirror_chrome", 1.0]]

    def decode_map(data_url):
        raw = base64.b64decode(data_url.split(",", 1)[1])
        return np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"), dtype=np.float32)

    # The tile is deliberately 192² while the clicked Easy preview is 512², so
    # pixels cannot be byte-identical. The same recipe must retain its
    # material-channel character across those resolutions.
    tile = decode_map(batch_map)
    full = decode_map(clicked_map)
    assert tile.shape == (192, 192, 3)
    assert full.shape == (512, 512, 3)
    assert np.allclose(tile.mean(axis=(0, 1)), full.mean(axis=(0, 1)), atol=18)
    assert np.allclose(tile.std(axis=(0, 1)), full.std(axis=(0, 1)), atol=22)


def test_batch_color_recommendations_change_only_the_active_paint_color(app_client, tmp_path):
    paint = np.zeros((64, 64, 3), dtype=np.uint8)
    paint[:, :32] = [230, 25, 25]
    paint[:, 32:] = [20, 40, 225]
    path = tmp_path / "recommend_one_color.png"
    Image.fromarray(paint, mode="RGB").save(path)
    base = {"kind": "mode", "look_id": "zoned", "seed": 111, "material_scale": 1.0}

    def variation(label, look_id, seed):
        return {
            "label": label,
            "presets": [[look_id, 1]],
            "seed": seed,
            "exact": True,
            "easy_base": base,
            "easy_color_layers": [
                {
                    "slot_id": "red",
                    "color": [230, 25, 25],
                    "tolerance": 18,
                    "kind": "preset",
                    "look_id": look_id,
                    "seed": seed,
                    "material_scale": 1.0,
                }
            ],
        }

    response = app_client.post(
        "/api/spec-sculpt/batch",
        json={
            "paint_file": str(path),
            "preview_size": 192,
            "variations": [
                variation("Mirror red", "mirror_chrome", 222),
                variation("Matte red", "matte_silk", 333),
            ],
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    rows = response.get_json()["variations"]
    assert all(row["easy_color_layers"][0]["matched"] is True for row in rows)

    def decode(data_url):
        raw = base64.b64decode(data_url.split(",", 1)[1])
        return np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"), dtype=np.uint8)

    mirror = decode(rows[0]["previews"]["composite"])
    matte = decode(rows[1]["previews"]["composite"])
    assert np.array_equal(mirror[:, 130:], matte[:, 130:]), "The untouched blue/base material must stay fixed."
    assert np.mean(np.abs(mirror[:, :80].astype(np.int16) - matte[:, :80].astype(np.int16))) > 8


def test_easy_strict_2048_rejects_preview_before_sculpt(app_client, tmp_paint_file):
    response = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": tmp_paint_file,
            "save_tga": False,
            "strict2048": True,
            "mode": "zoned",
            "preview_tex_size": 512,
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data["code"] == "easy_requires_2048"
    assert data["original_resolution"] == [64, 64]
    assert "2048x2048" in data["error"]


def test_spec_sculpt_generate_json_writes_job_tgas(app_client, tmp_paint_file, monkeypatch, server_module, tmp_path):
    out_root = tmp_path / f"spec_sculpt_api_{uuid.uuid4().hex}"
    out_root.mkdir(parents=True)
    monkeypatch.setattr(server_module, "OUTPUT_FOLDER", str(out_root))
    monkeypatch.setattr(server_module, "SPEC_SCULPT_JOBS_DIR", str(out_root / "shokker_spec_sculpt"))
    os.makedirs(server_module.SPEC_SCULPT_JOBS_DIR, exist_ok=True)

    response = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": tmp_paint_file,
            "iracing_id": "23371",
            "use_custom_number": True,
            "chromatic_shift": False,
            "seed": 4242,
            "save_tga": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["success"] is True
    assert data.get("job_id")
    pp = (data.get("paint_path") or "").replace("\\", "/")
    sp = (data.get("spec_path") or "").replace("\\", "/")
    assert "shokker_spec_sculpt" in pp
    assert "car_num_23371.tga" in pp
    assert "car_spec_23371.tga" in sp
    assert os.path.isfile(data["paint_path"])
    assert os.path.isfile(data["spec_path"])
    assert data.get("previews", {}).get("composite", "").startswith("data:image/png;base64,")
    preview_payload = data["previews"]["composite"].split(",", 1)[1]
    assert Image.open(io.BytesIO(base64.b64decode(preview_payload))).size == (512, 512)
    assert Image.open(Path(data["paint_path"]).parent / "PREVIEW_spec.png").size == (512, 512)
    sc = data.get("sculpt") or {}
    assert sc.get("finish_id", "").startswith("spec_sculpt_")
    assert sc.get("seed_effective") == 4242
    assert sc.get("preset_stack") == []


def test_spec_sculpt_generate_catalog_registry_blend(app_client, tmp_paint_file, monkeypatch, server_module, tmp_path):
    out_root = tmp_path / f"spec_sculpt_cat_{uuid.uuid4().hex}"
    out_root.mkdir(parents=True)
    monkeypatch.setattr(server_module, "OUTPUT_FOLDER", str(out_root))
    monkeypatch.setattr(server_module, "SPEC_SCULPT_JOBS_DIR", str(out_root / "shokker_spec_sculpt"))
    os.makedirs(server_module.SPEC_SCULPT_JOBS_DIR, exist_ok=True)

    fid = sorted(BASE_REGISTRY.keys())[0]
    response = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": tmp_paint_file,
            "iracing_id": "23371",
            "chromatic_shift": True,
            "seed": 222,
            "save_tga": True,
            "catalog_stack": [{"id": fid, "weight": 1}],
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["success"] is True
    sc = data.get("sculpt") or {}
    assert sc.get("blend_mode") == "catalog_registry"
    assert len(sc.get("catalog_stack") or []) == 1
    assert sc.get("catalog_stack")[0]["id"] == fid


def test_spec_sculpt_catalog_index_ok(app_client):
    response = app_client.get("/api/spec-sculpt/catalog-index")
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("success") is True
    assert data.get("complete") is True
    assert data.get("warning") == ""
    assert data.get("counts", {}).get("bases", 0) > 0
    assert data.get("counts", {}).get("specials", 0) > 0
    assert sum(data.get("counts", {}).values()) >= 2400, "A fresh server must publish the expanded catalog, not the pre-render subset."
    assert all("description" in row for row in data.get("bases", [])[:20])
    rows = (data.get("bases") or []) + (data.get("specials") or [])
    descriptions = "\n".join(row.get("description") or "" for row in rows)
    assert "WEAK-" not in descriptions and "BASE-" not in descriptions
    assert "GGX-FIX" not in descriptions and "FLAG-IND" not in descriptions
    assert all(token not in descriptions for token in ("CC=", "M=", "R=", "M/R/CC"))
    assert not re.search(
        r"(?i)\b(?:paint_fn|spec_fn|flat[- ]?fix|owner\s+(?:hue|rated|doctored|proof|\d)|cc\s+fixed|hardmode[-_]|matl[-_]|lazy[-_]|warn[-_])",
        descriptions,
    )
    assert not re.search(r"\(\s*$", descriptions, flags=re.MULTILINE)
    satin = next(row for row in rows if row.get("id") == "satin")
    assert satin["description"] and "sheen" in satin["description"].lower()
    by_id = {row["id"]: row for row in rows}
    assert by_id["pf_bright_canary_glass"]["name"].startswith("Prism Forge ")
    assert by_id["f_anodized"]["name"] == "Foundation Anodized"
    assert by_id["enh_anodized"]["name"] == "Enhanced Anodized"
    assert "oxide" in by_id["enh_anodized"]["description"].lower()
    assert by_id["msh_peach_jellyshock"]["name"].startswith("MONEY SHOKK ")
    assert by_id["mshx_blueprint_jackpot"]["name"].startswith("MONEY SHOKK ")
    assert by_id["p_coronal"]["name"] == "PARADIGM Coronal Mass Ejection"
    assert by_id["od_drab"]["name"] == "OD Drab"
    assert by_id["forged_carbon_vis"]["name"].endswith("Visible")
    assert by_id["fd_anglerfish"]["name"].startswith("Fractured Deep ")
    assert by_id["fd_azure_celestial"]["name"].startswith("Forbidden Dragon ")
    assert by_id["gf_x_1024293_6391"]["name"].startswith("Grunge & Fun Artwork ")
    assert "1024293" not in by_id["gf_x_1024293_6391"]["name"]
    from engine.spec_sculpt.catalog_blend import normalize_catalog_stack

    unselectable = [
        row["id"] for row in rows
        if normalize_catalog_stack([[row["id"], 1.0]]) != [(row["id"], 1.0)]
    ]
    assert not unselectable, f"Every Easy catalog card must resolve when clicked: {unselectable[:10]}"
    assert by_id["ui_stw_3c4c676f_02"]["name"] == "SHOKK Drop Voronoi Beach · Jelly Iridescent"
    assert by_id["ui_chatgpt_image_jun_16_2026_03_01_34_pm"]["name"] == "SHOKK Drop Custom Artwork"
    assert by_id["fd_abyssalsnow"]["name"] == "Fractured Deep Abyssal Snow"
    assert not any(re.search(r"\b\d{6,}\b", row["name"]) for row in rows)

    # Some suite fixtures intentionally exercise the pre-expansion registry.
    # Test optional-pack naming directly so that isolation does not depend on
    # which lazy expansion another test loaded first.
    from server import _easy_catalog_name

    assert _easy_catalog_name("grd_chromatic_aberration") == "Gradient Chromatic Aberration"
    assert _easy_catalog_name("aniso_circular_chrome").startswith("Anisotropic ")
    assert _easy_catalog_name("anime2_screentone") == "Anime Manga Screentone"
    assert _easy_catalog_name("anime2_speed_lines") == "Anime Speed Lines: Action Burst"
    assert _easy_catalog_name("anime2_energy_aura") == "Anime Energy Aura: Ki Charge"
    assert _easy_catalog_name("anime2_crystal") == "Anime Crystal Facet: Jewel Shards"
    assert _easy_catalog_name("anime2_gradient_hair") == "Anime Gradient Hair: Gloss Strands"
    assert _easy_catalog_name("materials2_carbon") == "Materials & Physics Carbon Twill Weave"
    assert _easy_catalog_name("optics2_aurora") == "Light & Optics Aurora Veil"
    assert _easy_catalog_name("neon2_circuit_city") == "Neon Underground Copper Ghost"


def test_shipping_named_preset_route_has_no_blank_thumbnail_cards(app_client):
    response = app_client.get("/api/spec-sculpt/presets")
    assert response.status_code == 200
    rows = response.get_json().get("presets") or []
    thumb_root = Path(__file__).resolve().parents[1] / "thumbnails" / "spec_sculpt_presets"
    manifest = json.loads((thumb_root / "_manifest.json").read_text(encoding="utf-8"))
    shipped_ids = [row["id"] for row in manifest["thumbs"]]
    assert manifest["count"] == len(shipped_ids) == 175
    assert set(shipped_ids).issubset({row["id"] for row in rows})
    missing = [preset_id for preset_id in shipped_ids if not (thumb_root / f"{preset_id}.png").is_file()]
    assert missing == []


def test_spec_sculpt_generate_fusion_catalog_and_scratch(app_client, tmp_paint_file, monkeypatch, server_module, tmp_path):
    out_root = tmp_path / f"spec_sculpt_fusion_{uuid.uuid4().hex}"
    out_root.mkdir(parents=True)
    monkeypatch.setattr(server_module, "OUTPUT_FOLDER", str(out_root))
    monkeypatch.setattr(server_module, "SPEC_SCULPT_JOBS_DIR", str(out_root / "shokker_spec_sculpt"))
    os.makedirs(server_module.SPEC_SCULPT_JOBS_DIR, exist_ok=True)

    fid = sorted(BASE_REGISTRY.keys())[0]
    response = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": tmp_paint_file,
            "iracing_id": "23371",
            "chromatic_shift": False,
            "seed": 333,
            "save_tga": True,
            "catalog_stack": [{"id": fid, "weight": 1}],
            "preset_stack": [{"id": "mirror_chrome", "weight": 1}],
            "fusion_mix": 0.4,
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["success"] is True
    sc = data.get("sculpt") or {}
    assert sc.get("blend_mode") == "fusion_registry_scratch"
    assert sc.get("fusion_mix") == 0.4
    assert any("fusion" in w for w in (data.get("warnings") or [])) is False


def test_spec_sculpt_generate_preset_stack_blend(app_client, tmp_paint_file, monkeypatch, server_module, tmp_path):
    out_root = tmp_path / f"spec_sculpt_blend_{uuid.uuid4().hex}"
    out_root.mkdir(parents=True)
    monkeypatch.setattr(server_module, "OUTPUT_FOLDER", str(out_root))
    monkeypatch.setattr(server_module, "SPEC_SCULPT_JOBS_DIR", str(out_root / "shokker_spec_sculpt"))
    os.makedirs(server_module.SPEC_SCULPT_JOBS_DIR, exist_ok=True)

    response = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": tmp_paint_file,
            "iracing_id": "23371",
            "chromatic_shift": True,
            "seed": 777,
            "save_tga": True,
            "preset_stack": [
                {"id": "mirror_chrome", "weight": 2},
                {"id": "forged_carbon", "weight": 1},
            ],
        },
        content_type="application/json",
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["success"] is True
    sc = data.get("sculpt") or {}
    assert len(sc.get("preset_stack") or []) == 2


def test_spec_sculpt_generate_json_car_prefix_without_custom_numbers(app_client, tmp_paint_file, monkeypatch, server_module, tmp_path):
    out_root = tmp_path / f"spec_sculpt_car_{uuid.uuid4().hex}"
    out_root.mkdir(parents=True)
    monkeypatch.setattr(server_module, "OUTPUT_FOLDER", str(out_root))
    monkeypatch.setattr(server_module, "SPEC_SCULPT_JOBS_DIR", str(out_root / "shokker_spec_sculpt"))
    os.makedirs(server_module.SPEC_SCULPT_JOBS_DIR, exist_ok=True)

    response = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": tmp_paint_file,
            "iracing_id": "23371",
            "use_custom_number": False,
            "chromatic_shift": False,
            "seed": 1,
            "save_tga": True,
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    pp = (data.get("paint_path") or "").replace("\\", "/")
    assert "car_23371.tga" in pp
    assert "car_num_23371.tga" not in pp


def test_easy_generate_recolors_paint_and_pushes_exact_pair_to_output_dir(
    app_client,
    tmp_paint_file,
    monkeypatch,
    server_module,
    tmp_path,
):
    out_root = tmp_path / f"spec_sculpt_recolor_{uuid.uuid4().hex}"
    jobs_root = out_root / "shokker_spec_sculpt"
    target = tmp_path / f"iracing_car_{uuid.uuid4().hex}"
    jobs_root.mkdir(parents=True)
    target.mkdir(parents=True)
    monkeypatch.setattr(server_module, "OUTPUT_FOLDER", str(out_root))
    monkeypatch.setattr(server_module, "SPEC_SCULPT_JOBS_DIR", str(jobs_root))

    response = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": tmp_paint_file,
            "iracing_id": "23371",
            "use_custom_number": True,
            "save_tga": True,
            "output_dir": str(target),
            "mode": "zoned",
            "easy_color_layers": [{
                "slot_id": "red",
                "color": [200, 0, 0],
                "tolerance": 18,
                "kind": "preset",
                "look_id": "mirror_chrome",
                "replacement_color": [20, 230, 60],
            }],
        },
        content_type="application/json",
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    routed = data["output_dir"]
    assert routed["success"] is True
    assert routed["verified"] is True
    assert Path(routed["path"]).resolve() == target.resolve()
    assert set(routed["pushed_files"]) == {"car_num_23371.tga", "car_spec_23371.tga"}
    assert (target / "car_num_23371.tga").read_bytes() == Path(data["paint_path"]).read_bytes()
    assert (target / "car_spec_23371.tga").read_bytes() == Path(data["spec_path"]).read_bytes()
    paint = np.asarray(Image.open(target / "car_num_23371.tga").convert("RGB"))
    assert float(paint[..., 1].mean()) > float(paint[..., 0].mean())
    assert float(paint[..., 1].mean()) > float(paint[..., 2].mean())

def test_easy_generate_deploys_and_hash_verifies_the_paint_spec_pair(
    app_client,
    tmp_paint_file,
    monkeypatch,
    server_module,
    tmp_path,
):
    out_root = tmp_path / f"spec_sculpt_verified_deploy_{uuid.uuid4().hex}"
    jobs_root = out_root / "shokker_spec_sculpt"
    documents_root = tmp_path / f"redirected_documents_{uuid.uuid4().hex}" / "iRacing"
    target = documents_root / "paint" / "dirtlatemodel 438"
    jobs_root.mkdir(parents=True)
    target.mkdir(parents=True)
    monkeypatch.setattr(server_module, "OUTPUT_FOLDER", str(out_root))
    monkeypatch.setattr(server_module, "SPEC_SCULPT_JOBS_DIR", str(jobs_root))
    monkeypatch.setattr(server_module, "_iracing_documents_dir", lambda: str(documents_root))

    response = app_client.post(
        "/api/spec-sculpt/generate",
        json={
            "paint_file": tmp_paint_file,
            "iracing_id": "23371",
            "use_custom_number": True,
            "chromatic_shift": True,
            "seed": 9191,
            "save_tga": True,
            "deploy_car_folder": "dirtlatemodel 438",
            "mode": "zoned",
        },
        content_type="application/json",
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    deployed = data["deploy_to_iracing"]
    assert deployed["success"] is True
    assert deployed["verified"] is True
    assert set(deployed["deployed"]) == {"car_num_23371.tga", "car_spec_23371.tga"}
    assert {row["name"] for row in deployed["files"]} == set(deployed["deployed"])
    for row in deployed["files"]:
        installed = target / row["name"]
        source = data["paint_path"] if row["name"].startswith("car_num_") else data["spec_path"]
        assert installed.read_bytes() == Path(source).read_bytes()
        assert row["sha256"] == __import__("hashlib").sha256(installed.read_bytes()).hexdigest()
