import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from _forge_semantic_pair_equivalence_gate import JOB_SCHEMA, evaluate_job


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "_forge_data" / "semantic_pair_equivalence_gate"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_asset(path: Path, variant: str) -> None:
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if variant == "primary":
        draw.ellipse((42, 38, 212, 220), fill=(24, 24, 28, 255))
        draw.ellipse((58, 54, 196, 204), fill=(236, 236, 232, 255))
        draw.ellipse((91, 71, 164, 190), fill=(218, 58, 42, 255))
        draw.ellipse((108, 93, 147, 168), fill=(32, 36, 44, 255))
    elif variant == "independent":
        draw.ellipse((55, 28, 196, 132), fill=(30, 94, 222, 255))
        draw.ellipse((38, 104, 218, 224), fill=(236, 76, 48, 255))
        draw.ellipse((86, 77, 169, 184), fill=(246, 242, 225, 255))
    else:
        raise ValueError(variant)
    image.save(path)


def _transform(rotation: int = 0) -> dict:
    return {
        "rotation_deg": rotation,
        "car_space_pixel_scale": [1.0, 1.0],
        "readable_orientation": "upright",
        "readable_direction": "front_to_rear",
    }


def _job(tmp_path: Path, first: Path, second: Path, *, policy: str) -> Path:
    payload = {
        "$schema": JOB_SCHEMA,
        "pair_id": f"synthetic_{policy}",
        "policy": policy,
        "assets": {
            "first": {
                "source": {"path": first.name, "sha256": _sha(first)},
                "canonical_transform": _transform(),
            },
            "second": {
                "source": {"path": second.name, "sha256": _sha(second)},
                "canonical_transform": _transform(),
            },
        },
        "claims": {"calibration_only": True},
    }
    path = tmp_path / f"{policy}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_synthetic_exact_match_accepts(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _make_asset(first, "primary")
    _make_asset(second, "primary")

    report = evaluate_job(_job(tmp_path, first, second, policy="match"))

    assert report["status"] == "accept"
    assert report["metrics"]["alpha_iou"] == 1.0
    assert report["metrics"]["alpha_mae"] == 0.0
    assert report["metrics"]["rgba_similarity"] == 1.0
    assert report["metrics"]["palette_js"] == 0.0
    assert report["metrics"]["edge_topology_iou"] == 1.0
    assert report["blockers"] == []


def test_independent_policy_accepts_different_valid_assets(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _make_asset(first, "primary")
    _make_asset(second, "independent")

    report = evaluate_job(_job(tmp_path, first, second, policy="independent"))

    assert report["status"] == "accept"
    assert report["match_thresholds_applied"] is False
    assert report["metrics"]["alpha_iou"] < 0.9
    assert report["claims"]["policy_is_manifest_data"] is True


def test_not_comparable_policy_records_metrics_but_does_not_infer_match(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _make_asset(first, "primary")
    _make_asset(second, "independent")

    report = evaluate_job(_job(tmp_path, first, second, policy="not_comparable"))

    assert report["status"] == "accept"
    assert report["comparison_performed"] is True
    assert report["match_thresholds_applied"] is False


def test_stale_source_hash_rejects(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _make_asset(first, "primary")
    _make_asset(second, "primary")
    job_path = _job(tmp_path, first, second, policy="match")
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    payload["assets"]["second"]["source"]["sha256"] = "0" * 64
    job_path.write_text(json.dumps(payload), encoding="utf-8")

    report = evaluate_job(job_path)

    assert report["status"] == "reject"
    assert report["source_hash_mismatch"] is True
    assert "assets:second:source: sha256_mismatch" in report["contradictions"]


def test_missing_canonical_transform_abstains(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _make_asset(first, "primary")
    _make_asset(second, "primary")
    job_path = _job(tmp_path, first, second, policy="match")
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    del payload["assets"]["second"]["canonical_transform"]
    job_path.write_text(json.dumps(payload), encoding="utf-8")

    report = evaluate_job(job_path)

    assert report["status"] == "abstain"
    assert any("canonical_transform required" in item for item in report["insufficient_evidence"])


def test_mirroring_is_forbidden_and_rejects(tmp_path: Path) -> None:
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    _make_asset(first, "primary")
    _make_asset(second, "primary")
    job_path = _job(tmp_path, first, second, policy="match")
    payload = json.loads(job_path.read_text(encoding="utf-8"))
    payload["assets"]["second"]["canonical_transform"]["mirror_x"] = True
    job_path.write_text(json.dumps(payload), encoding="utf-8")

    report = evaluate_job(job_path)

    assert report["status"] == "reject"
    assert any("mirroring_forbidden" in item for item in report["contradictions"])
    assert report["claims"]["mirroring_or_inference_used"] is False


def test_owner_rejected_core4_number_pairs_remain_negative() -> None:
    jobs = sorted(FIXTURE_ROOT.glob("*_side_numbers.json"))
    assert len(jobs) == 4
    reports = [evaluate_job(path) for path in jobs]
    assert all(report["status"] == "reject" for report in reports)
    assert all(report["policy"] == "match" for report in reports)
    assert all(report["source_hash_mismatch"] is False for report in reports)
    assert all(report["metrics"]["alpha_iou"] < 0.9 for report in reports)
    assert all(report["claims"]["psd_or_delivery_produced"] is False for report in reports)
