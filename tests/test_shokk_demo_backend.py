from __future__ import annotations

import ast
import base64
import io
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
import pytest


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "demo" / "product-manifest.json"
BACKEND = ROOT / "demo" / "backend"


@pytest.fixture()
def tmp_path(tmp_path_factory):
    # Demo API tests need isolated sessions/files, not conftest's shared scratch.
    return tmp_path_factory.mktemp('shokk-demo-api')

EXPECTED_VISIBLE_IDS = [
    "f_chrome",
    "gloss",
    "f_frozen",
    "f_powder_coat",
    "f_metallic",
    "efx_holographic_drift",
    "fo_lava_lamp",
    "cherry_polka",
    "tac_frozen_bank",
    "elm_tsunami",
    "elm_black_ice",
    "ffo_haz_bloom",
    "fmo_chrysina_gold",
    "dkc_hematite",
    "fab_glass_slipper",
    "fab_woodcut_block",
    "beetle_ground",
    "butterfly_swallowtail",
    "cs_chocolate_mint",
    "xlab_shatter_royale",
    "xlab_stained_circuit",
    "grad_neon_rush",
    "grad_fire_fade_h",
    "aurora_black_rainbow",
    "fm_herringbone",
    "ff_wovencell",
    "ffl_foundry_spatter",
    "ff_truchet_glass",
    "impossible_cinder_pulse",
]

def _png_data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def _decode_data_url(value: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(value.split(",", 1)[1]))).convert("RGB")


def _rle_mask(mask: np.ndarray) -> dict[str, object]:
    values = np.asarray(mask, dtype=np.uint8)
    flat = values.ravel()
    runs: list[list[int]] = []
    current = int(flat[0])
    count = 1
    for item in flat[1:]:
        value = int(item)
        if value == current:
            count += 1
        else:
            runs.append([current, count])
            current = value
            count = 1
    runs.append([current, count])
    return {"width": int(values.shape[1]), "height": int(values.shape[0]), "runs": runs}


@pytest.fixture()
def demo_layout(tmp_path: Path):
    from demo.backend.catalog import DemoCatalog
    from demo.backend.compositor import SNAPSHOT_SCHEMA

    assets = tmp_path / "assets"
    snapshots = assets / "snapshots"
    thumbnails = assets / "thumbnails"
    starter_dir = assets / "starter"
    frontend = tmp_path / "frontend"
    runtime = tmp_path / "runtime"
    for directory in (snapshots, thumbnails, starter_dir, frontend, runtime):
        directory.mkdir(parents=True, exist_ok=True)

    catalog = DemoCatalog(MANIFEST)
    yy, xx = np.mgrid[0:32, 0:32]
    for index, finish in enumerate(catalog.finishes.values()):
        shade = ((xx * 7 + yy * 11 + index * 13) % 256).astype(np.uint8)
        paint = np.stack([shade, np.roll(shade, index % 7, 0), np.roll(shade, index % 5, 1)], axis=2)
        spec = np.stack([shade, 255 - shade, np.roll(shade, 3, 1)], axis=2)
        with (snapshots / f"{finish.id}.npz").open("wb") as handle:
            np.savez_compressed(
                handle,
                schema=np.array(SNAPSHOT_SCHEMA),
                finish_id=np.array(finish.id),
                build_size=np.array([32, 32]),
                paint=paint,
                spec=spec,
            )
        Image.fromarray(paint, mode="RGB").save(thumbnails / f"{finish.id}.png")

    starter = starter_dir / "SPB ARCA Chevy V6.psd"
    from psd_tools import PSDImage

    PSDImage.frompil(Image.new("RGBA", (16, 12), (40, 80, 120, 255))).save(starter)
    (frontend / "paint-booth-v2.html").write_text(
        "<!doctype html><title>SHOKK DEMO</title>", encoding="utf-8"
    )
    return {
        "assets": assets,
        "starter": starter,
        "frontend": frontend,
        "runtime": runtime,
        "catalog": catalog,
    }


@pytest.fixture()
def demo_app(demo_layout):
    from demo.backend.app import create_app

    return create_app(
        {"TESTING": True},
        manifest_path=MANIFEST,
        frontend_dir=demo_layout["frontend"],
        asset_dir=demo_layout["assets"],
        runtime_dir=demo_layout["runtime"],
    )


@pytest.fixture()
def demo_client(demo_app):
    return demo_app.test_client()


def test_manifest_is_the_exact_29_plus_hidden_fracture_contract():
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    visible = [entry for entry in raw["finishes"] if entry["visible"]]
    hidden = [entry for entry in raw["finishes"] if not entry["visible"]]

    assert [entry["id"] for entry in visible] == EXPECTED_VISIBLE_IDS
    assert [entry["id"] for entry in hidden] == ["fs_core_emerald"]
    assert raw["capabilities"]["visible_finish_count"] == 29
    assert raw["capabilities"]["renderable_finish_count"] == 30
    assert raw["capabilities"]["tools"] == ["pick", "exclude"]
    assert raw["capabilities"]["patterns"] is False
    assert raw["capabilities"]["spec_patterns"] is False
    assert raw["capabilities"]["extra_base_overlays"] == 0
    assert raw["branding"]["payhip_url"] == "https://payhip.com/b/AHgpV"
    by_id = {entry["id"]: entry for entry in raw["finishes"]}
    assert by_id["fmo_chrysina_gold"]["name"] == "Chrysina Gold"
    assert by_id["xlab_shatter_royale"]["name"] == "Shatter Royale"
    assert by_id["aurora_black_rainbow"]["category"] == "Aurora & Chromatic Flow"


def test_runtime_import_graph_has_no_paid_server_or_engine_imports():
    forbidden = {"server", "server_v5", "engine.registry", "shokker_engine_v2"}
    runtime_files = [path for path in BACKEND.glob("*.py") if path.name != "build_snapshots.py"]
    found = []
    for path in runtime_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.extend(alias.name for alias in node.names if alias.name in forbidden)
            elif isinstance(node, ast.ImportFrom) and node.module in forbidden:
                found.append(node.module)
    assert found == []


