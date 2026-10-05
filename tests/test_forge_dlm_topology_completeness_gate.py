import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import _forge_layers
from _forge_dlm_topology_completeness_gate import JOB_SCHEMA, evaluate_job


def _rgba(mask: np.ndarray, colour: tuple[int, int, int]) -> Image.Image:
    array = np.zeros((*mask.shape, 4), dtype=np.uint8)
    array[mask, :3] = colour
    array[mask, 3] = 255
    return Image.fromarray(array, "RGBA")


def _fixture(tmp_path: Path, *, mode: str) -> Path:
    size = 128
    official = np.zeros((size, size), dtype=bool)
    official[8:108, 8:108] = True
    official[112:120, 112:120] = True
    labels = np.zeros((size, size), dtype=np.uint16)
    labels[8:108, 8:108] = 1
    labels[112:120, 112:120] = 2
    if mode == "mismatched_labels":
        labels[112:120, 112:120] = 0

    full = np.ones((size, size), dtype=bool)
    if mode == "complete":
        projected = official.copy()
    else:
        projected = np.zeros_like(official)
        projected[8:108, 8:108] = True

    base = _rgba(full, (24, 70, 140))
    paint = _rgba(projected, (220, 48, 42))
    composite = Image.alpha_composite(base, paint)
    psd_path = tmp_path / "candidate.psd"
    _forge_layers.write_grouped_psd(
        [
            {"name": "BASE", "layers": [("unbounded canvas base", base)]},
            {"name": "PAINT", "layers": [("bounded projected paint", paint)]},
        ],
        composite,
        str(psd_path),
    )
    composite.save(tmp_path / "candidate.png")
    Image.fromarray(official.astype(np.uint8) * 255).save(tmp_path / "official.png")
    Image.fromarray(labels).save(tmp_path / "labels.png")
    job = {
        "$schema": JOB_SCHEMA,
        "candidate_flat": "candidate.png",
        "psd": "candidate.psd",
        "official_mask": "official.png",
        "topology_labels": "labels.png",
        "coverage_groups": ["BASE", "PAINT"],
        "output_dir": "proof",
        "legacy_validation_valid": True,
        "unsafe_allow_test_canvas": True,
        "unsafe_test_thresholds": {"minimum_component_pixels": 32},
    }
    path = tmp_path / "job.json"
    path.write_text(json.dumps(job), encoding="utf-8")
    return path


def test_complete_bounded_union_passes_despite_unbounded_canvas_base(tmp_path: Path):
    report = evaluate_job(_fixture(tmp_path, mode="complete"))
    assert report["status"] == "PASS"
    assert report["coverage"]["official_utilization"] == 1.0
    assert report["coverage"]["excluded_full_canvas_layer_count"] == 1
    assert report["coverage"]["flat_alpha_is_uninformative"] is True


def test_component_gate_rejects_hole_hidden_by_opaque_flat(tmp_path: Path):
    report = evaluate_job(_fixture(tmp_path, mode="component_hole"))
    # Global utilization would clear the legacy 0.985 threshold: the small
    # second island is only 64 of 10,064 official pixels.
    assert report["coverage"]["official_utilization"] > 0.985
    assert report["status"] == "REJECT"
    assert report["component_summary"]["missing_major_component_count"] == 1
    assert report["missing_major_components"][0]["label"] == 2
    assert report["coverage"]["flat_alpha_is_uninformative"] is True


def test_topology_label_union_mismatch_abstains(tmp_path: Path):
    report = evaluate_job(_fixture(tmp_path, mode="mismatched_labels"))
    assert report["status"] == "ABSTAIN"
    assert any("nonzero union" in value for value in report["insufficient_evidence"])


def test_production_threshold_override_is_forbidden(tmp_path: Path):
    path = _fixture(tmp_path, mode="complete")
    job = json.loads(path.read_text(encoding="utf-8"))
    job["thresholds"] = {"minimum_official_utilization": 0.1}
    path.write_text(json.dumps(job), encoding="utf-8")
    with pytest.raises(ValueError, match="overrides are forbidden"):
        evaluate_job(path)
