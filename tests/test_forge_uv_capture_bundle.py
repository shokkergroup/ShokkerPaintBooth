import hashlib
import json
import os
import uuid
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_uv_calibration_pack import (
    BLUE_REFERENCE,
    HIGH_PRECISION_CODEC_SCHEMA,
    encode_uv_coordinates_high_precision,
)
from _forge_uv_capture_bundle import (
    REQUIRED_ROLES,
    _json_sha256,
    validate_capture_bundle,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, dict[str, dict[str, Path]], str, str]:
    tmp_path = tmp_path / f"capture_bundle_{uuid.uuid4().hex}"
    tmp_path.mkdir(parents=True)
    uv_size = (64, 64)
    calibration = tmp_path / "calibration"
    calibration.mkdir()
    codec = {
        "schema": HIGH_PRECISION_CODEC_SCHEMA,
        "preferred": True,
        "passes_msd_to_lsd": ["05_uv_hex12_msd", "06_uv_hex12_mid", "07_uv_hex12_lsd"],
        "white_control": "02_flat_white_control",
        "radix": 16,
        "digits": 3,
        "direct_pixel_addressing": True,
    }
    manifest = {
        "$schema": "shokk-forge.uv-calibration-pack/v1",
        "canvas": list(uv_size),
        "surface_lookup": [{"id": 1, "surface": "official_domain"}],
        "preferred_coordinate_codec": "hex12_v2",
        "coordinate_codecs": {"hex12_v2": codec},
    }
    manifest_path = calibration / "calibration_manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    Image.fromarray(np.ones(uv_size[::-1], dtype=np.uint16)).save(
        calibration / "surface_ownership.png"
    )

    code = encode_uv_coordinates_high_precision(uv_size).astype(np.float32)
    yy, xx = np.mgrid[0 : uv_size[1], 0 : uv_size[0]]
    shade = (0.51 + 0.27 * xx / (uv_size[0] - 1))[..., None]
    base_rendered = np.rint(code * shade[None, ...]).clip(0, 255).astype(np.uint8)
    base_white = np.repeat(
        np.rint(BLUE_REFERENCE * shade).clip(0, 255).astype(np.uint8), 3, axis=2
    )
    captures: dict[str, dict[str, Path]] = {}
    for index, role in enumerate(REQUIRED_ROLES):
        role_dir = tmp_path / "captures" / role
        role_dir.mkdir(parents=True)
        rendered = np.roll(base_rendered, shift=index, axis=2)
        white = np.roll(base_white, shift=index, axis=1)
        captures[role] = {}
        for pass_index, slot in enumerate(("hex_msd", "hex_mid", "hex_lsd")):
            path = role_dir / f"{slot}.png"
            Image.fromarray(rendered[pass_index], "RGB").save(path)
            captures[role][slot] = path
        white_path = role_dir / "white.png"
        Image.fromarray(white, "RGB").save(white_path)
        captures[role]["white"] = white_path
    return calibration, captures, _sha(manifest_path), _json_sha256(codec)


def test_complete_bundle_decodes_all_roles_and_fuses_deterministically(tmp_path: Path):
    calibration, captures, pack_hash, codec_hash = _fixture(tmp_path)
    output = tmp_path / "out"
    thresholds = {
        "min_views": 5,
        "min_uv_visibility_fraction": 0.99,
        "min_mean_confidence": 0.5,
        "max_p95_quantization_residual": 4.25,
        "max_surface_conflict_fraction": 0.0,
    }
    result = validate_capture_bundle(
        captures,
        calibration,
        output,
        expected_pack_sha256=pack_hash,
        expected_codec_sha256=codec_hash,
        fusion_thresholds=thresholds,
    )
    assert result["capture_bundle_ready"]
    assert result["correspondence_fuser_called"]
    assert result["capture_count"] == 20
    assert result["fusion_summary"]["view_count"] == 5
    assert result["fusion_summary"]["roles"] == sorted(REQUIRED_ROLES)
    assert not result["livery_ready"]
    assert not result["psd_ready"]
    assert not result["delivery_ready"]
    for role in REQUIRED_ROLES:
        decode = result["roles"][role]["decode"]
        assert decode["coordinate_codec"] == "hex12_v2"
        assert decode["screen_coverage_fraction"] > 0.99
        assert decode["mean_confidence"] > 0.5
        assert decode["p95_quantization_residual"] <= 4.25
    first_hash = _sha(output / "capture_bundle_manifest.json")
    second = validate_capture_bundle(
        captures,
        calibration,
        output,
        expected_pack_sha256=pack_hash,
        expected_codec_sha256=codec_hash,
        fusion_thresholds=thresholds,
    )
    assert second["capture_bundle_ready"]
    assert _sha(output / "capture_bundle_manifest.json") == first_hash