def test_static_splash_video_supports_chromium_byte_ranges(demo_client, demo_layout):
    branding = demo_layout["frontend"] / "assets" / "branding"
    branding.mkdir(parents=True, exist_ok=True)
    payload = b"synthetic-mp4-range-payload"
    (branding / "spb-splash-intro.mp4").write_bytes(payload)

    response = demo_client.get(
        "/assets/branding/spb-splash-intro.mp4",
        headers={"Range": "bytes=3-9"},
    )

    assert response.status_code == 206
    assert response.mimetype == "video/mp4"
    assert response.data == payload[3:10]
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.headers["Content-Range"] == f"bytes 3-9/{len(payload)}"


def test_electron_health_contract_is_exact(demo_client):
    response = demo_client.get("/api/demo/health")
    assert response.status_code == 200
    assert response.get_json() == {"ok": True, "product": "shokk-demo"}


def test_launch_token_and_host_header_are_enforced(demo_layout):
    from demo.backend.app import create_app

    app = create_app(
        {"TESTING": True, "DEMO_LAUNCH_TOKEN": "unit-test-secret"},
        manifest_path=MANIFEST,
        frontend_dir=demo_layout["frontend"],
        asset_dir=demo_layout["assets"],
        runtime_dir=demo_layout["runtime"],
    )
    client = app.test_client()
    missing = client.get("/api/demo/health")
    assert missing.status_code == 401
    assert missing.get_json()["error_code"] == "launch_token_required"
    rejected_host = client.get(
        "/api/demo/health",
        headers={"Host": "demo-attacker.example", "X-SPB-Demo-Token": "unit-test-secret"},
    )
    assert rejected_host.status_code == 421
    assert rejected_host.get_json()["error_code"] == "invalid_host"
    accepted = client.get(
        "/api/demo/health",
        headers={"Host": "127.0.0.1:59886", "X-SPB-Demo-Token": "unit-test-secret"},
    )
    assert accepted.status_code == 200
    assert accepted.get_json() == {"ok": True, "product": "shokk-demo"}


def test_runtime_defaults_under_electron_demo_user_data(monkeypatch, tmp_path):
    from demo.backend.app import _default_runtime_dir

    monkeypatch.delenv("SHOKK_DEMO_RUNTIME_DIR", raising=False)
    monkeypatch.setenv("SPB_DEMO_USER_DATA", str(tmp_path / "demo-user-data"))
    assert _default_runtime_dir() == (tmp_path / "demo-user-data" / "server-runtime").resolve()


def test_catalog_never_exposes_hidden_fracture_or_patterns(demo_client):
    data = demo_client.get("/api/finish-data").get_json()
    visible = data["bases"] + data["specials"]
    assert len(visible) == 29
    assert {entry["id"] for entry in visible} == set(EXPECTED_VISIBLE_IDS)
    public_manifest = demo_client.get("/api/demo-manifest").get_json()
    assert [entry["id"] for entry in public_manifest["finishes"]] == EXPECTED_VISIBLE_IDS
    assert len(public_manifest["finishes"]) == 29
    assert len(public_manifest["base_color_sources"]) == 30
    assert [entry["id"] for entry in public_manifest["base_color_sources"]][-1] == (
        "fs_core_emerald"
    )
    assert public_manifest["finishes"][0]["thumbnail"] == (
        "/demo-assets/thumbnails/f_chrome.png"
    )
    assert data["bases"][0]["thumbnail"].startswith("/demo-assets/thumbnails/")
    assert data["patterns"] == []
    assert data["counts"]["total"] == 29
    assert demo_client.get("/api/finish-by-id/fs_core_emerald").status_code == 404
    status = demo_client.get("/api/finish-registry-status").get_json()
    assert status["count"] == 29
    assert "fs_core_emerald" not in status["registered"]
    assert demo_client.get("/demo-assets/thumbnails/f_chrome.png").status_code == 200
    assert demo_client.get("/demo-assets/thumbnails/fs_core_emerald.png").status_code == 200
    assert demo_client.get("/demo-assets/thumbnails/not-allowed.png").status_code == 404


def test_snapshot_exporter_captures_through_a_full_coverage_zone(tmp_path):
    """[SPB-DEMO-PARITY 2026-09-03] The bake must not let a colour pick decide coverage.

    This test used to pin the exact-RGB neutral selector. That selector is what made
    fs_core_emerald bake FLAT (paint std 0.00 and spec std 0.00 at every plate level and
    canvas size) while the same finish over the same plate, captured through a
    whole-canvas region mask, renders with its real structure. Pinning the old contract
    was pinning the bug, so the assertion now demands full coverage.
    """

    from demo.backend.build_snapshots import (
        SnapshotBuildError,
        _renderer_zone,
        _square_field,
        _validate_capture_has_structure,
        _validate_renderer_changed_plate,
        _write_thumbnail,
    )

    class FakeEngine:
        BASE_REGISTRY = {"f_chrome": object()}
        MONOLITHIC_REGISTRY = {"fs_core_emerald": object()}

    base_zone = _renderer_zone(FakeEngine, "f_chrome", "base", 64)
    mono_zone = _renderer_zone(FakeEngine, "fs_core_emerald", "monolithic", 64)
    for zone in (base_zone, mono_zone):
        assert "color" not in zone, "a colour pick must not decide what gets captured"
        assert zone["apply_area_shape_only"] is True
        assert zone["region_mask"].shape == (64, 64)
        assert float(zone["region_mask"].min()) == 1.0

    # A capture with no structure in paint OR spec that also ignores both source plates
    # rendered nothing, and must fail the build rather than ship as a flat colour.
    flat = np.full((8, 8, 3), 40, dtype=np.uint8)
    with pytest.raises(SnapshotBuildError, match="rendered nothing"):
        _validate_capture_has_structure("fs_core_emerald", flat, flat, flat, flat)
    # Responding to the source plates is enough to prove the finish ran.
    _validate_capture_has_structure(
        "fs_core_emerald", flat, flat, np.full((8, 8, 3), 200, dtype=np.uint8), flat
    )

    with pytest.raises(SnapshotBuildError, match="unchanged neutral fields"):
        _validate_renderer_changed_plate(
            "f_chrome",
            np.full((2, 2, 3), 128, dtype=np.uint8),
            np.broadcast_to(np.array([5, 100, 16], dtype=np.uint8), (2, 2, 3)),
        )
    paint = np.full((16, 16, 3), 127, dtype=np.uint8)
    spec = np.zeros((16, 16, 3), dtype=np.uint8)
    spec[:, ::2, 0] = 255
    spec[:, 1::2, 1] = 220
    thumbnail = tmp_path / "f_chrome.png"
    _write_thumbnail(paint, spec, thumbnail)
    with Image.open(thumbnail) as image:
        assert image.size == (384, 192)
        thumbnail_rgb = np.asarray(image.convert("RGB"))
    assert np.array_equal(thumbnail_rgb[:, :192], _square_field(paint))
    assert np.array_equal(thumbnail_rgb[:, 192:], _square_field(spec))


