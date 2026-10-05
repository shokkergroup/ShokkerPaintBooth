from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import _forge_dlm_full_topology_calibration_kit_v2 as kit


ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data" / "dlm_full_topology_calibration_kit_v2" / "run113_job.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _job() -> dict:
    return json.loads(JOB.read_text(encoding="utf-8"))


def _source_path(job: dict, key: str) -> Path:
    return (JOB.parent / job["sources"][key]["path"]).resolve()


def _evidence() -> tuple[dict, np.ndarray, np.ndarray, dict]:
    job = _job()
    inventory = json.loads(_source_path(job, "exact_topology_inventory").read_text(encoding="utf-8"))
    labels = np.asarray(Image.open(_source_path(job, "exact_topology_labels")), dtype=np.int32)
    mask = np.asarray(Image.open(_source_path(job, "official_coverage_mask")).convert("L"), dtype=np.uint8)
    return inventory, labels, mask, job


def test_sources_are_hash_bound() -> None:
    job = _job()
    for name, source in job["sources"].items():
        path = _source_path(job, name)
        assert path.is_file()
        assert _sha(path) == source["sha256"]


def test_all_exact_components_and_pixels_validate() -> None:
    inventory, labels, mask, job = _evidence()
    components, metrics = kit.validate_topology(inventory, labels, mask, job["expected"])
    assert len(components) == metrics["component_count"] == 565
    assert metrics["official_pixel_count"] == 2_670_216
    assert metrics["maximum_label_value"] == 565
    assert metrics["unique_component_token_count"] == 565
    assert metrics["source_assigned_component_count"] == 390
    assert metrics["source_assigned_pixel_count"] == 891_468
    assert metrics["source_abstained_component_count"] == 175
    assert metrics["source_abstained_pixel_count"] == 1_778_748


def test_tokens_are_stable_unique_and_exclude_surface_hypotheses() -> None:
    inventory, labels, mask, job = _evidence()
    components, _ = kit.validate_topology(inventory, labels, mask, job["expected"])
    tokens = [item["component_token"] for item in components]
    assert len(tokens) == len(set(tokens)) == 565
    assert all(len(token) == 16 for token in tokens)
    assert all(item["encoding_role"] == "neutral_topology_container" for item in components)
    assert all(item["physical_surface_claim"] is False for item in components)
    assert all(item["physical_side_claim"] is False for item in components)
    assert all(item["polarity_claim"] is False for item in components)
    assert all("physical_surface" not in item for item in components)
    first_raw = inventory["islands"][0]
    assert kit.stable_component_token(first_raw) == kit.stable_component_token(dict(first_raw))


def test_texture_alpha_is_exact_full_official_union() -> None:
    inventory, labels, mask, job = _evidence()
    components, _ = kit.validate_topology(inventory, labels, mask, job["expected"])
    texture, alpha, decoder = kit.render_texture(labels, components, kit._policy(job))
    official = mask > 0
    assert texture.size == (2048, 2048)
    assert texture.mode == "RGBA"
    assert set(np.unique(alpha).tolist()) == {0, 255}
    assert np.array_equal(alpha == 255, official)
    assert int((alpha == 255).sum()) == 2_670_216
    assert len(decoder) == 565
    assert all(item["encoding_role"] == "neutral_topology_container" for item in decoder)


def test_absolute_orientation_is_not_bbox_normalized_or_symmetric() -> None:
    inventory, labels, mask, job = _evidence()
    components, _ = kit.validate_topology(inventory, labels, mask, job["expected"])
    texture, alpha, decoder = kit.render_texture(labels, components, kit._policy(job))
    symmetry = kit._symmetry_metrics(texture, alpha)
    assert symmetry["equals_horizontal_flip"] is False
    assert symmetry["equals_vertical_flip"] is False
    assert symmetry["equals_rotate_180"] is False
    assert all(item["coordinate_encoding"]["space"] == "absolute_2048_uv_canvas" for item in decoder)
    assert all(item["coordinate_encoding"]["origin"] == "top_left" for item in decoder)
    rgba = np.asarray(texture)
    official = mask > 0
    # The diagnostic must have substantial high-red, high-green, and high-blue
    # marks inside the exact official union, proving the three orientation axes
    # survived the neutral field and component-token overlays.
    assert int(np.count_nonzero(official & (rgba[:, :, 0] > 180) & (rgba[:, :, 1] < 150))) > 5_000
    assert int(np.count_nonzero(official & (rgba[:, :, 1] > 180) & (rgba[:, :, 0] < 150))) > 5_000
    assert int(np.count_nonzero(official & (rgba[:, :, 2] > 180))) > 5_000


