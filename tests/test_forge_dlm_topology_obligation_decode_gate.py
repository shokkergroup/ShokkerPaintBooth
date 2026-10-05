from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_dlm_chiral_decode_gate import ASSETS, decode_samples
from _forge_dlm_topology_obligation_decode_gate import (
    TopologyObligationDecodeError,
    build,
    evaluate_landmark_obligation,
)

ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data/dlm_topology_obligation_decode_gate/run136_job.json"
OUT = ROOT / "_forge_out/codex_full_uv_recovery/run_136_topology_obligation_decode_gate"


@pytest.fixture(scope="session")
def built():
    return build(JOB, OUT)


def test_live_core4_stays_fail_closed_until_real_capture(built):
    report = built["report"]
    assert report["status"] == "TOPOLOGY_OBLIGATION_CODEC_PASS_LIVE_ABSTAIN"
    assert report["counts"] == {
        "role_count": 10,
        "run133_accepted_role_count": 0,
        "topology_obligation_accepted_role_count": 0,
        "topology_obligation_abstained_role_count": 10,
    }
    assert all(not row["accepted"] for row in report["role_results"])


def test_uniform_run133_sample_is_rejected_as_topologically_incomplete(built):
    baseline = built["synthetic"]["run133_uniform_baseline"]
    assert baseline["accepted_visible_container_obligation"] is False
    assert baseline["decoded_sample_count"] == 1024
    assert baseline["observed_container_count"] == 634
    assert baseline["complete_container_count"] == 0
    assert baseline["incomplete_observed_container_count"] == 634
    assert baseline["recovered_distinct_landmark_count"] == 11


def test_plan_driven_decode_recovers_every_landmark_exactly(built):
    planned = built["synthetic"]["run136_plan_driven"]
    assert planned["accepted_visible_container_obligation"] is True
    assert planned["container_count"] == 4719
    assert planned["complete_container_count"] == 4719
    assert planned["target_landmark_count"] == 28_314
    assert planned["recovered_distinct_landmark_count"] == 28_314
    assert planned["duplicate_decoded_native_uv_count"] == 0
    assert planned["maximum_native_residual_px"] == 0.0


def test_explicit_hash_bound_decoder_path_is_used(built):
    decoded = built["decode"]
    assert decoded["sample_strategy"] == "explicit_hash_bound_points"
    assert decoded["decoded_sample_count"] == 28_314
    assert decoded["exact_native_sample_count"] == 28_314
    assert decoded["unique_native_uv_count"] == 28_314


def test_vectorized_exhaustive_screen_decoder_recovers_all_targets(built):
    vector = built["synthetic"]["vectorized_exhaustive_decode"]
    assert vector["accepted"] is True
    assert vector["candidate_screen_pixel_count"] == 2_658_729
    assert vector["decoded_screen_pixel_count"] == 2_658_729
    assert vector["unique_decoded_native_uv_count"] == 2_658_729
    assert vector["recovered_target_landmark_count"] == 28_314
    assert vector["target_landmark_recovery_fraction"] == 1.0


def test_vectorized_decoder_rejects_axis_and_chiral_corruptions(built):
    rows = built["synthetic"]["vectorized_corruption_rehearsal"]
    assert [row["scenario"] for row in rows] == [
        "axis_family_swap",
        "u_coordinate_reflection",
        "v_coordinate_reflection",
        "chiral_signal_reflection",
    ]
    assert all(row["accepted"] is False for row in rows)
    assert max(row["target_landmark_recovery_fraction"] for row in rows) < 0.05

def test_one_missing_landmark_rejects_observed_container(built):
    clean = list(built["decode"]["decoded_uv_screen_samples"])
    degraded = clean[1:]
    plan = built["synthetic"]["run136_plan_driven"]
    manifest = json.loads((OUT.parent / "run_135_topology_stratified_sample_plan/NATIVE_CONTAINER_SAMPLE_PLAN.json").read_text(encoding="utf-8"))
    result = evaluate_landmark_obligation(degraded, manifest, built["labels"], 0.0)
    assert result["accepted_visible_container_obligation"] is False
    assert result["complete_container_count"] == plan["complete_container_count"] - 1
    assert result["incomplete_observed_container_count"] == 1


def test_duplicate_decode_replay_cannot_fill_six_landmarks(built):
    manifest = json.loads((OUT.parent / "run_135_topology_stratified_sample_plan/NATIVE_CONTAINER_SAMPLE_PLAN.json").read_text(encoding="utf-8"))
    first = manifest["containers"][0]["samples_uv"][0]
    repeated = [{"native_u": first[0], "native_v": first[1]} for _ in range(12)]
    result = evaluate_landmark_obligation(repeated, manifest, built["labels"], 0.0)
    assert result["duplicate_decoded_native_uv_count"] == 11
    assert result["recovered_distinct_landmark_count"] == 1
    assert result["complete_container_count"] == 0
    assert result["accepted_visible_container_obligation"] is False


def test_explicit_decoder_rejects_point_outside_candidate():
    images = {asset: np.zeros((2, 2, 3), dtype=np.uint8) for asset in ASSETS}
    coverage = np.ones((2, 2), dtype=bool)
    candidate = np.ones((2, 2), dtype=bool)
    candidate[1, 1] = False
    result = decode_samples(
        images,
        {},
        coverage,
        candidate,
        {"maximum_sample_count": 4},
        explicit_points_yx=np.asarray([[1, 1]], dtype=np.int32),
    )
    assert result == {"accepted": False, "reasons": ["CHIRAL_DECODE_EXPLICIT_POINT_OUTSIDE_CANDIDATE"]}


def test_rank1_fragments_remain_parent_fusion_or_abstention(built):
    planned = built["synthetic"]["run136_plan_driven"]
    assert planned["rank1_container_count"] == 243
    assert planned["rank1_requires_parent_surface_fusion"] is True
    assert all(not row["physical_orientation_allowed"] for row in planned["container_results"])


def test_downstream_release_claims_remain_false(built):
    claims = built["report"]["claims"]
    assert claims["synthetic_topology_obligation_decode"] is True
    for key in ("live_topology_obligation_decode", "physical_surface_ownership", "physical_side_polarity", "readable_direction", "stored_orientation", "projector", "psd", "delivery", "app", "fidelity_95"):
        assert claims[key] is False


def test_evidence_boards_exist_at_full_review_size(built):
    del built
    expected = {
        "TOPOLOGY_OBLIGATION_BEFORE_AFTER_CONTACT.png": (1800, 1030),
        "TOPOLOGY_OBLIGATION_OPERATOR_BOARD.png": (1800, 1200),
    }
    for name, size in expected.items():
        with Image.open(OUT / name) as opened:
            assert opened.size == size


def test_hash_bound_sample_plan_tamper_rejects(tmp_path):
    job = json.loads(JOB.read_text(encoding="utf-8"))
    for source in job["sources"].values():
        source["path"] = str((JOB.parent / source["path"]).resolve())
    job["sources"]["run135_sample_plan"]["sha256"] = "0" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(TopologyObligationDecodeError, match="run135_sample_plan_sha256_mismatch"):
        build(path, tmp_path / "out")


def test_reusable_module_has_no_livery_identity_literals():
    source = (ROOT / "_forge_dlm_topology_obligation_decode_gate.py").read_text(encoding="utf-8").lower()
    forbidden = ("waffle", "domino", "crystal", "jason", "wax", "miller", "dew", "spider")
    assert not any(token in source for token in forbidden)