def test_default_assets_resolve_only_to_packaged_paths(demo_client, demo_layout):
    response = demo_client.get("/api/default-assets")
    assert response.status_code == 200
    data = response.get_json()
    assert Path(data["assets"]["starter_psd"]) == demo_layout["starter"]
    assert data["assets"]["starter_uri"] == "starter://arca-chevy-v6"
    assert Path(data["assets"]["blank_canvas_tga"]).is_file()
    alias = demo_client.post("/check-file", json={"path": "starter://arca-chevy-v6"}).get_json()
    assert alias["is_file"] is True
    relative_alias = demo_client.post(
        "/check-file", json={"path": "assets/starter/SPB ARCA Chevy V6.psd"}
    ).get_json()
    assert Path(relative_alias["path"]) == demo_layout["starter"]


def test_preview_accepts_live_png_over_missing_paint_path_and_reuses_token(demo_client):
    source = Image.new("RGB", (24, 16), (120, 30, 70))
    body = {
        "paint_file": "Z:/definitely/missing.tga",
        "source_data_url": _png_data_url(source),
        "preview_scale": 1,
        "zones": [
            {
                "name": "Body",
                "color": "everything",
                "base": "gloss",
                "pattern": "none",
                "intensity": "100",
                "baseColorDepth": 0.65,
                "baseColorFlip": 75,
                "baseColorUnderglow": 0.25,
                "baseHueOffset": 20,
                "baseSaturationAdjust": 10,
                "baseBrightnessAdjust": 5,
                "specShiftR": 3,
                "specShiftG": -2,
                "specShiftB": 4,
                "baseSpecBlendMode": "screen",
            }
        ],
    }
    response = demo_client.post("/preview-render", json=body)
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["resolution"] == [24, 16]
    assert data["source_transport"] == "inline"
    assert data["paint_source_token"].startswith("demo-src-")
    assert data["paint_preview"].startswith("data:image/png;base64,")
    assert data["spec_preview"].startswith("data:image/png;base64,")

    reused = demo_client.post(
        "/preview-render",
        json={
            "paint_source_token": data["paint_source_token"],
            "zones": [{"color": "everything", "base": "f_chrome", "pattern": "none"}],
        },
    )
    assert reused.status_code == 200
    assert reused.get_json()["source_transport"] == "token"


def test_exclude_colors_are_subtracted_from_the_zone(demo_client):
    source_array = np.zeros((4, 8, 3), dtype=np.uint8)
    source_array[:, :4] = (255, 0, 0)
    source_array[:, 4:] = (0, 0, 255)
    source = Image.fromarray(source_array, mode="RGB")
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(source),
            "zones": [
                {
                    "color": "everything",
                    "base": "gloss",
                    "pattern": "none",
                    "base_color": [0, 0, 0],
                    "exclusions": [{"color_rgb": [0, 0, 255], "tolerance": 0}],
                }
            ],
        },
    )
    assert response.status_code == 200, response.get_json()
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))
    assert np.max(rendered[:, :4]) <= 10
    assert np.all(rendered[:, 4:] == np.array([0, 0, 255], dtype=np.uint8))


def test_five_zone_defaults_accept_empty_slots_and_render_remaining(demo_client):
    zones = [
        {
            "name": f"Zone {index}",
            "color": None,
            "colorMode": "none",
            "base": None,
            "finish": None,
            "pattern": "none",
        }
        for index in range(1, 5)
    ]
    zones.append(
        {
            "name": "Everything Else",
            "color": "remaining",
            "colorMode": "special",
            "base": "gloss",
            "pattern": "none",
            "baseColorMode": "source",
        }
    )
    source = Image.new("RGB", (12, 8), (31, 79, 143))
    response = demo_client.post(
        "/preview-render",
        json={"source_data_url": _png_data_url(source), "zones": zones},
    )
    assert response.status_code == 200, response.get_json()
    # Explicit source mode applies the material's spec but leaves paint exact.
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))
    assert np.array_equal(rendered, np.asarray(source))


def test_coverage_colors_supports_multiple_picks_shared_tolerance_and_remaining(demo_client):
    source_array = np.array(
        [
            [
                [250, 2, 1],
                [255, 0, 0],
                [0, 0, 255],
                [0, 8, 250],
                [0, 255, 0],
                [255, 255, 0],
            ]
        ],
        dtype=np.uint8,
    )
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(Image.fromarray(source_array, mode="RGB")),
            "zones": [
                {
                    "coverageMode": "Colors",
                    "coverageColors": [[255, 0, 0], [0, 0, 255]],
                    "coverageTolerance": 10,
                    "baseMaterial": "f_chrome",
                    "baseColorMode": "solid",
                    "baseColor": "#000000",
                },
                {
                    "coverage_mode": "remaining",
                    "base_material": "gloss",
                    "base_color_mode": "solid",
                    "base_color": "#ffffff",
                },
            ],
        },
    )
    assert response.status_code == 200, response.get_json()
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))[0]
    assert np.max(rendered[:4]) <= 1
    assert np.min(rendered[4:]) >= 254


def test_normal_zone_order_is_strict_first_wins(demo_client):
    response = demo_client.post(
        "/preview-render",
        json={
            # Saturated: "everything" is "painted or dark" and skips white art.
            "source_data_url": _png_data_url(Image.new("RGB", (6, 2), (31, 79, 143))),
            "zones": [
                {
                    "coverageMode": "everything",
                    "baseMaterial": "gloss",
                    "baseColorMode": "solid",
                    "baseColor": "#ff0000",
                },
                {
                    "coverageMode": "everything",
                    "baseMaterial": "f_chrome",
                    "baseColorMode": "solid",
                    "baseColor": "#0000ff",
                },
            ],
        },
    )
    assert response.status_code == 200, response.get_json()
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))
    assert np.min(rendered[:, :, 0]) >= 254
    assert np.max(rendered[:, :, 1:]) <= 1


