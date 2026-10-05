import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

import _forge_dlm_release_gate as release_gate

from _forge_dlm_visual_sanity_gate import (
    JOB_SCHEMA,
    REVIEW_SCHEMA,
    evaluate_job,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save_mask(path: Path, array: np.ndarray) -> None:
    Image.fromarray(array.astype(np.uint8) * 255).save(path)


def _save_labels(path: Path, array: np.ndarray) -> None:
    Image.fromarray(array.astype(np.uint16)).save(path)


def _make_evidence(tmp_path: Path) -> dict[str, str]:
    result = {}
    colours = {
        "wire_qa": (40, 180, 90),
        "reference_contact": (60, 100, 210),
        "render_contact": (220, 130, 30),
        "full_canvas_review": (150, 70, 190),
    }
    for name, colour in colours.items():
        path = tmp_path / f"{name}.png"
        image = Image.new("RGB", (256, 128), colour)
        ImageDraw.Draw(image).rectangle((15, 15, 240, 110), outline=(255, 255, 255), width=3)
        image.save(path)
        result[name] = path.name
    return result


def _base_fixture(tmp_path: Path, *, failing: bool = False) -> Path:
    height = width = 128
    official = np.zeros((height, width), dtype=bool)
    official[8:120, 8:56] = True
    official[8:120, 72:120] = True
    ownership = np.zeros((height, width), dtype=np.uint16)
    ownership[8:120, 8:56] = 1
    ownership[8:120, 72:120] = 2
    paint = official.copy()
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[official] = (38, 82, 164)
    semantic_labels = np.zeros((height, width), dtype=np.uint16)
    if failing:
        paint[:, 56:] = False
        paint[0:4, 0:4] = True
        rgb[8:120, 8:56] = (224, 35, 35)
        rgb[8:120, 72:120] = (30, 45, 225)
        # Identical same-colour objects.  Object 1 also touches its physical
        # surface edge, proving the clipping check independently.
        semantic_labels[8:16, 8:16] = 1
        semantic_labels[20:28, 82:90] = 2
        rgb[semantic_labels > 0] = (250, 245, 235)
    else:
        # Equal red pixel counts preserve palette consistency, while a square
        # and long bar remain distinct physical artwork shapes.
        semantic_labels[28:36, 24:32] = 1
        semantic_labels[28:32, 88:104] = 2
        rgb[semantic_labels > 0] = (230, 54, 42)
    semantic = semantic_labels > 0

    candidate = tmp_path / "candidate.png"
    Image.fromarray(rgb).save(candidate)
    _save_mask(tmp_path / "official.png", official)
    _save_mask(tmp_path / "paint.png", paint)
    _save_mask(tmp_path / "semantic.png", semantic)
    _save_mask(tmp_path / "left.png", ownership == 1)
    _save_mask(tmp_path / "right.png", ownership == 2)
    _save_labels(tmp_path / "ownership.png", ownership)
    _save_labels(tmp_path / "objects.png", semantic_labels)

    evidence = _make_evidence(tmp_path) if not failing else {}
    review_path = tmp_path / "review.json"
    if not failing:
        evidence_hashes = {key: _sha(tmp_path / value) for key, value in evidence.items()}
        review_path.write_text(
            json.dumps(
                {
                    "$schema": REVIEW_SCHEMA,
                    "candidate_sha256": _sha(candidate),
                    "decision": "accept",
                    "reviewer_kind": "agent_visual",
                    "reviewer": "synthetic-control",
                    "reviewed_at": "2026-07-17T00:00:00Z",
                    "reviewed_evidence_sha256": evidence_hashes,
                    "checks": {
                        "full_canvas_sanity": True,
                        "no_floating_fragments": True,
                        "no_unexplained_blank_body_fields": True,
                        "readable_art_unclipped": True,
                        "side_palette_consistent": True,
                        "front_surfaces_coherent": True,
                        "no_duplicate_physical_art": True,
                    },
                    "blockers": [],
                }
            ),
            encoding="utf-8",
        )

    job = {
        "$schema": JOB_SCHEMA,
        "candidate": candidate.name,
        "official_mask": "official.png",
        "paint_mask": "paint.png",
        "semantic_art_mask": "semantic.png",
        "ownership_labels": "ownership.png",
        "semantic_object_labels": "objects.png",
        "side_masks": {"left": "left.png", "right": "right.png"},
        "side_palette_policy": "match",
        "evidence": evidence,
        "thresholds": {"required_canvas_size": 128},
    }
    if not failing:
        job["visual_review"] = review_path.name
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")
    return job_path


def test_complete_candidate_passes_all_sanity_proofs(tmp_path):
    job_path = _base_fixture(tmp_path)

    report = evaluate_job(job_path, tmp_path / "proof", allow_unsafe_test_thresholds=True)

    assert report["status"] == "pass"
    assert report["valid"] is True
    assert report["failures"] == []
    assert report["insufficient_evidence"] == []
    assert report["metrics"]["coverage"]["official_utilization"] == 1.0
    assert report["visual_review"]["reviewer"] == "synthetic-control"
    assert report["visual_review"]["reviewer_kind"] == "agent_visual"
    assert report["visual_review"]["reviewed_at"] == "2026-07-17T00:00:00Z"
    assert report["metrics"]["coverage"]["outside_official_paint_pixels"] == 0
    assert report["metrics"]["semantic_objects"]["evaluated_count"] == 2
    assert report["metrics"]["semantic_objects"]["duplicate_pairs"] == []
    assert report["metrics"]["side_pair"]["palette_js_divergence"] == 0.0
    assert (tmp_path / "proof" / "dlm_visual_sanity_QA.png").is_file()
    release_errors = release_gate._check_flat_visual(
        report,
        {"composite": report["candidate"]["sha256"]},
        "",
        "",
        datetime.now(timezone.utc),
    )
    assert release_errors == []
    assert (tmp_path / "proof" / "dlm_visual_sanity_report.json").is_file()


def test_obvious_flat_uv_failures_are_rejected_not_scored_away(tmp_path):
    job_path = _base_fixture(tmp_path, failing=True)

    report = evaluate_job(job_path, allow_unsafe_test_thresholds=True)

    assert report["status"] == "reject"
    assert report["valid"] is False
    joined = "\n".join(report["failures"])
    assert "official utilization" in joined
    assert "outside-official paint" in joined
    assert "largest unintended blank" in joined
    assert "boundary-risk fraction" in joined
    assert "near-identical" in joined
    assert "palette JS divergence" in joined
    assert "mean RGB distance" in joined
    assert report["insufficient_evidence"]  # missing contact/review proof also fails closed


def test_missing_exact_masks_abstains_instead_of_guessing_from_candidate_colour(tmp_path):
    candidate = tmp_path / "solid.png"
    Image.new("RGB", (128, 128), (250, 190, 20)).save(candidate)
    job_path = tmp_path / "job.json"
    job_path.write_text(
        json.dumps(
            {
                "$schema": JOB_SCHEMA,
                "candidate": candidate.name,
                "thresholds": {"required_canvas_size": 128},
            }
        ),
        encoding="utf-8",
    )

    report = evaluate_job(job_path, allow_unsafe_test_thresholds=True)

    assert report["status"] == "abstain"
    assert report["failures"] == []
    assert any("paint_mask" in value for value in report["insufficient_evidence"])
    assert any("semantic_object_labels" in value for value in report["insufficient_evidence"])


def test_owner_rejected_waffle_candidate_fails_real_adapter_union(tmp_path):
    root = Path(__file__).resolve().parents[1]
    candidate = root / (
        "_forge_out/codex_four_psd_delivery/waffle_house/CURRENT_BEST/"
        "WAFFLE_HOUSE_77_DLM_COMPOSITE.png"
    )
    official_path = root / (
        "_forge_out/codex_full_uv_recovery/run_02_official_template_authority/"
        "official_coverage_mask.png"
    )
    inventory_path = root / (
        "_forge_out/codex_full_uv_recovery/run_70_v7_exact_topology/"
        "dlm_exact_topology_inventory.json"
    )
    labels_path = root / (
        "_forge_out/codex_full_uv_recovery/run_70_v7_exact_topology/"
        "dlm_exact_topology_labels.png"
    )
    if not all(path.is_file() for path in (candidate, official_path, inventory_path, labels_path)):
        pytest.skip("bounded owner-rejected Waffle fixture is not available")

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    official = np.asarray(Image.open(official_path).convert("L")) > 0
    union = np.zeros_like(official)
    source_by_surface = {}
    for row in inventory["adapter_surfaces"]:
        path = Path(row["source_mask"]["path"])
        mask = np.asarray(Image.open(path).convert("L")) > 0
        union |= mask
        source_by_surface[row["physical_surface"]] = path
    _save_mask(tmp_path / "paint.png", union)
    _save_mask(tmp_path / "semantic.png", np.zeros_like(official))
    _save_labels(tmp_path / "objects.png", np.zeros_like(official, dtype=np.uint16))

    job = {
        "$schema": JOB_SCHEMA,
        "candidate": str(candidate),
        "official_mask": str(official_path),
        "paint_mask": "paint.png",
        "semantic_art_mask": "semantic.png",
        "ownership_labels": str(labels_path),
        "semantic_object_labels": "objects.png",
        "side_masks": {
            "left": str(source_by_surface["left_side"]),
            "right": str(source_by_surface["right_side"]),
        },
        "side_palette_policy": "match",
        "evidence": {},
    }
    job_path = tmp_path / "rejected-job.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")

    report = evaluate_job(job_path)

    assert report["status"] == "reject"
    coverage = report["metrics"]["coverage"]
    assert coverage["official_utilization"] == pytest.approx(0.886911, abs=1e-5)
    assert coverage["outside_official_paint_pixels"] == 135672
    joined = "\n".join(report["failures"])
    assert "official utilization" in joined
    assert "outside-official paint" in joined


