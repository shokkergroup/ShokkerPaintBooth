import json
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_uv_calibration_pack import BLUE_REFERENCE, encode_uv_coordinates, encode_uv_coordinates_high_precision
from _forge_uv_render_decoder import assign_known_surfaces, decode_capture_high_precision, decode_render_pair


def test_pair_decoder_recovers_uv_and_rejects_static_background():
    uv_size = (256, 256)
    code = encode_uv_coordinates(uv_size).astype(np.float32)
    coordinate = np.full((140, 180, 3), 90, dtype=np.float32)
    white = coordinate.copy()
    yy, xx = np.mgrid[0:100, 0:120]
    source_x = np.rint(xx / 119 * 255).astype(np.int32)
    source_y = np.rint(yy / 99 * 255).astype(np.int32)
    shade = (0.42 + 0.38 * xx / 119)[..., None]
    coordinate[20:120, 30:150] = np.rint(code[source_y, source_x] * shade)
    white[20:120, 30:150] = np.rint(240 * shade)
    uv_xy, confidence = decode_render_pair(coordinate.astype(np.uint8), white.astype(np.uint8), uv_size)
    valid = confidence[20:120, 30:150] > 0
    expected = np.stack((source_x, source_y), axis=2)
    error = np.abs(uv_xy[20:120, 30:150][valid] - expected[valid])
    assert np.quantile(error, 0.95) < 3.0
    assert np.count_nonzero(confidence[:15]) == 0


def test_surface_assignment_reports_unknown_geometry():
    ownership = np.zeros((10, 10), dtype=np.uint16)
    ownership[:, :5] = 3
    uv_xy = np.array([[[2.0, 4.0], [8.0, 4.0]]], dtype=np.float32)
    confidence = np.ones((1, 2), dtype=np.float32)
    assigned = assign_known_surfaces(uv_xy, confidence, ownership)
    assert assigned.tolist() == [[3, 0]]


def test_high_precision_capture_recovers_exact_uv_and_preserves_unknown(tmp_path: Path):
    uv_size = (64, 64)
    code = encode_uv_coordinates_high_precision(uv_size).astype(np.float32)
    screen_height, screen_width = 72, 96
    yy, xx = np.mgrid[0:screen_height, 0:screen_width]
    source_x = np.rint(xx / (screen_width - 1) * (uv_size[0] - 1)).astype(np.int32)
    source_y = np.rint(yy / (screen_height - 1) * (uv_size[1] - 1)).astype(np.int32)
    shade = (0.48 + 0.35 * xx / (screen_width - 1))[..., None]
    rendered = np.rint(code[:, source_y, source_x] * shade[None, ...]).clip(0, 255).astype(np.uint8)
    white = np.repeat(np.rint(BLUE_REFERENCE * shade).clip(0, 255).astype(np.uint8), 3, axis=2)
    rendered[:, :5, :, :] = 90
    white[:5, :, :] = 90

    calibration = tmp_path / "calibration"
    calibration.mkdir(exist_ok=True)
    manifest = {
        "canvas": list(uv_size),
        "surface_lookup": [{"id": 1, "surface": "left_side"}],
        "preferred_coordinate_codec": "hex12_v2",
    }
    (calibration / "calibration_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    ownership = np.zeros((uv_size[1], uv_size[0]), dtype=np.uint16)
    ownership[:, : uv_size[0] // 2] = 1
    Image.fromarray(ownership).save(calibration / "surface_ownership.png")
    capture_paths = []
    for index in range(3):
        path = tmp_path / f"capture_{index}.png"
        Image.fromarray(rendered[index], "RGB").save(path)
        capture_paths.append(path)
    white_path = tmp_path / "white.png"
    Image.fromarray(white, "RGB").save(white_path)

    output = tmp_path / "decoded"
    result = decode_capture_high_precision(capture_paths, white_path, calibration, output)
    dense = np.load(output / "dense_screen_to_uv.npz")
    valid = dense["confidence"] > 0
    expected = np.stack((source_x, source_y), axis=2)
    error = np.max(np.abs(dense["uv_xy"][valid] - expected[valid]), axis=1)
    assert result["valid"]
    assert result["coordinate_codec"] == "hex12_v2"
    assert np.quantile(error, 0.95) <= 1.0
    assert np.count_nonzero(valid[:5]) == 0
    assert result["known_surface_pixels"] > 0
    assert result["unknown_geometry_pixels"] > 0
    assert result["p95_quantization_residual"] <= 4.25
    assert "quantization_residual" in dense.files