def test_picker_tolerance_uses_paid_bt601_weighted_rgb_distance(demo_client):
    # A 100-point blue-only delta is 33.17 in BT.601 space (inside 40),
    # but 100 in unweighted Euclidean RGB (outside 40).
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(Image.new("RGB", (4, 2), (0, 0, 0))),
            "zones": [
                {
                    "coverageMode": "colors",
                    "coverageColors": [
                        {"color_rgb": [0, 0, 100], "tolerance": 40}
                    ],
                    "baseMaterial": "gloss",
                    "baseColorMode": "solid",
                    "baseColor": "#ffffff",
                }
            ],
        },
    )
    assert response.status_code == 200, response.get_json()
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))
    assert np.min(rendered) >= 254


def test_multiple_source_layer_masks_are_unioned_then_intersected(demo_client):
    # Saturated: "everything" is "painted or dark" and skips white art.
    source = Image.new("RGB", (6, 2), (31, 79, 143))
    left = np.zeros((2, 6), dtype=np.uint8)
    right = np.zeros((2, 6), dtype=np.uint8)
    left[:, :2] = 255
    right[:, 4:] = 255
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(source),
            "zones": [
                {
                    "coverageMode": "everything",
                    "baseMaterial": "gloss",
                    "baseColorMode": "solid",
                    "baseColor": "#000000",
                    "sourceLayers": [
                        {"id": "body-left", "mask": _rle_mask(left)},
                        {"id": "body-right", "source_layer_mask": _rle_mask(right)},
                    ],
                }
            ],
        },
    )
    assert response.status_code == 200, response.get_json()
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))
    assert np.max(rendered[:, :2]) <= 1
    # The unmasked middle keeps the SOURCE paint, whatever colour that is.
    assert np.array_equal(rendered[:, 2:4], np.asarray(source)[:, 2:4])
    assert np.max(rendered[:, 4:]) <= 1


def test_restricted_colors_match_layer_own_rgb_not_flattened_composite(demo_client):
    flattened = Image.new("RGB", (6, 2), (0, 0, 255))
    layer_rgba = np.zeros((2, 6, 4), dtype=np.uint8)
    layer_rgba[:, :3, :3] = (255, 0, 0)
    layer_rgba[:, :3, 3] = 255
    layer_scope = np.zeros((2, 6), dtype=np.uint8)
    layer_scope[:, :3] = 255
    raw_layer_png = _png_data_url(Image.fromarray(layer_rgba, mode="RGBA")).split(",", 1)[1]

    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(flattened),
            "zones": [
                {
                    "coverageMode": "colors",
                    "coverageColors": [
                        {"color_rgb": [255, 0, 0], "tolerance": 0}
                    ],
                    "baseMaterial": "gloss",
                    "baseColorMode": "solid",
                    "baseColor": "#000000",
                    "sourceLayers": ["unblended-red-art"],
                    "sourceLayerMask": _rle_mask(layer_scope),
                    "source_layer_rgb_png": raw_layer_png,
                }
            ],
        },
    )
    assert response.status_code == 200, response.get_json()
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))
    assert np.max(rendered[:, :3]) <= 1
    assert np.all(rendered[:, 3:] == np.array([0, 0, 255], dtype=np.uint8))


def test_duplicate_zones_share_one_top_level_source_layer_scope(demo_client, demo_layout):
    from demo.backend.validation import validate_render_request

    # Saturated: "everything" is "painted or dark" and skips white art.
    flattened = Image.new("RGB", (6, 2), (31, 79, 143))
    layer_rgba = np.zeros((2, 6, 4), dtype=np.uint8)
    layer_rgba[:, :3, :3] = (255, 0, 0)
    layer_rgba[:, 3:, :3] = (0, 0, 255)
    layer_rgba[:, :, 3] = 255
    scope_mask = _rle_mask(np.full((2, 6), 255, dtype=np.uint8))
    scope_rgb = _png_data_url(Image.fromarray(layer_rgba, mode="RGBA")).split(",", 1)[1]
    body = {
        "source_data_url": _png_data_url(flattened),
        "source_layer_scopes": {
            "body-art-v1": {
                "source_layer_mask": scope_mask,
                "source_layer_rgb_png": scope_rgb,
                # Scope tables cannot inject arbitrary render controls.
                "base": "paid_only_finish",
            }
        },
        "zones": [
            {
                "source_layer_scope_id": "body-art-v1",
                "coverageMode": "colors",
                "coverageColors": [{"color_rgb": [255, 0, 0], "tolerance": 0}],
                "baseMaterial": "gloss",
                "baseColorMode": "solid",
                "baseColor": "#000000",
            },
            {
                "source_layer_scope_id": "body-art-v1",
                "coverageMode": "colors",
                "coverageColors": [{"color_rgb": [0, 0, 255], "tolerance": 0}],
                "baseMaterial": "f_chrome",
                "baseColorMode": "solid",
                "baseColor": "#00ff00",
            },
        ],
    }
    checked = validate_render_request(body, demo_layout["catalog"].renderable_ids)
    assert checked[0]["_demo_source_layer_masks"][0] is scope_mask
    assert checked[1]["_demo_source_layer_masks"][0] is scope_mask
    assert "paid_only_finish" not in checked[0].values()

    response = demo_client.post("/preview-render", json=body)
    assert response.status_code == 200, response.get_json()
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))
    assert np.max(rendered[:, :3]) <= 1
    assert np.all(rendered[:, 3:] == np.array([0, 255, 0], dtype=np.uint8))