def test_independent_side_palette_policy_preserves_reference_asymmetry(tmp_path):
    job_path = _base_fixture(tmp_path)
    candidate = tmp_path / "candidate.png"
    image = np.asarray(Image.open(candidate).convert("RGB"), dtype=np.uint8).copy()
    right = np.asarray(Image.open(tmp_path / "right.png").convert("L")) > 0
    image[right] = (232, 38, 38)
    Image.fromarray(image).save(candidate)

    review_path = tmp_path / "review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["candidate_sha256"] = _sha(candidate)
    review_path.write_text(json.dumps(review), encoding="utf-8")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    job["side_palette_policy"] = "independent"
    job_path.write_text(json.dumps(job), encoding="utf-8")

    report = evaluate_job(job_path, allow_unsafe_test_thresholds=True)

    assert report["status"] == "pass"
    assert report["metrics"]["side_pair"]["policy"] == "independent"
    assert report["metrics"]["side_pair"]["palette_js_divergence"] > 0.14


def test_production_job_cannot_weaken_locked_thresholds(tmp_path):
    job_path = _base_fixture(tmp_path)

    report = evaluate_job(job_path)

    assert report["status"] == "reject"
    assert any("per-job overrides are forbidden" in row for row in report["insufficient_evidence"])
    assert any("required 2048x2048" in row for row in report["failures"])
