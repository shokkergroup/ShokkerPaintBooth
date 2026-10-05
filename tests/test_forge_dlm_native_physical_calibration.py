from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image
from scipy import ndimage as ndi

import _forge_dlm_native_physical_calibration as calibration


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data/dlm_native_physical_calibration/run126_job.json"
LEGACY_WIRE = ROOT / "_dlm_dossier/psd/guides/04_Wire.png"
REQUIRED_ROLES = [
    "physical_side_a_profile",
    "physical_side_b_profile",
    "front_head_on",
    "rear_head_on",
    "top_front",
    "top_rear",
    "front_three_quarter_a",
    "front_three_quarter_b",
    "rear_three_quarter_a",
    "rear_three_quarter_b",
]
FORBIDDEN_CLAIMS = {
    "physical_surface_ownership",
    "physical_side_polarity",
    "stored_orientation",
    "surface_adjacency",
    "occlusion_truth",
    "projector",
    "livery",
    "psd",
    "app",
    "delivery",
}


def _job() -> dict:
    return json.loads(JOB.read_text(encoding="utf-8"))


def _tree_hashes(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): calibration.sha256_file(item)
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    output = tmp_path_factory.mktemp("run126-native-calibration")
    return output, calibration.build(JOB, output)


def test_job_binds_only_native_2048_run121_authority() -> None:
    job = _job()
    assert job["$schema"] == calibration.JOB_SCHEMA
    assert job["expected"] == {
        "canvas": [2048, 2048],
        "native_coverage_pixels": 2_658_729,
        "texture_asset_count": 9,
        "capture_role_count": 10,
        "required_frame_count": 180,
    }
    assert set(job["sources"]) == {"run121_report", "native_wire", "native_coverage"}
    assert job["sources"]["native_wire"]["sha256"] == calibration.NATIVE_WIRE_SHA256
    assert job["sources"]["native_coverage"]["sha256"] == calibration.NATIVE_COVERAGE_FILE_SHA256
    assert job["sources"]["run121_report"]["sha256"] == calibration.RUN121_REPORT_SHA256
    for source in job["sources"].values():
        path = calibration._resolve(JOB, source["path"])
        assert path.is_file()
        assert calibration.sha256_file(path) == source["sha256"]


def test_native_coverage_and_every_texture_are_exactly_clipped(built: tuple[Path, dict]) -> None:
    output, result = built
    coverage = result["coverage"]
    assert coverage.shape == (2048, 2048)
    assert int(coverage.sum()) == calibration.NATIVE_COVERAGE_PIXELS
    assert calibration.pixel_sha256(coverage.astype(np.uint8)) == calibration.NATIVE_COVERAGE_PIXEL_SHA256
    assets = result["report"]["assets"]
    assert len(assets) == 9
    for asset in assets:
        png = np.asarray(Image.open(output / asset["png"]["path"]).convert("RGB"), dtype=np.uint8)
        tga = np.asarray(Image.open(output / asset["tga"]["path"]).convert("RGB"), dtype=np.uint8)
        assert png.shape == tga.shape == (2048, 2048, 3)
        assert np.array_equal(png, tga)
        active = np.any(png != 0, axis=2)
        assert np.array_equal(active, coverage)
        assert int(active.sum()) == calibration.NATIVE_COVERAGE_PIXELS
        assert asset["active_pixel_sha256"] == calibration.NATIVE_COVERAGE_PIXEL_SHA256


def test_decoder_is_exact_on_clean_blur_and_noise_and_abstains_on_occlusion(built: tuple[Path, dict]) -> None:
    _, result = built
    metrics = result["report"]["synthetic_validation"]
    assert metrics["sample_count"] == 96
    assert metrics["clean_exact_rate"] == 1.0
    assert metrics["blur_exact_rate"] == 1.0
    assert metrics["noise_exact_rate"] == 1.0
    assert metrics["occlusion_abstain_rate"] == 1.0
    assert metrics["pass"] is True

    coverage = result["coverage"]
    interior = ndi.binary_erosion(coverage, iterations=6)
    v, u = [int(item[0]) for item in np.nonzero(interior)]
    observations = calibration._sample_observations(result["stack"], u, v)
    decoded = calibration.decode_observation_vector(observations, result["decoder"], coverage)
    assert decoded["status"] == "DECODED_NATIVE_UV_NOT_PHYSICAL_OWNERSHIP"
    assert (decoded["u"], decoded["v"]) == (u, v)
    observations["phase_v_128"] = None
    abstained = calibration.decode_observation_vector(observations, result["decoder"], coverage)
    assert abstained["status"] == "ABSTAIN_MISSING_PASS"


