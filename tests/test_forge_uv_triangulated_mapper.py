import hashlib
import uuid
from pathlib import Path

import numpy as np
import pytest

from _forge_uv_triangulated_mapper import fit_triangulated_mapper


def _root(tmp_path: Path) -> Path:
    path = tmp_path / f"triangulated_{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    return path


def _write_view(
    path: Path,
    screen_xy: np.ndarray,
    *,
    visible: np.ndarray | None = None,
    sample_count: int = 1,
) -> Path:
    shape = screen_xy.shape[:2]
    if visible is None:
        visible = np.ones(shape, dtype=bool)
    counts = np.where(visible, sample_count, 0).astype(np.uint32)
    confidence = np.where(visible, 0.97, 0.0).astype(np.float32)
    residual = np.where(visible, 0.12, 0.0).astype(np.float32)
    surface = np.where(visible, 1, 0).astype(np.uint16)
    stored_screen = screen_xy.astype(np.float32).copy()
    stored_screen[~visible] = np.nan
    np.savez_compressed(
        path,
        screen_xy=stored_screen,
        sample_count=counts,
        confidence_mean=confidence,
        quantization_residual_max=residual,
        surface_id=surface,
        surface_conflict=np.zeros(shape, dtype=bool),
    )
    return path


def _thresholds(**overrides: float) -> dict[str, float]:
    values = {
        "min_confidence": 0.9,
        "max_residual": 0.5,
        "grid_stride": 4,
        "min_uv_triangle_area": 0.5,
        "min_screen_triangle_area": 0.1,
        "max_uv_edge": 9.0,
        "max_screen_edge": 30.0,
        "min_triangle_support": 3,
        "min_accepted_triangles": 20,
        "min_withheld_points": 100,
        "min_withheld_coverage": 0.82,
        "max_withheld_p95_residual": 0.8,
        "min_domain_coverage": 0.78,
        "min_delivery_mask_coverage": 0.82,
    }
    values.update(overrides)
    return values


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_known_nonlinear_warp_withholds_samples_and_preserves_occlusion(tmp_path: Path):
    root = _root(tmp_path)
    height, width = 48, 64
    yy, xx = np.mgrid[0:height, 0:width]
    screen = np.stack(
        (2.0 * xx + 0.01 * xx * yy, 1.5 * yy + 0.005 * xx * xx), axis=2
    )
    visible = np.ones((height, width), dtype=bool)
    visible[18:28, 26:38] = False
    view = _write_view(root / "view_left_uv_to_screen.npz", screen, visible=visible)
    domain = np.ones_like(visible)
    delivery = visible.copy()
    result = fit_triangulated_mapper(
        view,
        "left",
        root / "mapped",
        thresholds=_thresholds(),
        domain_mask=domain,
        delivery_mask=delivery,
    )
    assert result["geometric_mapping_ready"]
    assert result["evidence"]["withheld_p95_residual_pixels"] < 0.8
    assert result["evidence"]["withheld_coverage"] >= 0.82
    assert result["triangles"]["accepted"] >= 20
    assert len(result["thresholds_sha256"]) == 64
    assert result["domain_mask"]["source_kind"] == "inline_array"
    assert result["delivery_mask"]["source_kind"] == "inline_array"
    assert len(result["domain_mask"]["boolean_sha256"]) == 64
    assert not result["livery_ready"]
    assert not result["psd_ready"]
    assert not result["delivery_ready"]
    with np.load(root / "mapped" / "triangulated_uv_to_screen.npz") as payload:
        assert not payload["valid"][18:28, 26:38].any()
        assert payload["occluded_or_unknown"][18:28, 26:38].all()
        assert np.isnan(payload["screen_xy"][18:28, 26:38]).all()


def test_mapper_output_is_byte_deterministic(tmp_path: Path):
    root = _root(tmp_path)
    yy, xx = np.mgrid[0:32, 0:40]
    screen = np.stack((1.2 * xx + 0.004 * yy * yy, 1.1 * yy + 0.003 * xx * yy), axis=2)
    view = _write_view(root / "view_top_uv_to_screen.npz", screen)
    mask = np.ones((32, 40), dtype=bool)
    kwargs = dict(
        thresholds=_thresholds(
            min_accepted_triangles=10,
            min_withheld_points=50,
            min_domain_coverage=0.75,
            min_delivery_mask_coverage=0.75,
        ),
        domain_mask=mask,
        delivery_mask=mask,
    )
    output = root / "mapped"
    first = fit_triangulated_mapper(view, "top", output, **kwargs)
    first_npz = _sha(output / "triangulated_uv_to_screen.npz")
    first_json = _sha(output / "triangulated_mapper.json")
    second = fit_triangulated_mapper(view, "top", output, **kwargs)
    assert first["output"]["sha256"] == second["output"]["sha256"]
    assert _sha(output / "triangulated_uv_to_screen.npz") == first_npz
    assert _sha(output / "triangulated_mapper.json") == first_json