@pytest.mark.parametrize(
    ("table", "scope_id", "error_code"),
    [
        ({}, "missing", "source_layer_scope_not_found"),
        ({}, "x" * 129, "invalid_source_layer_scope_ref"),
        ([], "missing", "invalid_source_layer_scopes"),
        (
            {"broken": {"source_layer_rgb_png": "not-a-mask"}},
            "broken",
            "invalid_source_layer_scope",
        ),
        (
            {
                f"scope-{index}": {
                    "source_layer_mask": {"width": 1, "height": 1, "runs": [[255, 1]]}
                }
                for index in range(65)
            },
            "scope-0",
            "too_many_source_layer_scopes",
        ),
        (
            {
                "x" * 129: {
                    "source_layer_mask": {"width": 1, "height": 1, "runs": [[255, 1]]}
                }
            },
            "x" * 129,
            "source_layer_scope_id_too_long",
        ),
    ],
)
def test_source_layer_scope_table_rejects_missing_malformed_or_oversized_refs(
    demo_client, table, scope_id, error_code
):
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(Image.new("RGB", (2, 2), "white")),
            "source_layer_scopes": table,
            "zones": [
                {
                    "source_layer_scope_id": scope_id,
                    "coverageMode": "everything",
                    "baseMaterial": "gloss",
                    "baseColorMode": "source",
                }
            ],
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error_code"] == error_code


def test_layer_restricted_remaining_uses_only_overlapping_restricted_claims(demo_client):
    source_array = np.zeros((1, 6, 3), dtype=np.uint8)
    source_array[0, 0] = (255, 0, 0)
    prior_layer = np.zeros((1, 6), dtype=np.uint8)
    prior_layer[0, 1] = 255
    remainder_layer = np.zeros((1, 6), dtype=np.uint8)
    remainder_layer[0, :4] = 255
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(Image.fromarray(source_array, mode="RGB")),
            "zones": [
                {
                    "coverageMode": "colors",
                    "coverageColors": [{"color_rgb": [255, 0, 0], "tolerance": 0}],
                    "baseMaterial": "gloss",
                    "baseColorMode": "solid",
                    "baseColor": "#ffff00",
                },
                {
                    "coverageMode": "everything",
                    "baseMaterial": "gloss",
                    "baseColorMode": "solid",
                    "baseColor": "#00ff00",
                    "sourceLayers": ["restricted-prior"],
                    "sourceLayerMask": _rle_mask(prior_layer),
                },
                {
                    "coverageMode": "remaining",
                    "baseMaterial": "gloss",
                    "baseColorMode": "solid",
                    "baseColor": "#0000ff",
                    "sourceLayers": ["restricted-remainder"],
                    "sourceLayerMask": _rle_mask(remainder_layer),
                },
            ],
        },
    )
    assert response.status_code == 200, response.get_json()
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))[0]
    # Col 0's earlier unrestricted yellow claim is intentionally ignored by
    # layer-local Remaining; col 1's restricted green claim is preserved.
    assert np.array_equal(rendered[0], [0, 0, 255])
    assert np.array_equal(rendered[1], [0, 255, 0])
    assert np.all(rendered[2:4] == np.array([0, 0, 255], dtype=np.uint8))
    assert np.all(rendered[4:] == np.array([0, 0, 0], dtype=np.uint8))


def test_named_source_layers_without_masks_fail_closed(demo_client):
    source = Image.new("RGB", (6, 2), (25, 50, 75))
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(source),
            "zones": [
                {
                    "coverageMode": "everything",
                    "baseMaterial": "gloss",
                    "baseColorMode": "solid",
                    "baseColor": "#ffffff",
                    "sourceLayers": ["psd-layer-id-without-raster-mask"],
                }
            ],
        },
    )
    assert response.status_code == 200, response.get_json()
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))
    assert np.array_equal(rendered, np.asarray(source))


@pytest.mark.parametrize("enabled", [None, False, True])
def test_color_lab_requires_explicit_opt_in_and_can_be_switched_back_off(enabled):
    from demo.backend.compositor import _apply_color_lab_controls

    material = np.full((2, 3, 3), (10, 41, 23), dtype=np.float32)
    selected = np.full((2, 3, 3), (241, 4, 20), dtype=np.float32)
    zone = {"baseColorDepth": .65, "baseColorFlip": 180, "baseColorUnderglow": .5}
    if enabled is not None:
        zone["baseColorLabEnabled"] = enabled
    rendered = _apply_color_lab_controls(material, selected, zone)
    assert np.array_equal(rendered, selected) is (enabled is not True)
    zone["baseColorLabEnabled"] = False
    assert np.array_equal(_apply_color_lab_controls(material, selected, zone), selected)


@pytest.mark.parametrize("color", ["#F10414", "#010101", "#010000", "#00FF00", "#123456"])
def test_literal_solid_color_survives_preview_and_export(demo_client, tmp_path, color):
    expected = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    source = Image.new("RGB", (32, 32), (40, 80, 120))
    zone = {
        "finish": "fs_core_emerald", "color": "remaining",
        "baseColorMode": "solid", "baseColor": color,
        "baseColorDepth": .65, "baseColorFlip": 180, "baseColorUnderglow": .4,
        "baseStrength": 1, "baseColorStrength": 1, "baseSpecStrength": 3,
        "baseHueOffset": 0, "baseSaturationAdjust": 0, "baseBrightnessAdjust": 0,
    }
    payload = {"source_data_url": _png_data_url(source), "zones": [zone]}
    preview = demo_client.post("/preview-render", json={**payload, "preview_scale": .5})
    assert preview.status_code == 200, preview.get_json()
    assert np.all(np.asarray(_decode_data_url(preview.get_json()["paint_preview"])) == expected)
    output_dir = tmp_path / "export"
    render = demo_client.post("/render", json={**payload, "iracing_id": "23371", "use_custom_number": True, "output_dir": str(output_dir)})
    assert render.status_code == 200, render.get_json()
    assert np.all(np.asarray(Image.open(output_dir / "car_num_23371.tga").convert("RGB")) == expected)
    assert render.get_json()["recipe"]["zones"][0]["adjustments"]["color_lab_enabled"] is False