def test_explicit_blur_path_preserves_phase_at_interior_point(built: tuple[Path, dict]) -> None:
    _, result = built
    coverage = result["coverage"]
    interior = ndi.binary_erosion(coverage, iterations=8)
    ys, xs = np.nonzero(interior)
    index = len(xs) // 2
    u, v = int(xs[index]), int(ys[index])
    blurred = {
        key: cv2.GaussianBlur(value, (5, 5), 1.0, borderType=cv2.BORDER_REFLECT101)
        for key, value in result["stack"].items()
    }
    decoded = calibration.decode_observation_vector(
        calibration._sample_observations(blurred, u, v), result["decoder"], coverage
    )
    assert decoded["status"] == "DECODED_NATIVE_UV_NOT_PHYSICAL_OWNERSHIP"
    assert (decoded["u"], decoded["v"]) == (u, v)


def test_capture_inventory_has_all_distinct_views_and_zero_captured(built: tuple[Path, dict]) -> None:
    _, result = built
    inventory = result["inventory"]
    assert inventory["status"] == "NOT_CAPTURED"
    assert [role["role_id"] for role in inventory["roles"]] == REQUIRED_ROLES
    assert inventory["metrics"] == {
        "capture_role_count": 10,
        "asset_count": 9,
        "wire_pair_count": 90,
        "required_frame_count": 180,
        "captured_frame_count": 0,
        "remaining_frame_count": 180,
    }
    assert all(frame["status"] == "NOT_CAPTURED" for frame in inventory["frames"])
    assert all(frame["captured_path"] is None and frame["captured_sha256"] is None for frame in inventory["frames"])
    targeted = {item for role in inventory["roles"] for item in role["targeted_abstentions"]}
    assert targeted == {
        "hood",
        "nose",
        "front_fender_a",
        "front_fender_b",
        "roof",
        "rear_deck",
        "tub",
        "spoiler_face_inside",
        "spoiler_face_outside",
    }
    for role in inventory["roles"]:
        assert len(role["asset_pairs"]) == 9
        assert role["required_frame_count"] == 18
        assert role["captured_frame_count"] == 0
        for pair in role["asset_pairs"]:
            assert pair["unchanged_camera_required"] is True
            assert pair["wire_off"]["camera_lock_id"] == pair["wire_on"]["camera_lock_id"] == role["camera_lock_id"]
            assert pair["wire_off"]["wire_state"] == "wire_off"
            assert pair["wire_on"]["wire_state"] == "wire_on"


def test_report_is_honest_calibration_only_with_all_forbidden_claims_false(built: tuple[Path, dict]) -> None:
    output, result = built
    report = result["report"]
    decoder = result["decoder"]
    assert report["status"] == "PASS_READY_FOR_NATIVE_PHYSICAL_CAPTURE_NOT_CAPTURED_NOT_DELIVERY"
    assert report["metrics"]["captured_frame_count"] == 0
    for claim in FORBIDDEN_CLAIMS:
        assert report["claims"][claim] is False
        assert decoder["claims"][claim] is False
    assert (output / "NATIVE_PHYSICAL_DECODER_CONTRACT.json").is_file()
    assert (output / "NATIVE_PHYSICAL_CAPTURE_INVENTORY.json").is_file()
    assert (output / "CAPTURE_PROTOCOL.md").is_file()
    assert (output / "RUN126_NATIVE_PHYSICAL_CALIBRATION_CONTACT.png").is_file()
    assert (output / "RUN126_SUMMARY.md").is_file()


def test_legacy_wire_source_is_rejected_before_any_calibration_output(tmp_path: Path) -> None:
    assert LEGACY_WIRE.is_file()
    with pytest.raises(calibration.CalibrationEvidenceError, match="native_wire_sha256_mismatch_not_native_authority"):
        calibration.build(JOB, tmp_path / "rejected", source_overrides={"native_wire": LEGACY_WIRE})
    assert not (tmp_path / "rejected/textures").exists()


def test_fixed_output_rebuild_is_byte_deterministic(built: tuple[Path, dict]) -> None:
    output, _ = built
    before = _tree_hashes(output)
    calibration.build(JOB, output)
    after = _tree_hashes(output)
    assert after == before


def test_reusable_module_contains_no_livery_identity_or_legacy_pack_dependency() -> None:
    text = (ROOT / "_forge_dlm_native_physical_calibration.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal lake", "sex wax", "miller", "mountain dew", "spider-man"):
        assert forbidden not in text
    for forbidden in ("run113", "run110", "full_topology_component_decoder", "04_wire.png"):
        assert forbidden not in text
