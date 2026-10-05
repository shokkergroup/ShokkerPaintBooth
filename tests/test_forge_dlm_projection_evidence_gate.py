import hashlib
import json
from pathlib import Path

from PIL import Image

from _forge_dlm_projection_evidence_gate import (
    BATCH_SCHEMA,
    JOB_SCHEMA,
    audit_legacy_report,
    evaluate_batch,
    evaluate_job,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "_forge_data" / "dlm_projection_evidence_gate"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _image(path: Path, color: tuple[int, int, int, int]) -> None:
    Image.new("RGBA", (100, 100), color).save(path)


def _bound(path: Path) -> dict:
    return {"path": path.name, "sha256": _sha(path)}


def _valid_job(tmp_path: Path) -> Path:
    source = tmp_path / "source.png"
    mask = tmp_path / "mask.png"
    wire_a_off = tmp_path / "view_a_off.png"
    wire_a_on = tmp_path / "view_a_on.png"
    wire_b_off = tmp_path / "view_b_off.png"
    wire_b_on = tmp_path / "view_b_on.png"
    _image(source, (40, 80, 120, 255))
    _image(mask, (255, 255, 255, 255))
    _image(wire_a_off, (80, 80, 80, 255))
    _image(wire_a_on, (100, 100, 100, 255))
    _image(wire_b_off, (120, 120, 120, 255))
    _image(wire_b_on, (140, 140, 140, 255))
    train_points = [
        ("t0", [5, 5], [6, 6]),
        ("t1", [95, 5], [94, 6]),
        ("t2", [5, 95], [6, 94]),
        ("t3", [95, 95], [94, 94]),
        ("t4", [50, 10], [50, 11]),
        ("t5", [50, 90], [50, 89]),
    ]
    pair_a = {"wire_off": _bound(wire_a_off), "wire_on": _bound(wire_a_on)}
    pair_b = {"wire_off": _bound(wire_b_off), "wire_on": _bound(wire_b_on)}
    payload = {
        "$schema": JOB_SCHEMA,
        "projector_id": "synthetic_piecewise_positive",
        "surface_class": "semantic_object",
        "source_asset": _bound(source),
        "target_mask": _bound(mask),
        "transform": {"method": "piecewise_affine", "determinant": 1.0, "mirror": False},
        "train_anchors": [
            {"id": anchor_id, "source_xy": src, "uv_xy": uv}
            for anchor_id, src, uv in train_points
        ],
        "holdout_observations": [
            {"id": "h0", "view_id": "view_a", "evidence_type": "iracing_wire_pair", "evidence_pair": pair_a, "predicted_uv": [20, 20], "expected_uv": [21, 20]},
            {"id": "h1", "view_id": "view_a", "evidence_type": "iracing_wire_pair", "evidence_pair": pair_a, "predicted_uv": [80, 20], "expected_uv": [80, 21]},
            {"id": "h2", "view_id": "view_b", "evidence_type": "iracing_wire_pair", "evidence_pair": pair_b, "predicted_uv": [20, 80], "expected_uv": [21, 80]},
            {"id": "h3", "view_id": "view_b", "evidence_type": "iracing_wire_pair", "evidence_pair": pair_b, "predicted_uv": [80, 80], "expected_uv": [80, 81]},
        ],
    }
    job = tmp_path / "job.json"
    job.write_text(json.dumps(payload), encoding="utf-8")
    return job


def test_independent_low_residual_holdout_accepts(tmp_path: Path) -> None:
    report = evaluate_job(_valid_job(tmp_path))
    assert report["status"] == "accept"
    assert report["metrics"]["valid_train_anchors"] == 6
    assert report["metrics"]["valid_holdout_anchors"] == 4
    assert report["metrics"]["independent_holdout_views"] == 2
    assert report["metrics"]["distinct_holdout_evidence_pairs"] == 2
    assert report["metrics"]["holdout_p95_error_px"] == 1.0
    assert report["claims"]["self_roundtrip_is_acceptance_authority"] is False


def test_self_roundtrip_without_independent_holdout_abstains(tmp_path: Path) -> None:
    job = _valid_job(tmp_path)
    payload = json.loads(job.read_text(encoding="utf-8"))
    payload["holdout_observations"] = []
    payload["declared_roundtrip_alpha_iou"] = 1.0
    job.write_text(json.dumps(payload), encoding="utf-8")
    report = evaluate_job(job)
    assert report["status"] == "abstain"
    assert any("holdout_observations" in item for item in report["insufficient_evidence"])


def test_duplicate_pair_labels_do_not_fake_independent_views(tmp_path: Path) -> None:
    job = _valid_job(tmp_path)
    payload = json.loads(job.read_text(encoding="utf-8"))
    first_pair = payload["holdout_observations"][0]["evidence_pair"]
    for item in payload["holdout_observations"]:
        item["evidence_pair"] = first_pair
    job.write_text(json.dumps(payload), encoding="utf-8")
    report = evaluate_job(job)
    assert report["status"] == "abstain"
    assert report["metrics"]["distinct_holdout_evidence_pairs"] == 1


def test_reflection_and_large_holdout_residual_reject(tmp_path: Path) -> None:
    job = _valid_job(tmp_path)
    payload = json.loads(job.read_text(encoding="utf-8"))
    payload["transform"]["determinant"] = -1.0
    payload["holdout_observations"][0]["predicted_uv"] = [50, 50]
    job.write_text(json.dumps(payload), encoding="utf-8")
    report = evaluate_job(job)
    assert report["status"] == "reject"
    assert "reflection_or_degenerate_transform" in report["contradictions"]
    assert "holdout_single_error_exceeded" in report["contradictions"]


def test_stale_evidence_hash_rejects(tmp_path: Path) -> None:
    job = _valid_job(tmp_path)
    payload = json.loads(job.read_text(encoding="utf-8"))
    payload["holdout_observations"][0]["evidence_pair"]["wire_on"]["sha256"] = "0" * 64
    job.write_text(json.dumps(payload), encoding="utf-8")
    report = evaluate_job(job)
    assert report["status"] == "reject"
    assert any("sha256_mismatch" in item for item in report["contradictions"])


def test_legacy_core_projection_reports_are_not_promotable() -> None:
    batch = FIXTURE_ROOT / "run120_legacy_reports.json"
    report = evaluate_batch(batch)
    assert report["status"] == "PASS_FIREWALL"
    assert report["counts"] == {"total": 5, "accept": 0, "abstain": 5, "reject": 0}
    assert all(item["independent_holdout_case_count"] == 0 for item in report["cases"])
    assert all(
        "independent_physical_holdout_missing" in item["insufficient_evidence"]
        for item in report["cases"]
    )