@pytest.mark.parametrize("scale", [1, .5, .25])
def test_spatial_exclude_preserves_only_drawn_pixels_in_preview_and_export(demo_client, tmp_path, scale):
    # SPB-93 / owner 09-04: EXCLUDE is a zone mask, never a color-wide edit.
    source = Image.new("RGB", (64, 32), (40, 80, 120))
    mask = np.zeros((32, 64), dtype=np.uint8)
    mask[8:24, 16:48] = 2
    zone = {"finish": "fs_core_emerald", "color": "remaining",
            "baseColorMode": "solid", "baseColor": "#F10414",
            "baseStrength": 1, "baseColorStrength": 1,
            "spatial_mask": _rle_mask(mask)}
    payload = {"source_data_url": _png_data_url(source), "zones": [zone]}
    preview = demo_client.post("/preview-render", json={**payload, "preview_scale": scale})
    assert preview.status_code == 200, preview.get_json()
    paint = np.asarray(_decode_data_url(preview.get_json()["paint_preview"]))
    height, width = paint.shape[:2]
    excluded = np.asarray(Image.fromarray(mask).resize((width, height), Image.Resampling.NEAREST)) == 2
    assert np.all(paint[excluded] == (40, 80, 120))
    assert np.all(paint[~excluded] == (241, 4, 20))
    spec = np.asarray(_decode_data_url(preview.get_json()["spec_preview"]))
    assert np.all(spec[excluded] == (0, 128, 0))
    # Export keeps the source at excluded locations too, at native resolution.
    output_dir = tmp_path / "export"
    rendered = demo_client.post("/render", json={**payload, "iracing_id": "23371", "use_custom_number": True, "output_dir": str(output_dir)})
    assert rendered.status_code == 200, rendered.get_json()
    exported = np.asarray(Image.open(output_dir / "car_num_23371.tga").convert("RGB"))
    assert np.all(exported[mask == 2] == (40, 80, 120))
    assert np.all(exported[mask == 0] == (241, 4, 20))
    exported_spec = np.asarray(Image.open(output_dir / "car_spec_23371.tga").convert("RGB"))
    assert np.all(exported_spec[mask == 2] == (0, 128, 0))


def test_spatial_exclude_releases_pixels_to_remaining_zone(demo_client):
    mask = np.zeros((16, 32), dtype=np.uint8)
    mask[:, 16:] = 2
    response = demo_client.post("/preview-render", json={
        "source_data_url": _png_data_url(Image.new("RGB", (32, 16), (40, 80, 120))),
        "zones": [
            {"finish": "gloss", "color": "remaining", "baseColorMode": "solid", "baseColor": "#FF0000", "spatial_mask": _rle_mask(mask)},
            {"finish": "gloss", "color": "remaining", "baseColorMode": "solid", "baseColor": "#00FF00"},
        ],
    })
    assert response.status_code == 200, response.get_json()
    paint = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))
    assert np.all(paint[:, :16] == (255, 0, 0))
    assert np.all(paint[:, 16:] == (0, 255, 0))


def test_neutral_color_paths_preserve_authored_source_special_and_gradient():
    from demo.backend.catalog import DemoCatalog
    from demo.backend.compositor import _paint_field, _gradient_field, _parse_color

    finish = DemoCatalog(MANIFEST).finishes["fs_core_emerald"]
    source = np.full((3, 256, 3), (241, 4, 20), dtype=np.float32)
    texture = np.broadcast_to(np.arange(256, dtype=np.float32)[None, :, None], source.shape).copy()
    gradient = _gradient_field([{"pos": 0, "color": "#010101"}, {"pos": 1, "color": "#F10414"}], "horizontal", 256, 3)
    assert np.array_equal(gradient[0, 0], [1, 1, 1])
    assert np.array_equal(gradient[0, -1], [241, 4, 20])
    # Test all 256 levels and both request encodings, not only fully saturated primaries.
    for value in range(256):
        assert np.array_equal(_parse_color([value / 255] * 3)[0], [value] * 3)
    for mode, color_source, expected in [("finish", None, texture), ("source", None, source), ("special", texture, texture), ("gradient", gradient, gradient)]:
        zone = {"baseColorMode": mode, "baseColorDepth": .65, "baseColorFlip": 180, "baseColorUnderglow": .5}
        actual = _paint_field(source, texture, finish, zone, color_source=color_source, authored=True)
        assert np.array_equal(actual, expected), mode
    # Deliberate HSB adjustments and strength blending must remain functional.
    adjusted = _paint_field(source, texture, finish, {"baseColorMode": "source", "baseBrightnessAdjust": -50}, authored=True)
    assert not np.array_equal(adjusted, source)


def test_base_material_and_base_color_modes_are_independent(demo_client):
    source = Image.new("RGB", (16, 10), (24, 66, 108))

    def preview(zone_update):
        zone = {
            "coverageMode": "everything",
            "baseMaterial": "gloss",
        }
        zone.update(zone_update)
        response = demo_client.post(
            "/preview-render",
            json={"source_data_url": _png_data_url(source), "zones": [zone]},
        )
        assert response.status_code == 200, response.get_json()
        return response.get_json()

    source_mode = preview({"baseColorMode": "source"})
    finish_mode = preview({"baseColorMode": "finish-own"})
    solid_mode = preview({"baseColorMode": "solid", "baseColor": "#ff0000"})
    special_a = preview(
        {"baseColorMode": "from-special", "baseColorSource": "xlab_shatter_royale"}
    )
    special_b = preview(
        {"base_color_mode": "special", "base_color_source": "fo_lava_lamp"}
    )

    assert np.array_equal(
        np.asarray(_decode_data_url(source_mode["paint_preview"])), np.asarray(source)
    )
    assert finish_mode["paint_sig"] != source_mode["paint_sig"]
    solid = np.asarray(_decode_data_url(solid_mode["paint_preview"]))
    assert np.min(solid[:, :, 0]) >= 254
    assert np.max(solid[:, :, 1:]) <= 1
    assert special_a["paint_sig"] != special_b["paint_sig"]
    # Color source changes paint only; material identity owns the spec output.
    assert special_a["spec_sig"] == special_b["spec_sig"]


