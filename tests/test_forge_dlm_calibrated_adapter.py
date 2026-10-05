from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_dlm_calibrated_adapter import REQUIRED_ROLES, compile_calibrated_adapter


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _thresholds(**overrides: float) -> dict[str, float]:
    value = {
        "min_official_ownership_coverage": 0.98,
        "min_official_mapped_coverage": 0.95,
        "max_outside_official_fraction": 0.0,
        "max_surface_conflict_fraction": 0.0,
        "min_surface_coverage": 0.95,
        "min_surface_views": 2.0,
        "min_surface_mean_confidence": 0.9,
        "max_surface_withheld_p95_residual": 0.5,
        "min_role_withheld_coverage": 0.9,
        "min_role_domain_coverage": 0.9,
        "min_role_delivery_coverage": 0.9,
    }
    value.update(overrides)
    return value


def _fixture(
    root: Path,
    *,
    confidence: float = 0.97,
    screen_error: float = 0.0,
    mapper_contradiction: bool = False,
    fusion_conflict: bool = False,
    topology_unaccounted: int = 0,
) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    shape = (24, 32)
    yy, xx = np.indices(shape)
    official = (xx >= 2) & (xx < 30) & (yy >= 2) & (yy < 22)
    labels = np.zeros(shape, dtype=np.uint16)
    labels[official] = 1
    label_path = root / "labels.png"
    Image.fromarray(labels).save(label_path)
    topology = {
        "$schema": "shokk-forge.dlm-exact-topology/v1",
        "livery_agnostic": True,
        "claims": {"topology_accounting": True, "correspondence": False, "delivery_ready": False},
        "label_map": {"path": label_path.name, "sha256": _sha(label_path)},
        "adapter_surfaces": [
            {"physical_surface": "left_side"},
            {"physical_surface": "right_side"},
        ],
        "topology": {
            "component_count": 1,
            "official_pixel_count": int(official.sum()),
            "unaccounted_official_pixel_count": topology_unaccounted,
        },
    }
    topology_path = root / "topology.json"
    _write_json(topology_path, topology)
    calibration = {
        "$schema": "shokk-forge.uv-calibration-pack/v1",
        "canvas": [shape[1], shape[0]],
        "surface_lookup": [
            {"id": 1, "surface": "left_side"},
            {"id": 2, "surface": "right_side"},
        ],
    }
    calibration_path = root / "calibration.json"
    _write_json(calibration_path, calibration)
    surface = np.zeros(shape, dtype=np.uint16)
    surface[official & (xx < 16)] = 1
    surface[official & (xx >= 16)] = 2
    conflict = np.zeros(shape, dtype=bool)
    if fusion_conflict:
        conflict[10, 10] = True
    cross_path = root / "cross.npz"
    np.savez_compressed(
        cross_path,
        surface_id=surface,
        surface_conflict=conflict,
        visibility_count=np.where(official, 5, 0).astype(np.uint16),
    )
    fusion_views = []
    mapper_reports: dict[str, Path] = {}
    for index, role in enumerate(REQUIRED_ROLES):
        screen = np.stack((xx * 1.15 + index * 2.0, yy * 0.95 + index), axis=2).astype(np.float32)
        source_path = root / f"view_{role}.npz"
        np.savez_compressed(
            source_path,
            screen_xy=screen,
            confidence_mean=np.where(official, confidence, 0).astype(np.float32),
            surface_id=surface,
        )
        fusion_views.append({"role": role, "output_sha256": _sha(source_path)})
        mapped_surface = surface.copy()
        if mapper_contradiction and role == "left":
            mapped_surface[10, 10] = 2 if surface[10, 10] == 1 else 1
        mapper_npz = root / f"mapped_{role}.npz"
        withheld = official & (((xx + yy) % 3) != 0)
        mapped_xy = screen.copy()
        mapped_xy[official] += screen_error
        mapped_xy[~official] = np.nan
        np.savez_compressed(
            mapper_npz,
            screen_xy=mapped_xy,
            valid=official,
            surface_id=mapped_surface,
            withheld=withheld,
        )
        mapper = {
            "$schema": "shokk-forge.triangulated-uv-screen-map/v1",
            "role": role,
            "source": source_path.name,
            "source_sha256": _sha(source_path),
            "output": {"path": mapper_npz.name, "sha256": _sha(mapper_npz)},
            "geometric_mapping_ready": True,
            "evidence": {
                "withheld_coverage": 1.0,
                "domain_coverage": 1.0,
                "delivery_mask_coverage": 1.0,
            },
        }
        mapper_path = root / f"mapper_{role}.json"
        _write_json(mapper_path, mapper)
        mapper_reports[role] = mapper_path
    fusion = {
        "$schema": "shokk-forge.uv-correspondence-fusion/v1",
        "roles": list(REQUIRED_ROLES),
        "readiness": {"correspondence_ready": True},
        "cross_view": {"output": cross_path.name, "output_sha256": _sha(cross_path)},
        "views": fusion_views,
    }
    fusion_path = root / "fusion.json"
    _write_json(fusion_path, fusion)
    return {
        "topology": topology_path,
        "calibration": calibration_path,
        "fusion": fusion_path,
        "mappers": mapper_reports,
        "output": root / "compiled",
    }


