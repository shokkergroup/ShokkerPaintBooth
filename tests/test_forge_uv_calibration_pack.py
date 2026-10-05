import json
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_uv_calibration_pack import (
    BLUE_REFERENCE,
    HEX_LEVEL_MIN,
    HEX_LEVEL_STEP,
    build_pack,
    decode_uv_coordinates,
    decode_uv_coordinates_high_precision,
    encode_uv_coordinates,
    encode_uv_coordinates_high_precision,
)


def test_coordinate_code_survives_neutral_shading():
    size = (2048, 2048)
    encoded = encode_uv_coordinates(size)
    points = np.array([encoded[0, 0], encoded[1024, 700], encoded[2047, 2047]], dtype=np.float32)
    shaded = np.rint(points * 0.57).astype(np.uint8)
    decoded, confidence = decode_uv_coordinates(shaded, size)
    expected = np.array([[0, 0], [700, 1024], [2047, 2047]], dtype=np.float32)
    assert np.max(np.abs(decoded - expected)) < 12
    assert np.all(confidence > 0.9)


def test_hex12_codec_recovers_2048_uv_with_subpixel_tail_under_shading_and_noise():
    size = (2048, 2048)
    encoded = encode_uv_coordinates_high_precision(size)
    rng = np.random.default_rng(20260717)
    x = rng.integers(0, size[0], size=4096)
    y = rng.integers(0, size[1], size=4096)
    samples = encoded[:, y, x, :].astype(np.float32)
    gain = rng.uniform(0.38, 0.92, size=(4096, 3)).astype(np.float32)
    white = BLUE_REFERENCE * gain + rng.normal(0.0, 0.22, size=(4096, 3))
    rendered = samples * gain[None, ...] + rng.normal(0.0, 0.22, size=samples.shape)
    rendered = np.clip(np.rint(rendered), 0, 255).astype(np.uint8)
    white = np.clip(np.rint(white), 0, 255).astype(np.uint8)

    decoded, confidence, residual = decode_uv_coordinates_high_precision(rendered, white, size)
    valid = confidence > 0
    expected = np.stack((x, y), axis=1)
    error = np.max(np.abs(decoded[valid] - expected[valid]), axis=1)
    assert valid.mean() > 0.985
    assert np.median(error) <= 1.0
    assert np.quantile(error, 0.95) <= 1.0
    assert np.quantile(residual[valid], 0.95) < 4.25


def test_hex12_codec_rejects_background_clipping_and_midpoint_corruption():
    size = (2048, 2048)
    encoded = encode_uv_coordinates_high_precision(size)[:, 731:732, 1284:1285, :].astype(np.float32)
    rendered = np.repeat(encoded, 4, axis=1)
    white = np.full((4, 1, 3), BLUE_REFERENCE, dtype=np.float32)
    rendered[:, 0] = white[0]  # static background
    white[1, 0, 0] = 255  # clipped lighting control
    rendered[1, 2, 0, 0] = HEX_LEVEL_MIN + HEX_LEVEL_STEP * 4.5  # illegal half digit
    rendered[2, 3, 0, 2] = 210  # blue normalization/reference drift

    decoded, confidence, residual = decode_uv_coordinates_high_precision(
        np.rint(rendered).astype(np.uint8), np.rint(white).astype(np.uint8), size
    )
    assert np.count_nonzero(confidence) == 0
    assert np.isnan(decoded).all()
    assert residual[2, 0] >= HEX_LEVEL_STEP / 2 - 0.01


def test_build_pack_keeps_full_canvas_coordinate_coverage(tmp_path: Path):
    mask_dir = tmp_path / "masks"
    mask_dir.mkdir(exist_ok=True)
    left = np.zeros((16, 16), dtype=np.uint8)
    left[:, :10] = 255
    fender = np.zeros((16, 16), dtype=np.uint8)
    fender[2:7, 7:15] = 255
    Image.fromarray(left, "L").save(mask_dir / "left.png")
    Image.fromarray(fender, "L").save(mask_dir / "fender.png")
    adapter = {
        "adapter_id": "test-adapter",
        "canvas": [16, 16],
        "surfaces": {
            "side": {"family": "side", "mask_path": "masks/left.png"},
            "fender": {"family": "front_fender", "mask_path": "masks/fender.png"},
        },
    }
    adapter_path = tmp_path / "adapter.json"
    adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
    official = np.zeros((16, 16), dtype=np.uint8)
    official[:, :14] = 255
    official_path = tmp_path / "official.png"
    Image.fromarray(official, "L").save(official_path)
    output = tmp_path / "out"
    manifest = build_pack(adapter_path, output, official_path)
    coordinate = np.asarray(Image.open(output / "01_uv_coordinate.png").convert("RGB"))
    ownership = np.asarray(Image.open(output / "surface_ownership.png"))
    assert manifest["valid"]
    assert coordinate.shape == (16, 16, 3)
    assert np.all(coordinate[:, :, 2] == 240)
    assert ownership[3, 8] == 1  # smaller fender mask wins overlap ownership
    assert np.count_nonzero(ownership[:, 14:]) == 0
    assert manifest["official_domain"]["applied"]
    assert manifest["outside_official_owned_pixels"] == 0
    fender_row = next(row for row in manifest["surface_lookup"] if row["surface"] == "fender")
    assert fender_row["source_mask_pixels"] == 40
    assert fender_row["official_clip_removed_pixels"] == 5
    assert (output / "DLM_UV_CALIBRATION_PACK.psd").exists()
    assert (output / "01_uv_coordinate.tga").exists()
    for stem in ("05_uv_hex12_msd", "06_uv_hex12_mid", "07_uv_hex12_lsd"):
        assert (output / f"{stem}.png").exists()
        assert (output / f"{stem}.tga").exists()
    assert manifest["preferred_coordinate_codec"] == "hex12_v2"
    assert manifest["coordinate_codecs"]["legacy_v1"]["preserved_for_backward_compatibility"]
    assert manifest["coordinate_codecs"]["hex12_v2"]["nominal_quantization_pixels"] == 1
    capture_readme = output / "README_CAPTURE.md"
    assert capture_readme.exists()
    assert "Never round rejected pixels" in capture_readme.read_text(encoding="utf-8")
    assert manifest["capture_protocol_file"]["required_camera_roles"] == [
        "left",
        "right",
        "top",
        "front",
        "rear",
    ]
    assert manifest["capture_protocol_file"]["total_required_captures"] == 20
