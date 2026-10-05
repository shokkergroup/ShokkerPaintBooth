from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_dlm_chiral_decode_gate import ASSETS
from _forge_dlm_live_visibility_decode_gate import (
    LiveVisibilityDecodeError,
    build,
    evaluate_live_route_uniqueness,
    live_frame_still_hash_bound,
    unique_rows_by_key,
    required_role_assets,
    responsive_candidate,
)

ROOT=Path(__file__).resolve().parents[1]
JOB=ROOT/"_forge_data/dlm_live_visibility_decode_gate/run138_job.json"
OUT=ROOT/"_forge_out/codex_full_uv_recovery/run_138_live_visibility_decode_gate"


@pytest.fixture(scope="session")
def built():
    return build(JOB,OUT)


def test_live_roles_require_atomic_220_frame_capture(built):
    report=built["report"]
    assert report["status"]=="LIVE_VISIBILITY_DECODE_ABSTAIN"
    assert report["counts"]=={
        "role_count":10,
        "expected_frame_count":220,
        "routed_frame_count":0,
        "bookend_accepted_role_count":0,
        "decode_ready_role_count":0,
        "live_visibility_accepted_role_count":0,
        "live_visibility_abstained_role_count":10,
    }
    assert all(not row["accepted"] for row in report["role_results"])


def test_absent_frames_are_missing_not_invisible_surfaces(built):
    for row in built["report"]["role_results"]:
        assert row["accepted_role_frame_count"]==0
        assert row["complete_decode_asset_pair_count"]==0
        assert "LIVE_DECODE_REQUIRES_ATOMIC_22_FRAME_BOOKEND_COHORT" in row["reasons"]
        assert row["decode"] is None


def test_each_role_has_exact_nine_asset_decode_stack(built):
    for row in built["report"]["role_results"]:
        assert [item["texture_asset_id"] for item in row["asset_matrix"]]==list(ASSETS)
        assert len(row["asset_matrix"])==9
        assert all(not item["complete"] for item in row["asset_matrix"])


def test_schedule_selects_start_controls_and_middle_codec_assets():
    job=json.loads(JOB.read_text(encoding="utf-8"))
    path=(JOB.parent/job["sources"]["run131_schedule"]["path"]).resolve()
    schedule=json.loads(path.read_text(encoding="utf-8"))["schedule"]
    selected=required_role_assets(schedule)
    assert len(selected)==10
    for assets in selected.values():
        assert tuple(assets)==ASSETS
        assert assets["control_black"]["bookend_position"]=="start"
        assert assets["control_white"]["bookend_position"]=="start"
        assert all(assets[key]["bookend_position"]=="middle" for key in ASSETS[2:])


def test_synthetic_same_code_path_completes_all_visible_containers(built):
    result=built["report"]["synthetic_holdout"]
    bound=result["visibility_bound_obligation"]
    assert result["accepted"] is True
    assert result["responsive_candidate_pixel_count"]==2_658_729
    assert bound["independently_visible_container_count"]==4_719
    assert bound["complete_visible_container_count"]==4_719
    assert bound["incomplete_visible_container_count"]==0


def test_responsive_candidate_uses_positive_three_channel_span():
    black=np.zeros((2,2,3),dtype=np.uint8)
    white=np.full((2,2,3),40,dtype=np.uint8)
    white[0,1,2]=5
    images={key:black.copy() for key in ASSETS}
    images["control_black"]=black
    images["control_white"]=white
    mask=responsive_candidate(images,10)
    assert mask.tolist()==[[True,False],[True,True]]


def test_responsive_candidate_rejects_incomplete_stack():
    with pytest.raises(LiveVisibilityDecodeError,match="live_decode_asset_stack_incomplete"):
        responsive_candidate({},10)


def test_downstream_release_claims_remain_false(built):
    claims=built["report"]["claims"]
    assert claims["synthetic_live_decode_path"] is True
    for key in ("live_visibility_decode","physical_surface_ownership","physical_side_polarity","readable_direction","stored_orientation","projector","psd","delivery","app","fidelity_95"):
        assert claims[key] is False


def test_boards_exist_at_full_review_size(built):
    del built
    expected={"LIVE_VISIBILITY_COHORT_BEFORE_AFTER.png":(1800,980),"LIVE_VISIBILITY_ROLE_OPERATOR_BOARD.png":(1800,1200)}
    for name,size in expected.items():
        with Image.open(OUT/name) as opened:
            assert opened.size==size


def test_hash_binding_tamper_rejects(tmp_path):
    job=json.loads(JOB.read_text(encoding="utf-8"))
    for row in job["sources"].values():
        row["path"]=str((JOB.parent/row["path"]).resolve())
    job["sources"]["run131_scan"]["sha256"]="0"*64
    path=tmp_path/"tampered.json";path.write_text(json.dumps(job),encoding="utf-8")
    with pytest.raises(LiveVisibilityDecodeError,match="run131_scan_sha256_mismatch"):
        build(path,tmp_path/"out")


def test_live_frame_hash_is_revalidated_at_decode_boundary(tmp_path):
    frame = tmp_path / "frame.png"
    frame.write_bytes(b"first")
    import hashlib
    row = {"path": str(frame), "sha256": hashlib.sha256(frame.read_bytes()).hexdigest()}
    assert live_frame_still_hash_bound(row) is True
    frame.write_bytes(b"mutated-after-scan")
    assert live_frame_still_hash_bound(row) is False
    assert live_frame_still_hash_bound({"path": None, "sha256": None}) is False


def test_live_scan_routes_are_unique_and_duplicate_mutation_rejects(built):
    route = built["route_uniqueness"]
    assert route["accepted"] is True
    assert route["unique_frame_route_count"] == 220
    assert route["unique_pair_route_count"] == 110
    assert route["unique_bookend_role_count"] == 10
    assert route["duplicate_route_count"] == 0
    duplicate = [{"pair_id": "pair", "wire_state": "wire_off"}] * 2
    with pytest.raises(LiveVisibilityDecodeError, match="live_frame_route_duplicate"):
        unique_rows_by_key(
            duplicate,
            lambda row: (row["pair_id"], row["wire_state"]),
            "live_frame_route",
        )


def test_reusable_module_has_no_livery_identity_literals():
    source=(ROOT/"_forge_dlm_live_visibility_decode_gate.py").read_text(encoding="utf-8").lower()
    forbidden=("waffle","domino","crystal","jason","wax","miller","dew","spider","sponsor","car_name")
    assert not any(token in source for token in forbidden)