def test_spec_strength_300_percent_changes_render_accepts_percent_and_rejects_overflow(demo_client):
    from demo.backend.compositor import _spec_strength_ratio

    assert _spec_strength_ratio(1) == 1
    assert _spec_strength_ratio(3) == 3
    assert _spec_strength_ratio(100) == 1
    assert _spec_strength_ratio(300) == 3

    # Saturated: "everything" is the engine's "painted or dark" selector and skips
    # unsaturated mid-tone art (verified against the paid engine: solid white/gray -> 0%).
    source = Image.new("RGB", (16, 10), (31, 79, 143))

    def preview(strength: float):
        response = demo_client.post(
            "/preview-render",
            json={
                "source_data_url": _png_data_url(source),
                "zones": [
                    {
                        "coverageMode": "everything",
                        "baseMaterial": "gloss",
                        "baseColorMode": "source",
                        "base_spec_strength": strength,
                    }
                ],
            },
        )
        return response

    at_100 = preview(1.0)
    at_300 = preview(3.0)
    assert at_100.status_code == 200, at_100.get_json()
    assert at_300.status_code == 200, at_300.get_json()

    neutral = np.array([0, 128, 0], dtype=np.float32)
    spec_100 = np.asarray(_decode_data_url(at_100.get_json()["spec_preview"]), dtype=np.float32)
    spec_300 = np.asarray(_decode_data_url(at_300.get_json()["spec_preview"]), dtype=np.float32)
    departure_100 = np.abs(spec_100 - neutral).mean()
    departure_300 = np.abs(spec_300 - neutral).mean()
    assert departure_300 > departure_100
    assert at_300.get_json()["spec_sig"] != at_100.get_json()["spec_sig"]

    percent_100 = preview(100)
    percent_300 = preview(300)
    legacy_3_01_percent = preview(3.01)
    ratio_3_01_percent = preview(0.0301)
    overflow = preview(301)
    assert percent_100.status_code == 200, percent_100.get_json()
    assert percent_300.status_code == 200, percent_300.get_json()
    assert legacy_3_01_percent.status_code == 200, legacy_3_01_percent.get_json()
    assert ratio_3_01_percent.status_code == 200, ratio_3_01_percent.get_json()
    assert overflow.status_code == 400
    assert percent_100.get_json()["spec_sig"] == at_100.get_json()["spec_sig"]
    assert percent_300.get_json()["spec_sig"] == at_300.get_json()["spec_sig"]
    assert legacy_3_01_percent.get_json()["spec_sig"] == ratio_3_01_percent.get_json()["spec_sig"]
    assert overflow.get_json()["error_code"] == "invalid_spec_strength"

    aliases = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(source),
            "zones": [
                {
                    "coverageMode": "everything",
                    "baseMaterial": "gloss",
                    "baseColorMode": "source",
                    "base_spec_strength": 3.0,
                    "baseSpecStrength": 300,
                }
            ],
        },
    )
    assert aliases.status_code == 200, aliases.get_json()
    assert aliases.get_json()["spec_sig"] == at_300.get_json()["spec_sig"]

    invalid = preview("loud")
    assert invalid.status_code == 400
    assert invalid.get_json()["error_code"] == "invalid_spec_strength"


def test_custom_gradient_accepts_position_shape_and_direction(demo_client):
    response = demo_client.post(
        "/preview-render",
        json={
            # Saturated: "everything" skips unsaturated mid-tones (paid-engine parity).
            "source_data_url": _png_data_url(Image.new("RGB", (20, 8), (31, 79, 143))),
            "zones": [
                {
                    "coverageMode": "everything",
                    "baseMaterial": "gloss",
                    "baseColorMode": "custom-gradient",
                    "gradientStops": [
                        {"position": 0, "color": "#000000"},
                        {"position": 1, "color": "#ffffff"},
                    ],
                    "gradientDirection": "horizontal",
                }
            ],
        },
    )
    assert response.status_code == 200, response.get_json()
    rendered = np.asarray(_decode_data_url(response.get_json()["paint_preview"]))
    assert np.max(rendered[:, 0]) <= 1
    assert np.min(rendered[:, -1]) >= 254
    assert float(rendered[:, -1].mean()) > float(rendered[:, 0].mean()) + 200


def test_temporarily_blank_special_picker_falls_back_without_breaking_preview(demo_client):
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(Image.new("RGB", (8, 8), "gray")),
            "zones": [
                {
                    "coverageMode": "everything",
                    "baseMaterial": "gloss",
                    "baseColorMode": "special",
                    "baseColorSource": "",
                }
            ],
        },
    )
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["success"] is True


@pytest.mark.parametrize(
    ("zone_update", "error_code"),
    [
        (
            {"baseColorMode": "special", "baseColorSource": "paid_only_finish"},
            "finish_not_allowed",
        ),
        (
            {
                "baseColorMode": "gradient",
                "gradientStops": [{"position": 0, "color": "#000000"}],
            },
            "invalid_gradient",
        ),
        ({"baseColorMode": "stack-three-colors"}, "invalid_base_color_mode"),
    ],
)
def test_expanded_zone_contract_rejects_unavailable_or_invalid_color_modes(
    demo_client, zone_update, error_code
):
    zone = {"coverageMode": "everything", "baseMaterial": "gloss"}
    zone.update(zone_update)
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(Image.new("RGB", (8, 8), "white")),
            "zones": [zone],
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error_code"] == error_code


@pytest.mark.parametrize(
    ("zone_update", "error_code"),
    [
        ({"pattern": "carbon_fiber"}, "demo_capability_denied"),
        ({"pattern_stack": [{"id": "carbon_fiber"}]}, "demo_capability_denied"),
        ({"spec_pattern_stack": [{"pattern": "hologram"}]}, "demo_capability_denied"),
        ({"second_base": "f_chrome"}, "demo_capability_denied"),
        ({"base": "chrome"}, "finish_not_allowed"),
    ],
)
def test_render_payload_hard_rejects_paid_features(demo_client, zone_update, error_code):
    zone = {"color": "everything", "base": "gloss", "pattern": "none"}
    zone.update(zone_update)
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(Image.new("RGB", (8, 8), "white")),
            "zones": [zone],
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error_code"] == error_code


def test_hidden_fracture_is_renderable_but_not_catalogued(demo_client):
    response = demo_client.post(
        "/preview-render",
        json={
            "source_data_url": _png_data_url(Image.new("RGB", (8, 8), "white")),
            "zones": [{"color": "everything", "finish": "fs_core_emerald"}],
        },
    )
    assert response.status_code == 200, response.get_json()


