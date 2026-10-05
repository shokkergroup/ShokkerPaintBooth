from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import _forge_dlm_physical_capture_bundle_v1 as capture


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_physical_capture_bundle_v1" / "run115_job.json"
REQUIRED_ROLES = [
    "capture_01_physical_side_a_profile",
    "capture_02_physical_side_b_profile",
    "capture_03_front_three_quarter_a",
    "capture_04_front_three_quarter_b",
    "capture_05_rear_three_quarter_a",
    "capture_06_rear_three_quarter_b",
    "capture_07_top_front",
    "capture_08_top_rear",
    "capture_09_nose_head_on",
    "capture_10_rear_head_on",
]
FORBIDDEN_CLAIMS = {
    "physical_surface_ownership",
    "physical_side_polarity",
    "surface_adjacency",
    "projector",
    "livery",
    "psd",
    "app",
    "delivery",
}


def _job() -> dict:
    return json.loads(JOB.read_text(encoding="utf-8"))


def _resolved(job: dict) -> dict[str, Path]:
    return {
        key: capture._resolve(JOB, source["path"])
        for key, source in job["sources"].items()
    }


def _tree_hashes(path: Path) -> dict[str, str]:
    return {
        item.relative_to(path).as_posix(): capture.sha256_file(item)
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    output = tmp_path_factory.mktemp("run115")
    return output, capture.build(JOB, output)


def test_job_hash_binds_run113_and_run69_sources() -> None:
    job = _job()
    assert job["$schema"] == capture.JOB_SCHEMA
    assert job["expected"] == {
        "canvas_size": [2048, 2048],
        "component_count": 565,
        "official_pixel_count": 2_670_216,
        "asset_count": 5,
        "capture_role_count": 10,
        "frames_per_role": 10,
    }
    assert job["required_role_ids"] == REQUIRED_ROLES
    assert len(job["sources"]) == 13
    for source in job["sources"].values():
        path = capture._resolve(JOB, source["path"])
        assert path.is_file()
        assert capture.sha256_file(path) == source["sha256"]


def test_sources_prove_full_topology_and_hex12_authority() -> None:
    job = _job()
    contracts = capture._asset_contracts(job)
    evidence = capture.validate_sources(job, _resolved(job), contracts)
    report = evidence["run113_report"]
    decoder = evidence["run113_decoder"]
    run69 = evidence["run69_manifest"]

    assert report["metrics"]["component_count"] == 565
    assert report["metrics"]["encoded_pixel_count"] == 2_670_216
    assert len(decoder["components"]) == 565
    assert len(evidence["component_tokens"]) == len(set(evidence["component_tokens"])) == 565
    assert np.count_nonzero(evidence["run113_alpha"]) == 2_670_216
    assert run69["preferred_coordinate_codec"] == "hex12_v2"
    assert run69["coordinate_codecs"]["hex12_v2"]["passes_msd_to_lsd"] == [
        "05_uv_hex12_msd",
        "06_uv_hex12_mid",
        "07_uv_hex12_lsd",
    ]
    assert run69["coordinate_codecs"]["hex12_v2"]["white_control"] == "02_flat_white_control"


def test_emitted_assets_are_2048_rgb_png_tga_pairs(built: tuple[Path, dict]) -> None:
    output, result = built
    assets = result["manifest"]["assets"]
    assert len(assets) == 5
    assert [item["asset_id"] for item in assets] == [
        "full_topology_neutral_v2",
        "hex12_msd",
        "hex12_mid",
        "hex12_lsd",
        "flat_white_control",
    ]
    for asset in assets:
        png_path = output / asset["png"]["path"]
        tga_path = output / asset["tga"]["path"]
        png = Image.open(png_path)
        tga = Image.open(tga_path)
        assert png.size == tga.size == (2048, 2048)
        assert png.mode == tga.mode == "RGB"
        assert png.getbands() == tga.getbands() == ("R", "G", "B")
        assert np.array_equal(np.asarray(png), np.asarray(tga))
        assert capture.sha256_file(png_path) == asset["png"]["sha256"]
        assert capture.sha256_file(tga_path) == asset["tga"]["sha256"]


def test_neutral_topology_asset_preserves_every_official_pixel(built: tuple[Path, dict]) -> None:
    output, result = built
    job = _job()
    source = np.asarray(Image.open(_resolved(job)["run113_texture"]).convert("RGBA"), dtype=np.uint8)
    alpha = np.asarray(Image.open(_resolved(job)["run113_alpha"]).convert("L"), dtype=np.uint8)
    emitted = np.asarray(
        Image.open(output / result["manifest"]["assets"][0]["png"]["path"]).convert("RGB"),
        dtype=np.uint8,
    )
    official = alpha > 0
    assert int(np.count_nonzero(official)) == 2_670_216
    assert np.array_equal(emitted[official], source[:, :, :3][official])
    assert np.all(emitted[~official] == np.asarray(job["topology_background_rgb"], dtype=np.uint8))


def test_manifest_and_report_keep_calibration_only_nonclaims(built: tuple[Path, dict]) -> None:
    _, result = built
    manifest = result["manifest"]
    report = result["report"]
    audit = result["audit"]
    assert manifest["status"] == "READY_FOR_CAPTURE_NOT_CAPTURED_NOT_DELIVERY"
    assert report["status"] == "READY_FOR_CAPTURE_NOT_CAPTURED_NOT_DELIVERY"
    assert audit["status"] == "PASS_READY_FOR_CAPTURE_NOT_CAPTURED_NOT_DELIVERY"
    assert all(audit["gates"].values())
    assert manifest["topology"] == {
        "component_count": 565,
        "official_pixel_count": 2_670_216,
        "unique_component_token_count": 565,
        "outside_official_pixel_count": 0,
        "missing_official_pixel_count": 0,
        "overlap_pixel_count": 0,
        "guessed_pixel_count": 0,
    }
    for claim in FORBIDDEN_CLAIMS:
        assert manifest["claims"][claim] is False
        assert report["claims"][claim] is False
    assert report["metrics"]["captured_frame_count"] == 0


def test_capture_ledger_has_complete_independent_wire_pairs(built: tuple[Path, dict]) -> None:
    _, result = built
    ledger = result["ledger"]
    assert ledger["status"] == "NOT_CAPTURED"
    assert ledger["metrics"] == {
        "capture_role_count": 10,
        "asset_count": 5,
        "wire_pair_count": 50,
        "required_frame_count": 100,
        "captured_frame_count": 0,
        "remaining_frame_count": 100,
    }
    assert [role["role_id"] for role in ledger["roles"]] == REQUIRED_ROLES
    assert len(ledger["frames"]) == 100
    assert all(frame["status"] == "NOT_CAPTURED" for frame in ledger["frames"])
    assert all(frame["captured_path"] is None and frame["captured_sha256"] is None for frame in ledger["frames"])
    for role in ledger["roles"]:
        assert role["required_frame_count"] == 10
        assert role["captured_frame_count"] == 0
        assert len(role["asset_pairs"]) == 5
        assert "physical side A and B are captured independently" in role["camera_lock_rules"]
        for pair in role["asset_pairs"]:
            assert pair["status"] == "NOT_CAPTURED"
            assert pair["unchanged_camera_required"] is True
            assert pair["wire_off"]["wire_state"] == "wire_off"
            assert pair["wire_on"]["wire_state"] == "wire_on"
            assert pair["wire_off"]["camera_lock_id"] == pair["wire_on"]["camera_lock_id"] == role["camera_lock_id"]
            assert pair["wire_off"]["source_tga_sha256"] == pair["wire_on"]["source_tga_sha256"]


def test_fixed_output_rebuild_is_byte_deterministic(built: tuple[Path, dict]) -> None:
    output, _ = built
    before = _tree_hashes(output)
    capture.build(JOB, output)
    after = _tree_hashes(output)
    assert after == before


def test_source_hash_drift_fails_closed() -> None:
    job = _job()
    source = copy.deepcopy(job["sources"]["run113_report"])
    source["sha256"] = "0" * 64
    with pytest.raises(capture.EvidenceError, match="run113_report_source_sha256_mismatch"):
        capture._verify_source(JOB, source, "run113_report")


def test_run113_forbidden_claim_drift_fails_closed(tmp_path: Path) -> None:
    job = _job()
    resolved = _resolved(job)
    report = json.loads(resolved["run113_report"].read_text(encoding="utf-8"))
    report["claims"]["delivery"] = True
    tampered = tmp_path / "tampered_run113_report.json"
    tampered.write_text(json.dumps(report), encoding="utf-8")
    resolved["run113_report"] = tampered
    with pytest.raises(capture.EvidenceError, match="run113_forbidden_claim_not_false:delivery"):
        capture.validate_sources(job, resolved, capture._asset_contracts(job))


def test_reusable_module_contains_no_scheme_identity_literals() -> None:
    text = (ROOT / "_forge_dlm_physical_capture_bundle_v1.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal lake", "sex wax", "miller", "mountain dew", "spider-man"):
        assert forbidden not in text
