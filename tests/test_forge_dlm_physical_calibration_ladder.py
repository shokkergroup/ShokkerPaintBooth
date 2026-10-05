from pathlib import Path

from _forge_dlm_physical_calibration_ladder import evaluate_job


def test_ladder_requests_only_missing_stages(tmp_path):
    mask = tmp_path / "mask.bin"; mask.write_bytes(b"mask")
    import hashlib
    digest = hashlib.sha256(b"mask").hexdigest()
    base = {"geometry_id": "uvmask:" + digest, "mask": {"path": "mask.bin", "sha256": digest}}
    report = evaluate_job({"geometries": [base]}, tmp_path)
    assert report["accepted"] is False
    assert report["geometries"][0]["stage"] == "GEOMETRY_ONLY"
    assert len(report["geometries"][0]["targeted_requests"]) == 3


def test_two_role_hashes_then_orientation_then_render_reaches_release(tmp_path):
    mask = tmp_path / "mask.bin"; mask.write_bytes(b"mask")
    import hashlib
    digest = hashlib.sha256(b"mask").hexdigest()
    row = {"geometry_id": "uvmask:" + digest, "mask": {"path": "mask.bin", "sha256": digest}, "evidence": [
        {"role": "hood", "sha256": "a" * 64}, {"role": "hood", "sha256": "b" * 64},
        {"readable_direction": "forward", "matched_wire_pair": True}, {"render_validated": True},
    ]}
    report = evaluate_job({"geometries": [row]}, tmp_path)
    assert report["accepted"] is True
    assert report["geometries"][0]["targeted_requests"] == []