def test_capture_protocol_is_multiview_and_never_mirrors() -> None:
    job = _job()
    roles = kit.validate_capture_roles(job)
    assert len(roles) == 10
    assert sum(len(item["capture_states"]) for item in roles) == 20
    assert {item["capture_states"][0] for item in roles} == {"wire_off"}
    assert all(any("no image mirroring" in rule for rule in item["camera_rules"]) for item in roles)
    assert any(item["role_id"].endswith("nose_head_on") for item in roles)
    assert any(item["role_id"].endswith("rear_head_on") for item in roles)


def test_build_is_fail_closed_and_byte_repeatable(tmp_path: Path) -> None:
    output = tmp_path / "kit"
    first = kit.build(JOB, output)
    first_hashes = {path.name: _sha(path) for path in output.iterdir() if path.is_file()}
    second = kit.build(JOB, output)
    second_hashes = {path.name: _sha(path) for path in output.iterdir() if path.is_file()}
    assert first_hashes == second_hashes
    assert first["audit"]["status"] == "PASS_FULL_TOPOLOGY_DIAGNOSTIC_NOT_DELIVERY"
    assert second["report"]["metrics"]["component_count"] == 565
    assert second["report"]["metrics"]["encoded_pixel_count"] == 2_670_216
    assert second["report"]["metrics"]["outside_official_pixel_count"] == 0
    assert second["report"]["metrics"]["missing_official_pixel_count"] == 0
    assert second["report"]["metrics"]["overlap_pixel_count"] == 0
    assert second["report"]["metrics"]["guessed_pixel_count"] == 0
    assert all(second["audit"]["gates"].values())
    for claim in (
        "physical_surface_ownership",
        "physical_side_polarity",
        "surface_adjacency",
        "projector",
        "livery",
        "psd",
        "app",
        "delivery",
    ):
        assert second["report"]["claims"][claim] is False


def test_core_artifacts_match_across_output_directories(tmp_path: Path) -> None:
    one = tmp_path / "one"
    two = tmp_path / "two"
    kit.build(JOB, one)
    kit.build(JOB, two)
    for name in (
        "DLM_FULL_TOPOLOGY_CALIBRATION_TEXTURE_V2.png",
        "DLM_FULL_TOPOLOGY_CALIBRATION_ALPHA_V2.png",
        "FULL_TOPOLOGY_COMPONENT_DECODER_V2.json",
        "FULL_TOPOLOGY_CAPTURE_PROTOCOL_V2.md",
        "RUN113_FULL_TOPOLOGY_CALIBRATION_CONTACT.png",
    ):
        assert _sha(one / name) == _sha(two / name)


def test_hash_drift_is_rejected(tmp_path: Path) -> None:
    job = _job()
    for name in job["sources"]:
        job["sources"][name]["path"] = str(_source_path(job, name))
    job["sources"]["exact_topology_labels"]["sha256"] = "0" * 64
    bad_job = tmp_path / "bad_job.json"
    bad_job.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(kit.EvidenceError, match="exact_topology_labels_source_sha256_mismatch"):
        kit.build(bad_job, tmp_path / "out")


def test_official_mask_disagreement_is_rejected() -> None:
    inventory, labels, mask, job = _evidence()
    altered = mask.copy()
    y, x = np.argwhere(altered > 0)[0]
    altered[y, x] = 0
    with pytest.raises(kit.EvidenceError, match="official_mask_label_union_mismatch"):
        kit.validate_topology(inventory, labels, altered, job["expected"])
