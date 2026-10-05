import hashlib
from pathlib import Path

import numpy as np
import pytest

from _forge_uv_correspondence_fuser import aggregate_view, fuse_decoded_views


def _write_decoded(
    path: Path,
    samples: list[tuple[int, int, float, float, float, float, int]],
    shape: tuple[int, int] = (4, 6),
) -> Path:
    """Write samples as screen_y, screen_x, uv_x, uv_y, confidence, residual, surface."""

    uv_xy = np.full((*shape, 2), np.nan, dtype=np.float32)
    confidence = np.zeros(shape, dtype=np.float32)
    residual = np.full(shape, np.nan, dtype=np.float32)
    surface_id = np.zeros(shape, dtype=np.uint16)
    for screen_y, screen_x, uv_x, uv_y, weight, error, surface in samples:
        uv_xy[screen_y, screen_x] = (uv_x, uv_y)
        confidence[screen_y, screen_x] = weight
        residual[screen_y, screen_x] = error
        surface_id[screen_y, screen_x] = surface
    np.savez_compressed(
        path,
        uv_xy=uv_xy,
        confidence=confidence,
        quantization_residual=residual,
        surface_id=surface_id,
    )
    return path


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_screen_centroid_for_duplicate_uv_samples(tmp_path: Path):
    source = _write_decoded(
        tmp_path / "decoded.npz",
        [
            (1, 1, 2, 3, 0.8, 0.4, 7),
            (3, 5, 2, 3, 0.8, 0.4, 7),
        ],
    )
    arrays, metrics = aggregate_view(source, "side_a", (8, 8))
    assert arrays["sample_count"][3, 2] == 2
    assert arrays["screen_xy"][3, 2].tolist() == pytest.approx([3.0, 2.0])
    assert metrics["visible_uv_pixels"] == 1


def test_confidence_weighted_centroid_and_residual(tmp_path: Path):
    source = _write_decoded(
        tmp_path / "decoded.npz",
        [
            (0, 0, 1, 1, 0.25, 1.0, 4),
            (0, 4, 1, 1, 0.75, 3.0, 4),
        ],
    )
    arrays, _ = aggregate_view(source, "top", (5, 5))
    assert arrays["screen_xy"][1, 1].tolist() == pytest.approx([3.0, 0.0])
    assert arrays["confidence_mean"][1, 1] == pytest.approx(0.5)
    assert arrays["confidence_max"][1, 1] == pytest.approx(0.75)
    assert arrays["quantization_residual_mean"][1, 1] == pytest.approx(2.5)
    assert arrays["quantization_residual_max"][1, 1] == pytest.approx(3.0)


def test_conflicting_nonzero_surface_votes_abstain(tmp_path: Path):
    source = _write_decoded(
        tmp_path / "decoded.npz",
        [
            (0, 0, 3, 2, 0.9, 0.2, 12),
            (0, 1, 3, 2, 0.8, 0.3, 13),
        ],
    )
    arrays, metrics = aggregate_view(source, "front", (6, 6))
    assert arrays["surface_id"][2, 3] == 0
    assert arrays["surface_conflict"][2, 3]
    assert metrics["surface_conflict_uv_pixels"] == 1
    assert metrics["unknown_surface_uv_pixels"] == 1


@pytest.mark.parametrize("fault", ["outside", "missing_residual", "shape_mismatch"])
def test_invalid_v2_samples_are_rejected(tmp_path: Path, fault: str):
    source = _write_decoded(tmp_path / "decoded.npz", [(0, 0, 1, 1, 0.8, 0.2, 1)])
    with np.load(source) as data:
        payload = {name: data[name] for name in data.files}
    if fault == "outside":
        payload["uv_xy"] = payload["uv_xy"].copy()
        payload["uv_xy"][0, 0] = (99, 1)
    elif fault == "missing_residual":
        payload.pop("quantization_residual")
    else:
        payload["surface_id"] = payload["surface_id"][:-1]
    np.savez_compressed(source, **payload)
    with pytest.raises(ValueError):
        aggregate_view(source, "rear", (8, 8))


def test_multiview_visibility_and_fail_closed_readiness(tmp_path: Path):
    first = _write_decoded(
        tmp_path / "first.npz",
        [
            (0, 0, 1, 1, 0.9, 0.2, 2),
            (0, 1, 2, 1, 0.9, 0.2, 2),
        ],
    )
    second = _write_decoded(
        tmp_path / "second.npz",
        [
            (1, 0, 2, 1, 0.8, 0.3, 2),
            (1, 1, 3, 1, 0.8, 0.3, 2),
        ],
    )
    output = tmp_path / "fusion"
    result = fuse_decoded_views([("right", second), ("left", first)], (5, 4), output)
    cross = np.load(output / "cross_view_uv_summary.npz")
    assert result["roles"] == ["left", "right"]
    assert result["cross_view"]["unique_visible_uv_pixels"] == 3
    assert result["cross_view"]["multi_view_visible_uv_pixels"] == 1
    assert result["cross_view"]["visibility_count_histogram"] == {"1": 2, "2": 1}
    assert cross["visibility_count"][1, 2] == 2
    assert not result["readiness"]["correspondence_ready"]
    assert not result["readiness"]["delivery_ready"]
    assert "explicit_correspondence_thresholds_required" in result["readiness"]["blockers"]


def test_explicit_thresholds_can_qualify_correspondence_but_not_delivery(tmp_path: Path):
    source = _write_decoded(tmp_path / "decoded.npz", [(0, 0, 1, 1, 0.95, 0.1, 3)])
    thresholds = {
        "min_views": 1,
        "min_uv_visibility_fraction": 0.01,
        "min_mean_confidence": 0.9,
        "max_p95_quantization_residual": 0.2,
        "max_surface_conflict_fraction": 0.0,
    }
    result = fuse_decoded_views([("front", source)], (4, 4), tmp_path / "out", thresholds)
    assert result["readiness"]["correspondence_ready"]
    assert not result["readiness"]["delivery_ready"]


def test_outputs_are_byte_deterministic(tmp_path: Path):
    source = _write_decoded(
        tmp_path / "decoded.npz",
        [
            (0, 0, 1, 1, 0.8, 0.2, 5),
            (1, 2, 2, 2, 0.9, 0.3, 5),
        ],
    )
    first = tmp_path / "out_a"
    second = tmp_path / "out_b"
    fuse_decoded_views([("left", source)], (4, 4), first)
    fuse_decoded_views([("left", source)], (4, 4), second)
    for filename in (
        "view_left_uv_to_screen.npz",
        "cross_view_uv_summary.npz",
        "correspondence_fusion.json",
    ):
        assert _hash(first / filename) == _hash(second / filename)