def test_folded_triangles_are_rejected_and_not_used(tmp_path: Path):
    root = _root(tmp_path)
    height, width = 32, 48
    yy, xx = np.mgrid[0:height, 0:width]
    folded_x = np.where(xx < width // 2, xx, width - xx)
    screen = np.stack((folded_x.astype(float), yy.astype(float)), axis=2)
    view = _write_view(root / "view_front_uv_to_screen.npz", screen)
    mask = np.ones((height, width), dtype=bool)
    result = fit_triangulated_mapper(
        view,
        "front",
        root / "mapped",
        thresholds=_thresholds(
            min_domain_coverage=0.9,
            min_delivery_mask_coverage=0.9,
            max_withheld_p95_residual=2.0,
        ),
        domain_mask=mask,
        delivery_mask=mask,
    )
    assert result["triangles"]["rejected"]["folded"] > 0
    assert not result["geometric_mapping_ready"]
    assert "min_domain_coverage" in result["blockers"]


def test_degenerate_screen_mapping_is_rejected(tmp_path: Path):
    root = _root(tmp_path)
    yy, xx = np.mgrid[0:24, 0:32]
    screen = np.stack((xx.astype(float), np.zeros_like(yy, dtype=float)), axis=2)
    view = _write_view(root / "view_rear_uv_to_screen.npz", screen)
    mask = np.ones((24, 32), dtype=bool)
    result = fit_triangulated_mapper(
        view,
        "rear",
        root / "mapped",
        thresholds=_thresholds(min_accepted_triangles=1, min_withheld_points=20),
        domain_mask=mask,
        delivery_mask=mask,
    )
    assert result["triangles"]["accepted"] == 0
    assert result["triangles"]["rejected"]["degenerate_screen"] > 0
    assert not result["geometric_mapping_ready"]


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"max_uv_edge": 2.0}, "overlarge_uv"),
        ({"min_triangle_support": 4}, "low_support"),
    ],
)
def test_overlarge_and_low_support_triangles_fail_closed(
    tmp_path: Path, override: dict[str, float], reason: str
):
    root = _root(tmp_path)
    yy, xx = np.mgrid[0:24, 0:32]
    screen = np.stack((xx.astype(float), yy.astype(float)), axis=2)
    view = _write_view(root / "view_right_uv_to_screen.npz", screen)
    mask = np.ones((24, 32), dtype=bool)
    result = fit_triangulated_mapper(
        view,
        "right",
        root / "mapped",
        thresholds=_thresholds(min_accepted_triangles=1, min_withheld_points=20, **override),
        domain_mask=mask,
        delivery_mask=mask,
    )
    assert result["triangles"]["accepted"] == 0
    assert result["triangles"]["rejected"][reason] > 0
    assert not result["geometric_mapping_ready"]


def test_explicit_thresholds_and_masks_are_mandatory(tmp_path: Path):
    root = _root(tmp_path)
    yy, xx = np.mgrid[0:16, 0:16]
    view = _write_view(root / "view_left_uv_to_screen.npz", np.stack((xx, yy), axis=2))
    result = fit_triangulated_mapper(
        view,
        "left",
        root / "no_thresholds",
        thresholds=None,
        domain_mask=np.ones((16, 16), dtype=bool),
        delivery_mask=np.ones((16, 16), dtype=bool),
    )
    assert not result["geometric_mapping_ready"]
    assert result["blockers"] == ["explicit_triangulation_thresholds_required"]
    assert not (root / "no_thresholds" / "triangulated_uv_to_screen.npz").exists()
    result = fit_triangulated_mapper(
        view,
        "left",
        root / "no_masks",
        thresholds=_thresholds(),
        domain_mask=None,
        delivery_mask=None,
    )
    assert result["blockers"] == ["explicit_domain_and_delivery_masks_required"]


def test_mask_and_threshold_provenance_changes_with_inputs(tmp_path: Path):
    root = _root(tmp_path)
    yy, xx = np.mgrid[0:24, 0:32]
    view = _write_view(
        root / "view_left_uv_to_screen.npz",
        np.stack((xx.astype(float), yy.astype(float)), axis=2),
    )
    domain = np.ones((24, 32), dtype=bool)
    delivery_a = domain.copy()
    delivery_b = domain.copy()
    delivery_b[0, 0] = False
    thresholds_a = _thresholds(min_accepted_triangles=1, min_withheld_points=20)
    thresholds_b = dict(thresholds_a)
    thresholds_b["max_withheld_p95_residual"] = 0.7

    first = fit_triangulated_mapper(
        view, "left", root / "first", thresholds=thresholds_a,
        domain_mask=domain, delivery_mask=delivery_a,
    )
    second = fit_triangulated_mapper(
        view, "left", root / "second", thresholds=thresholds_b,
        domain_mask=domain, delivery_mask=delivery_b,
    )

    assert first["thresholds_sha256"] != second["thresholds_sha256"]
    assert first["delivery_mask"]["boolean_sha256"] != second["delivery_mask"]["boolean_sha256"]
    assert first["domain_mask"]["boolean_sha256"] == second["domain_mask"]["boolean_sha256"]
