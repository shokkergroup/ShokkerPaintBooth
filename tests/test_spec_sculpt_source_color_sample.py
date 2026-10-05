"""Source-true Easy Spec Sculpt color-picker regression tests."""

from __future__ import annotations

import io
import uuid

import numpy as np
from PIL import Image


INTERNAL_HEADERS = {"X-Shokker-Internal": "1"}


def _paint_dir(tmp_path):
    path = tmp_path / f"source_color_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_flat_2048_tga_upload_returns_native_rgb_not_preview_jpeg(app_client, tmp_path):
    color = (17, 101, 203)
    payload = io.BytesIO()
    Image.new("RGB", (2048, 2048), color).save(payload, format="TGA")
    payload.seek(0)

    response = app_client.post(
        "/api/spec-sculpt/sample-source-color",
        data={
            "x": "0.25",
            "y": "0.75",
            "paint_file": (payload, "owner-flat-2048.tga"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    data = response.get_json()
    assert data["success"] is True
    assert data["rgb"] == list(color)
    assert data["hex"] == "#1165CB"
    assert data["sample"]["center_rgb"] == list(color)
    assert data["sample"]["pixel"] == [512, 1536]
    assert data["sample"]["resolution"] == [2048, 2048]
    assert data["sample"]["method"] == "center-guided-local-mode"
    assert data["palette"] == [{
        "rgb": list(color),
        "hex": "#1165CB",
        "count": 25,
        "coverage": 1.0,
    }]
    assert data["source"]["via"] == "upload"


def test_path_analyze_token_samples_each_side_of_full_resolution_edge(
    app_client,
    tmp_path,
):
    left = (220, 20, 30)
    right = (10, 70, 240)
    pixels = np.empty((2048, 2048, 3), dtype=np.uint8)
    pixels[:, :1024] = left
    pixels[:, 1024:] = right
    paint_path = _paint_dir(tmp_path) / "one-pixel-edge-2048.tga"
    Image.fromarray(pixels, mode="RGB").save(paint_path, format="TGA")

    analyzed = app_client.post(
        "/api/spec-sculpt/analyze",
        json={"paint_file": str(paint_path)},
        content_type="application/json",
    )
    assert analyzed.status_code == 200, analyzed.get_data(as_text=True)
    source_token = analyzed.get_json().get("source_token")
    assert source_token and len(source_token) >= 48

    def sample_pixel(pixel_x):
        return app_client.post(
            "/api/spec-sculpt/sample-source-color",
            json={
                "source_token": source_token,
                "x": (pixel_x + 0.1) / 2048,
                "y": (800 + 0.1) / 2048,
            },
            headers=INTERNAL_HEADERS,
        )

    left_response = sample_pixel(1023)
    right_response = sample_pixel(1024)
    top_left_response = app_client.post(
        "/api/spec-sculpt/sample-source-color",
        json={"source_token": source_token, "x": 0, "y": 0},
        headers=INTERNAL_HEADERS,
    )
    bottom_right_response = app_client.post(
        "/api/spec-sculpt/sample-source-color",
        json={"source_token": source_token, "x": 1, "y": 1},
        headers=INTERNAL_HEADERS,
    )
    assert left_response.status_code == 200, left_response.get_data(as_text=True)
    assert right_response.status_code == 200, right_response.get_data(as_text=True)
    assert top_left_response.status_code == 200, top_left_response.get_data(as_text=True)
    assert bottom_right_response.status_code == 200, bottom_right_response.get_data(as_text=True)
    left_data = left_response.get_json()
    right_data = right_response.get_json()

    assert left_data["rgb"] == list(left)
    assert left_data["sample"]["center_rgb"] == list(left)
    assert left_data["sample"]["pixel"] == [1023, 800]
    assert {tuple(row["rgb"]) for row in left_data["palette"]} == {left, right}
    assert sorted(row["count"] for row in left_data["palette"]) == [10, 15]

    assert right_data["rgb"] == list(right)
    assert right_data["sample"]["center_rgb"] == list(right)
    assert right_data["sample"]["pixel"] == [1024, 800]
    assert {tuple(row["rgb"]) for row in right_data["palette"]} == {left, right}
    assert right_data["source"]["via"] == "source_token"

    top_left = top_left_response.get_json()["sample"]
    bottom_right = bottom_right_response.get_json()["sample"]
    assert top_left["pixel"] == [0, 0]
    assert top_left["bounds"] == [0, 0, 2, 2]
    assert top_left["rgb"] == list(left)
    assert bottom_right["pixel"] == [2047, 2047]
    assert bottom_right["bounds"] == [2045, 2045, 2047, 2047]
    assert bottom_right["rgb"] == list(right)


def test_raw_sample_path_requires_internal_marker_and_allowed_root(
    app_client,
    server_module,
    monkeypatch,
    tmp_path,
):
    paint_dir = _paint_dir(tmp_path)
    paint_path = paint_dir / "guarded-2048.tga"
    Image.new("RGB", (2048, 2048), (40, 80, 120)).save(paint_path, format="TGA")
    request_body = {"paint_file": str(paint_path), "x": 0.5, "y": 0.5}

    no_marker = app_client.post(
        "/api/spec-sculpt/sample-source-color",
        json=request_body,
    )
    assert no_marker.status_code == 403
    assert no_marker.get_json()["code"] == "internal_request_required"

    monkeypatch.setattr(server_module, "_spec_sculpt_sample_allowed_roots", lambda: [str(paint_dir / "other")])
    outside = app_client.post(
        "/api/spec-sculpt/sample-source-color",
        json=request_body,
        headers=INTERNAL_HEADERS,
    )
    assert outside.status_code == 403
    assert outside.get_json()["code"] == "source_path_not_allowed"


def test_sample_rejects_non_2048_and_out_of_range_coordinates(app_client):
    payload = io.BytesIO()
    Image.new("RGB", (64, 64), (1, 2, 3)).save(payload, format="TGA")
    payload.seek(0)
    wrong_size = app_client.post(
        "/api/spec-sculpt/sample-source-color",
        data={"x": "0.5", "y": "0.5", "paint_file": (payload, "small.tga")},
        content_type="multipart/form-data",
    )
    assert wrong_size.status_code == 400
    assert wrong_size.get_json()["code"] == "easy_requires_2048"

    payload = io.BytesIO()
    Image.new("RGB", (2048, 2048), (1, 2, 3)).save(payload, format="TGA")
    payload.seek(0)
    bad_coordinate = app_client.post(
        "/api/spec-sculpt/sample-source-color",
        data={"x": "1.01", "y": "0.5", "paint_file": (payload, "edge.tga")},
        content_type="multipart/form-data",
    )
    assert bad_coordinate.status_code == 400
    assert bad_coordinate.get_json()["code"] == "invalid_sample_coordinates"