def test_full_render_writes_iracing_files_and_serves_job_artifacts(demo_client, tmp_path):
    output_dir = tmp_path / "iracing" / "paint" / "arca"
    response = demo_client.post(
        "/render",
        json={
            "source_data_url": _png_data_url(Image.new("RGB", (12, 10), (80, 90, 100))),
            "iracing_id": "23371",
            "use_custom_number": True,
            "output_dir": str(output_dir),
            "zones": [{"color": "everything", "finish": "xlab_shatter_royale"}],
        },
    )
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data["success"] is True
    assert (output_dir / "car_num_23371.tga").is_file()
    assert (output_dir / "car_spec_23371.tga").is_file()
    assert data["output_dir"]["verified"] is True
    assert data["links"] == {
        "payhip": "https://payhip.com/b/AHgpV",
        "discord": "https://discord.gg/GwXxyhwtDu",
    }
    recipe = data["recipe"]
    assert recipe["schema"] == "spb-demo-render-recipe/1"
    assert recipe["render"]["output"]["path"] == str(output_dir.resolve())
    assert recipe["render"]["number"] == {
        "mode": "custom",
        "value": "",
        "iracing_id": "23371",
    }
    assert recipe["zones"][0]["material"]["name"] == "Shatter Royale"
    assert recipe["zones"][0]["coverage"]["mode"] == "everything"
    assert recipe["links"] == {
        "full_version": "https://payhip.com/b/AHgpV",
        "payhip": "https://payhip.com/b/AHgpV",
        "discord": "https://discord.gg/GwXxyhwtDu",
    }
    readme_response = demo_client.get(data["download_urls"]["SHOKK_DEMO_README"])
    assert readme_response.status_code == 200
    readme = readme_response.get_data(as_text=True)
    assert "https://payhip.com/b/AHgpV" in readme
    assert "https://discord.gg/GwXxyhwtDu" in readme
    assert demo_client.get(data["preview_urls"]["RENDER_paint.png"]).status_code == 200
    assert demo_client.get(data["download_urls"]["car_spec_23371"]).status_code == 200


def test_psd_import_and_rasterization_match_frontend_shapes(demo_client):
    imported = demo_client.post(
        "/api/psd-import", json={"psd_path": "starter://arca-chevy-v6"}
    )
    assert imported.status_code == 200, imported.get_json()
    payload = imported.get_json()
    assert payload["success"] is True
    assert payload["width"] == 16
    assert payload["height"] == 12
    assert payload["composite"].startswith("data:image/png;base64,")
    assert isinstance(payload["layers"], list)

    rasterized = demo_client.post(
        "/api/psd-rasterize-all", json={"psd_path": "starter://arca-chevy-v6"}
    )
    assert rasterized.status_code == 200, rasterized.get_json()
    assert rasterized.get_json()["success"] is True
    assert isinstance(rasterized.get_json()["layers"], dict)


def test_browser_flat_tga_upload_returns_a_bounded_png_preview(demo_client):
    source = Image.new("RGB", (7, 5), (12, 34, 56))
    buffer = io.BytesIO()
    source.save(buffer, "TGA")
    response = demo_client.post(
        "/preview-tga",
        data={"file": (io.BytesIO(buffer.getvalue()), "browser-paint.tga")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert response.mimetype == "image/png"
    preview = Image.open(io.BytesIO(response.data)).convert("RGB")
    assert preview.size == (7, 5)
    assert preview.getpixel((0, 0)) == (12, 34, 56)


def test_browser_flat_upload_rejects_unsupported_extension(demo_client):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), (1, 2, 3)).save(buffer, "PNG")
    response = demo_client.post(
        "/preview-tga",
        data={"file": (io.BytesIO(buffer.getvalue()), "unsupported.xcf")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "TGA, PNG, JPG, or JPEG" in response.get_json()["error"]


def test_browser_flat_upload_rejects_payload_over_source_limit(
    demo_client, monkeypatch
):
    import demo.backend.app as app_module

    monkeypatch.setattr(app_module, "MAX_SOURCE_BYTES", 16)
    response = demo_client.post(
        "/preview-tga",
        data={"file": (io.BytesIO(b"x" * 17), "oversized.tga")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "64 MiB" in response.get_json()["error"]


def test_config_and_file_browser_keep_source_and_output_paths_viable(demo_client, tmp_path):
    saved = demo_client.post(
        "/config",
        json={
            "iracing_id": "23371",
            "source_paint_path": "starter://arca-chevy-v6",
            "output_dir": str(tmp_path),
        },
    )
    assert saved.status_code == 200
    assert demo_client.get("/config").get_json()["iracing_id"] == "23371"

    (tmp_path / "car.tga").write_bytes(b"demo")
    (tmp_path / "ignore.txt").write_text("demo", encoding="utf-8")
    browsed = demo_client.post(
        "/browse-files", json={"path": str(tmp_path), "filter": ".tga,.psd"}
    )
    assert browsed.status_code == 200
    assert [item["name"] for item in browsed.get_json()["items"] if item["type"] == "file"] == [
        "car.tga"
    ]


def test_release_runtime_refuses_missing_reviewed_snapshots(tmp_path):
    from demo.backend.app import create_app

    case_root = tmp_path / "missing-snapshot-release-case"
    assets = case_root / "assets"
    (assets / "starter").mkdir(parents=True, exist_ok=True)
    (assets / "starter" / "SPB ARCA Chevy V6.psd").write_bytes(b"placeholder")
    with pytest.raises(RuntimeError, match="all 30 reviewed material snapshots"):
        create_app(
            {"TESTING": True},
            manifest_path=MANIFEST,
            asset_dir=assets,
            runtime_dir=case_root / "runtime",
            frontend_dir=case_root / "frontend",
        )

    # Synthetic material is reachable only behind an explicit dev/test flag.
    app = create_app(
        {"TESTING": True, "ALLOW_SYNTHETIC_SNAPSHOTS": True},
        manifest_path=MANIFEST,
        asset_dir=assets,
        runtime_dir=case_root / "runtime-synthetic",
        frontend_dir=case_root / "frontend",
    )
    assert app.test_client().get("/api/demo/health").status_code == 200
