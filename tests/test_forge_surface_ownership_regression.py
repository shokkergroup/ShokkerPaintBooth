from pathlib import Path
import json

import pytest
import numpy as np
from PIL import Image

import _forge_surface_ownership_regression as regression


def _report(score: float, left: float, right: float) -> dict:
    return {
        "combined_visual_fidelity": score,
        "views": [
            {"role": "left_profile", "metrics": {"visual_fidelity": left}},
            {"role": "right_profile", "metrics": {"visual_fidelity": right}},
        ],
    }


def test_parse_case_keeps_windows_paths() -> None:
    name, profiles, composite = regression.parse_case("sample=C:/profiles.json=C:/composite.png")
    assert name == "sample"
    assert profiles == Path("C:/profiles.json")
    assert composite == Path("C:/composite.png")


def test_parse_case_rejects_incomplete_spec() -> None:
    with pytest.raises(Exception):
        regression.parse_case("sample=C:/profiles.json")


def test_gate_accepts_bounded_non_regression_and_valid_seam() -> None:
    gate = regression.gate_case(
        _report(90.0, 91.0, 89.0),
        _report(89.7, 90.3, 89.1),
        {"valid": True, "weighted_continuity_score": 92.0, "audited_overlap_pixels": 800},
        maximum_case_regression=0.5,
        maximum_view_regression=1.0,
        baseline_observed_pixels=1000,
        candidate_observed_pixels=995,
    )
    assert gate["passed"]
    assert gate["delta"] == -0.3
    assert gate["coverage_valid"]


def test_gate_fails_one_hidden_view_regression() -> None:
    gate = regression.gate_case(
        _report(90.0, 91.0, 89.0),
        _report(89.8, 89.9, 89.7),
        {"valid": True, "weighted_continuity_score": 92.0, "audited_overlap_pixels": 800},
        maximum_case_regression=0.5,
        maximum_view_regression=1.0,
    )
    assert gate["case_non_regression"]
    assert not gate["views_non_regression"]
    assert not gate["passed"]


def test_gate_fails_invalid_seam() -> None:
    gate = regression.gate_case(
        _report(90.0, 91.0, 89.0),
        _report(90.2, 91.2, 89.2),
        {"valid": False, "weighted_continuity_score": 82.0, "audited_overlap_pixels": 800},
        maximum_case_regression=0.5,
        maximum_view_regression=1.0,
    )
    assert not gate["seam_valid"]
    assert not gate["passed"]


def test_gate_fails_observed_coverage_loss() -> None:
    gate = regression.gate_case(
        _report(90.0, 91.0, 89.0),
        _report(90.2, 91.2, 89.2),
        {"valid": True, "weighted_continuity_score": 92.0, "audited_overlap_pixels": 800},
        maximum_case_regression=0.5,
        maximum_view_regression=1.0,
        baseline_observed_pixels=1000,
        candidate_observed_pixels=980,
        minimum_coverage_ratio=0.99,
    )
    assert not gate["coverage_valid"]
    assert not gate["passed"]


def test_projection_density_uses_fixed_target_union(tmp_path: Path) -> None:
    mask = np.zeros((4, 4), dtype=np.uint8)
    mask[:, :2] = 255
    Image.fromarray(mask, "L").save(tmp_path / "side.png")
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[:, :2, 3] = 255
    Image.fromarray(rgba, "RGBA").save(tmp_path / "observed.png")
    adapter = {
        "canvas": [4, 4],
        "surfaces": {"side": {"mask_path": "side.png"}},
    }
    adapter_path = tmp_path / "adapter.json"
    adapter_path.write_text(json.dumps(adapter), encoding="utf-8")
    result = regression.projection_density_on_target(
        adapter_path,
        {"composite": str(tmp_path / "observed.png"), "observed_surfaces": [{"surface": "side"}]},
    )
    assert result == {"observed_pixels": 8, "target_pixels": 8, "density": 1.0}