def _compile(fixture: dict, **threshold_overrides: float) -> dict:
    return compile_calibrated_adapter(
        fixture["topology"],
        fixture["calibration"],
        fixture["fusion"],
        fixture["mappers"],
        fixture["output"],
        thresholds=_thresholds(**threshold_overrides),
        allow_unsafe_test_thresholds=True,
    )


def test_complete_five_view_evidence_compiles_geometry_only(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_complete")
    result = _compile(fixture)
    assert result["physical_adapter_ready"]
    assert not result["livery_ready"]
    assert not result["psd_ready"]
    assert not result["delivery_ready"]
    assert result["metrics"]["ownership_contradiction_pixels"] == 0
    assert result["metrics"]["mapped_outside_official_pixels"] == 0
    assert (fixture["output"] / "calibrated_physical_adapter.npz").is_file()
    assert (fixture["output"] / "CALIBRATED_ADAPTER_QA.png").is_file()
    assert all(row["ready"] for row in result["surfaces"])


def test_missing_mapper_role_fails_closed(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_missing")
    fixture["mappers"].pop("rear")
    result = _compile(fixture)
    assert not result["physical_adapter_ready"]
    assert result["blockers"] == ["exact_five_mapper_roles_required"]
    assert not (fixture["output"] / "calibrated_physical_adapter.npz").exists()


def test_mapper_surface_contradiction_is_measured_and_rejected(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_contradiction", mapper_contradiction=True)
    result = _compile(fixture)
    assert not result["physical_adapter_ready"]
    assert result["metrics"]["ownership_contradiction_pixels"] == 1
    assert "zero_mapper_ownership_contradictions" in result["blockers"]


def test_low_per_surface_confidence_abstains(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_confidence", confidence=0.65)
    result = _compile(fixture)
    assert not result["physical_adapter_ready"]
    assert "all_declared_surfaces_ready" in result["blockers"]
    assert all(not row["checks"]["min_surface_mean_confidence"] for row in result["surfaces"])


def test_direct_withheld_error_overrides_optimistic_mapper_report(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_error", screen_error=3.0)
    result = _compile(fixture)
    assert not result["physical_adapter_ready"]
    assert "all_declared_surfaces_ready" in result["blockers"]
    assert all(not row["checks"]["max_surface_withheld_p95_residual"] for row in result["surfaces"])


def test_cross_view_conflict_rejects_even_with_complete_maps(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_conflict", fusion_conflict=True)
    result = _compile(fixture)
    assert not result["physical_adapter_ready"]
    assert result["metrics"]["surface_conflict_pixels"] == 1
    assert "max_surface_conflict_fraction" in result["blockers"]


def test_surface_lookup_must_exactly_match_topology_contract(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_lookup")
    calibration = json.loads(fixture["calibration"].read_text(encoding="utf-8"))
    calibration["surface_lookup"] = calibration["surface_lookup"][:1]
    _write_json(fixture["calibration"], calibration)
    result = _compile(fixture)
    assert not result["physical_adapter_ready"]
    assert result["blockers"] == ["calibration_surface_set_differs_from_topology"]


def test_unaccounted_topology_pixels_stop_compilation(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_unaccounted", topology_unaccounted=1)
    result = _compile(fixture)
    assert not result["physical_adapter_ready"]
    assert result["blockers"] == ["topology_has_unaccounted_official_pixels"]


def test_outputs_are_byte_deterministic(tmp_path: Path) -> None:
    first = _fixture(tmp_path / "first")
    second = _fixture(tmp_path / "second")
    one = _compile(first)
    two = _compile(second)
    assert one["physical_adapter_ready"] and two["physical_adapter_ready"]
    assert _sha(first["output"] / "calibrated_physical_adapter.npz") == _sha(second["output"] / "calibrated_physical_adapter.npz")


def test_threshold_keys_are_exact_and_cannot_be_omitted(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_thresholds")
    thresholds = _thresholds()
    thresholds.pop("min_surface_coverage")
    result = compile_calibrated_adapter(
        fixture["topology"], fixture["calibration"], fixture["fusion"], fixture["mappers"], fixture["output"], thresholds=thresholds
    )
    assert result["blockers"] == ["exact_explicit_compiler_thresholds_required"]


def test_production_thresholds_cannot_be_lowered(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_no_threshold_bypass")
    result = compile_calibrated_adapter(
        fixture["topology"],
        fixture["calibration"],
        fixture["fusion"],
        fixture["mappers"],
        fixture["output"],
        thresholds=_thresholds(min_official_ownership_coverage=0.0),
    )
    assert not result["physical_adapter_ready"]
    assert result["blockers"] == ["compiler_threshold_overrides_forbidden"]


def test_global_mapped_coverage_is_an_explicit_gate(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path / "case_global_mapping")
    for mapper_path in fixture["mappers"].values():
        mapper = json.loads(mapper_path.read_text(encoding="utf-8"))
        npz_path = mapper_path.parent / mapper["output"]["path"]
        with np.load(npz_path, allow_pickle=False) as source:
            arrays = {name: source[name] for name in source.files}
        arrays["valid"][:, 2:5] = False
        np.savez_compressed(npz_path, **arrays)
        mapper["output"]["sha256"] = _sha(npz_path)
        _write_json(mapper_path, mapper)
    result = _compile(
        fixture,
        min_surface_coverage=0.0,
        min_official_mapped_coverage=1.0,
    )
    assert not result["physical_adapter_ready"]
    assert not result["readiness_checks"]["min_official_mapped_coverage"]
    assert "min_official_mapped_coverage" in result["blockers"]

