from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_dlm_topology_obligation_decode_gate import decode_candidate_landmarks_vectorized
from _forge_dlm_visibility_bound_obligation_gate import (
    VisibilityBoundObligationError,
    build,
    evaluate_visibility_bound_obligation,
)

ROOT = Path(__file__).resolve().parents[1]
JOB = ROOT / "_forge_data/dlm_visibility_bound_obligation_gate/run137_job.json"
OUT = ROOT / "_forge_out/codex_full_uv_recovery/run_137_visibility_bound_obligation_gate"


@pytest.fixture(scope="session")
def built():
    return build(JOB, OUT)


def test_exact_exhaustive_visibility_obligation_is_complete(built):
    exact = built["synthetic"]["synthetic_exact"]
    vector = exact["vector_decode"]
    bound = exact["visibility_bound_obligation"]
    assert vector["decoded_screen_pixel_count"] == 2_658_729
    assert vector["visibility_ledger"]["decoded_container_pixel_count"] == 2_658_729
    assert bound["independently_visible_container_count"] == 4_719
    assert bound["complete_visible_container_count"] == 4_719
    assert bound["incomplete_visible_container_count"] == 0
    assert bound["accepted_visibility_bound_obligation"] is True


def test_targetless_but_visible_container_closes_old_false_pass(built):
    row = built["synthetic"]["targetless_visible_container_rehearsal"]
    assert row["candidate_exact_container_ids"] == [1, 2]
    assert row["targeted_exact_container_ids"] == [1]
    assert row["targetless_but_visible_container_id"] == 2
    assert row["old_target_derived_gate"]["accepted_visible_container_obligation"] is True
    new = row["new_independent_visibility_gate"]
    assert new["accepted_visibility_bound_obligation"] is False
    assert new["incomplete_visible_container_ids"] == [2]


def test_visibility_ledger_is_independent_of_requested_targets(built):
    row = built["synthetic"]["targetless_visible_container_rehearsal"]
    vector = row["vector_decode"]
    assert vector["target_landmark_count"] == 6
    assert vector["recovered_target_landmark_count"] == 6
    assert vector["visibility_ledger"]["observed_container_ids"] == [1, 2]


def test_empty_visibility_never_passes(built):
    planned = json.loads((OUT.parent / "run_136_topology_obligation_decode_gate/SYNTHETIC_TOPOLOGY_OBLIGATION_REPORT.json").read_text(encoding="utf-8"))
    obligation = planned["vectorized_exhaustive_obligation"]
    obligation["container_results"] = built["synthetic"]["synthetic_exact"]["landmark_obligation"].get("container_results", [])
    if not obligation["container_results"]:
        obligation["container_results"] = [{"container_id": index, "complete": True, "topology_rank": 2} for index in range(1, 4_720)]
    result = evaluate_visibility_bound_obligation({"observed_container_ids": []}, obligation)
    assert result["accepted_visibility_bound_obligation"] is False


def test_all_axis_and_reflection_corruptions_reject(built):
    rows = built["synthetic"]["corruption_rehearsal"]
    assert [row["scenario"] for row in rows] == [
        "axis_family_swap",
        "u_coordinate_reflection",
        "v_coordinate_reflection",
        "chiral_signal_reflection",
    ]
    assert all(not row["visibility_bound_obligation"]["accepted_visibility_bound_obligation"] for row in rows)


def test_live_roles_stay_fail_closed(built):
    report = built["report"]
    assert report["status"] == "VISIBILITY_BOUND_CODEC_PASS_LIVE_ABSTAIN"
    assert report["counts"] == {
        "role_count": 10,
        "visibility_ledger_accepted_role_count": 0,
        "visibility_ledger_abstained_role_count": 10,
    }
    assert all(not row["accepted"] for row in report["role_results"])


def test_rank1_never_becomes_physical_authority(built):
    bound = built["synthetic"]["synthetic_exact"]["visibility_bound_obligation"]
    assert bound["rank1_visible_container_count"] == 243
    assert bound["rank1_requires_parent_surface_fusion"] is True
    assert bound["claims"]["physical_surface_ownership"] is False


def test_vector_decoder_rejects_mismatched_container_label_shape():
    image = np.zeros((2, 2, 3), dtype=np.uint8)
    images = {key: image for key in (
        "control_black", "control_white", "phase_u_01", "phase_u_16", "phase_u_128",
        "phase_v_01", "phase_v_16", "phase_v_128", "orientation_uv_chiral",
    )}
    result = decode_candidate_landmarks_vectorized(
        images, {}, np.ones((2, 2), dtype=bool), np.ones((2, 2), dtype=bool),
        np.asarray([[0, 0]], dtype=np.int32), container_labels=np.zeros((1, 1), dtype=np.int32),
    )
    assert result == {"accepted": False, "reasons": ["VECTOR_DECODE_CONTAINER_LABEL_SHAPE_INVALID"]}


def test_downstream_release_claims_remain_false(built):
    claims = built["report"]["claims"]
    assert claims["synthetic_independent_visibility_obligation"] is True
    for key in ("live_independent_visibility_obligation", "physical_surface_ownership", "physical_side_polarity", "readable_direction", "stored_orientation", "projector", "psd", "delivery", "app", "fidelity_95"):
        assert claims[key] is False


def test_full_resolution_review_boards_exist(built):
    del built
    expected = {
        "VISIBILITY_FALSE_PASS_BEFORE_AFTER_CONTACT.png": (1800, 980),
        "VISIBILITY_BOUND_OPERATOR_BOARD.png": (1800, 1200),
    }
    for name, size in expected.items():
        with Image.open(OUT / name) as opened:
            assert opened.size == size


def test_hash_binding_tamper_rejects(tmp_path):
    job = json.loads(JOB.read_text(encoding="utf-8"))
    for row in job["sources"].values():
        row["path"] = str((JOB.parent / row["path"]).resolve())
    job["sources"]["run135_sample_plan"]["sha256"] = "0" * 64
    path = tmp_path / "tampered.json"
    path.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(VisibilityBoundObligationError, match="run135_sample_plan_sha256_mismatch"):
        build(path, tmp_path / "out")


def test_reusable_modules_have_no_livery_identity_literals():
    forbidden = ("waffle", "domino", "crystal", "jason", "wax", "miller", "dew", "spider")
    for name in ("_forge_dlm_topology_obligation_decode_gate.py", "_forge_dlm_visibility_bound_obligation_gate.py"):
        source = (ROOT / name).read_text(encoding="utf-8").lower()
        assert not any(token in source for token in forbidden)
