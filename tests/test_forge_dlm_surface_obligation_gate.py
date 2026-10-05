import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from _forge_dlm_surface_obligation_gate import (
    JOB_SCHEMA,
    OFFICIAL_COMPONENTS_4,
    OFFICIAL_PIXELS,
    evaluate_job,
)


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = (
    ROOT
    / "_forge_out"
    / "codex_full_uv_recovery"
    / "run_02_official_template_authority"
    / "official_coverage_mask.png"
)
FIXTURE_ROOT = ROOT / "_forge_data" / "dlm_surface_obligation_gate"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _authority() -> np.ndarray:
    mask = np.asarray(Image.open(AUTHORITY).convert("L"), dtype=np.uint8) > 0
    labels, count = ndi.label(mask, structure=ndi.generate_binary_structure(2, 1))
    assert int(mask.sum()) == OFFICIAL_PIXELS
    assert count == OFFICIAL_COMPONENTS_4
    assert labels.shape == mask.shape
    return mask


def _save_rgba(path: Path, alpha: np.ndarray, colour=(40, 140, 220)) -> None:
    rgba = np.zeros((*alpha.shape, 4), dtype=np.uint8)
    rgba[..., :3] = colour
    rgba[..., 3] = alpha.astype(np.uint8) * 255
    Image.fromarray(rgba, "RGBA").save(path)


def _save_mask(path: Path, mask: np.ndarray) -> None:
    Image.fromarray(mask.astype(np.uint8) * 255, "L").save(path)


def _job(tmp_path: Path, layer: Path, *, layer_sha: str | None = None) -> Path:
    payload = {
        "$schema": JOB_SCHEMA,
        "candidate_id": "synthetic_surface_obligation_control",
        "authority": {
            "mask": {"path": str(AUTHORITY), "sha256": _sha(AUTHORITY)}
        },
        "planned_layers": [
            {
                "id": "counted_paint",
                "source": {
                    "path": layer.name,
                    "sha256": layer_sha or _sha(layer),
                },
                "generic_full_canvas_base": False,
            }
        ],
        "obligations": [
            {
                "id": "complete_paint_field",
                "classification": "paint_field",
                "mask": "authority",
                "rendered_by": ["counted_paint"],
            }
        ],
        "claims": {"calibration_only": True},
    }
    path = tmp_path / "job.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_synthetic_exact_complete_accepts_and_generic_base_never_counts(tmp_path: Path) -> None:
    official = _authority()
    counted = tmp_path / "counted.png"
    generic = tmp_path / "generic_base.png"
    _save_rgba(counted, official)
    _save_rgba(generic, np.ones_like(official))
    job = json.loads(_job(tmp_path, counted).read_text(encoding="utf-8"))
    job["planned_layers"].append(
        {
            "id": "generic_full_canvas_base",
            "source": {"path": generic.name, "sha256": _sha(generic)},
            "generic_full_canvas_base": True,
        }
    )
    job_path = tmp_path / "positive.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")

    report = evaluate_job(job_path)

    assert report["status"] == "accept"
    assert report["authority"]["actual_pixels"] == OFFICIAL_PIXELS
    assert (
        report["authority"]["actual_four_connected_components"]
        == OFFICIAL_COMPONENTS_4
    )
    assert report["classification"]["exactly_classified"] is True
    assert report["metrics"]["non_abstained_rendered_coverage"] == 1.0
    assert report["planned_layers"]["counted_union_pixels"] == OFFICIAL_PIXELS
    assert report["planned_layers"]["ignored_generic_base_count"] == 1
    assert (
        report["planned_layers"]["generic_full_canvas_base_counts_toward_coverage"]
        is False
    )


def test_missing_official_classification_rejects(tmp_path: Path) -> None:
    official = _authority()
    counted = tmp_path / "counted.png"
    partial = official.copy()
    labels, count = ndi.label(official, structure=ndi.generate_binary_structure(2, 1))
    assert count == OFFICIAL_COMPONENTS_4
    partial[labels == 1] = False
    partial_path = tmp_path / "partial.png"
    _save_rgba(counted, official)
    _save_mask(partial_path, partial)
    job = json.loads(_job(tmp_path, counted).read_text(encoding="utf-8"))
    job["obligations"][0]["mask"] = {
        "path": partial_path.name,
        "sha256": _sha(partial_path),
    }
    job_path = tmp_path / "missing.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")

    report = evaluate_job(job_path)

    assert report["status"] == "reject"
    assert report["classification"]["unclassified_official_pixels"] > 0
    assert any("official pixels unclassified" in item for item in report["blockers"])


def test_overlapping_obligations_reject(tmp_path: Path) -> None:
    official = _authority()
    counted = tmp_path / "counted.png"
    _save_rgba(counted, official)
    job = json.loads(_job(tmp_path, counted).read_text(encoding="utf-8"))
    job["obligations"].append(
        {
            "id": "duplicate_semantic_obligation",
            "classification": "semantic_object",
            "mask": "authority",
            "rendered_by": ["counted_paint"],
        }
    )
    job_path = tmp_path / "overlap.json"
    job_path.write_text(json.dumps(job), encoding="utf-8")

    report = evaluate_job(job_path)

    assert report["status"] == "reject"
    assert report["classification"]["overlapping_obligation_pixels"] == OFFICIAL_PIXELS
    assert any("overlapping obligation pixels" in item for item in report["blockers"])


def test_stale_planned_layer_hash_rejects(tmp_path: Path) -> None:
    official = _authority()
    counted = tmp_path / "counted.png"
    _save_rgba(counted, official)

    report = evaluate_job(_job(tmp_path, counted, layer_sha="0" * 64))

    assert report["status"] == "reject"
    assert "planned_layers:counted_paint: sha256_mismatch" in report["contradictions"]


def test_hole_and_outside_alpha_fail_locked_thresholds(tmp_path: Path) -> None:
    official = _authority()
    labels, count = ndi.label(official, structure=ndi.generate_binary_structure(2, 1))
    assert count == OFFICIAL_COMPONENTS_4
    areas = np.bincount(labels.ravel())
    largest_label = int(np.argmax(areas[1:]) + 1)
    bad_alpha = official.copy()
    bad_alpha[labels == largest_label] = False
    outside_coordinates = np.argwhere(~official)[:25_000]
    bad_alpha[outside_coordinates[:, 0], outside_coordinates[:, 1]] = True
    counted = tmp_path / "bad.png"
    _save_rgba(counted, bad_alpha)

    report = evaluate_job(_job(tmp_path, counted))

    assert report["status"] == "reject"
    assert report["metrics"]["non_abstained_rendered_coverage"] < 0.995
    assert report["metrics"]["outside_official_fraction"] > 0.001
    assert report["metrics"]["largest_unexplained_hole_fraction"] > 0.008


def test_preserved_owner_rejected_jobs_remain_negative() -> None:
    jobs = sorted(FIXTURE_ROOT.glob("*_owner_rejected.json"))
    assert len(jobs) == 4
    reports = [evaluate_job(path) for path in jobs]
    assert {report["candidate_id"] for report in reports} == {
        "waffle_house_v34_owner_rejected",
        "crystal_lake_v9_owner_rejected",
        "sex_wax_v11_owner_rejected",
        "dominos_v19_owner_rejected",
    }
    assert all(report["status"] == "reject" for report in reports)
    assert all(report["valid"] is False for report in reports)
    assert all(
        report["claims"]["psd_or_delivery_produced"] is False for report in reports
    )