@pytest.mark.parametrize(
    "fault", ["missing", "duplicate", "duplicate_content", "legacy", "dimensions", "stale"]
)
def test_preflight_faults_fail_closed_without_calling_fuser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
):
    calibration, captures, pack_hash, codec_hash = _fixture(tmp_path)
    if fault == "missing":
        captures.pop("rear")
    elif fault == "duplicate":
        captures["right"]["hex_msd"] = captures["left"]["hex_msd"]
    elif fault == "duplicate_content":
        captures["right"]["hex_msd"].write_bytes(captures["left"]["hex_msd"].read_bytes())
    elif fault == "legacy":
        captures["top"]["coordinate_render"] = captures["top"].pop("hex_msd")
    elif fault == "dimensions":
        Image.new("RGB", (32, 64), (10, 20, 30)).save(captures["front"]["hex_mid"])
    else:
        old = (calibration / "calibration_manifest.json").stat().st_mtime - 20
        os.utime(captures["rear"]["white"], (old, old))

    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("fuser must not run")

    monkeypatch.setattr("_forge_uv_capture_bundle.fuse_decoded_views", forbidden)
    result = validate_capture_bundle(
        captures,
        calibration,
        tmp_path / "rejected",
        expected_pack_sha256=pack_hash,
        expected_codec_sha256=codec_hash,
    )
    assert not result["capture_bundle_ready"]
    assert not result["correspondence_fuser_called"]
    assert not called
    assert result["blockers"]
    assert not (tmp_path / "rejected" / "fusion" / "correspondence_fusion.json").exists()


@pytest.mark.parametrize("kind", ["pack", "codec"])
def test_stale_expected_binding_rejects_before_decode(tmp_path: Path, kind: str):
    calibration, captures, pack_hash, codec_hash = _fixture(tmp_path)
    kwargs = {
        "expected_pack_sha256": "0" * 64 if kind == "pack" else pack_hash,
        "expected_codec_sha256": "f" * 64 if kind == "codec" else codec_hash,
    }
    output = tmp_path / f"binding_reject_{uuid.uuid4().hex}"
    result = validate_capture_bundle(captures, calibration, output, **kwargs)
    assert not result["capture_bundle_ready"]
    assert not result["correspondence_fuser_called"]
    assert "stale/wrong" in result["blockers"][0]
    assert not (output / "decoded").exists()


def test_fuser_failure_is_manifested_without_correspondence_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    calibration, captures, pack_hash, codec_hash = _fixture(tmp_path)

    def rejected(*args, **kwargs):
        raise ValueError("synthetic fusion rejection")

    monkeypatch.setattr("_forge_uv_capture_bundle.fuse_decoded_views", rejected)
    output = tmp_path / "fusion_rejected"
    result = validate_capture_bundle(
        captures,
        calibration,
        output,
        expected_pack_sha256=pack_hash,
        expected_codec_sha256=codec_hash,
    )
    assert result["capture_bundle_ready"]
    assert result["correspondence_fuser_called"]
    assert not result["correspondence_ready"]
    assert not result["delivery_ready"]
    assert result["blockers"] == ["correspondence fusion rejected: synthetic fusion rejection"]
    written = json.loads((output / "capture_bundle_manifest.json").read_text(encoding="utf-8"))
    assert written["capture_bundle_ready"]
    assert not written["correspondence_ready"]
