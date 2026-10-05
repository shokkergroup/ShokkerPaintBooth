from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from _forge_historical_pair_correspondence import (
    ImageEvidenceError,
    ManifestValidationError,
    PairEvidence,
    choose_withheld_cohort,
    fit_local_clusters,
    load_accepted_pairs,
    prepare_image,
    suppress_duplicate_matches,
)


SCHEMA = "shokk-forge.dlm-manual-cohort-pair-review/v1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_image(path: Path, size: tuple[int, int], seed: int, *, alpha: int | None = None) -> None:
    width, height = size
    rng = np.random.default_rng(seed)
    image = rng.integers(0, 255, (height, width, 3), dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (width - 20, height - 20), (10, 220, 90), 4)
    if alpha is not None:
        image = np.dstack([image, np.full((height, width), alpha, dtype=np.uint8)])
    assert cv2.imwrite(str(path), image)


def _build_manifest(tmp_path: Path) -> tuple[Path, Path, Path, dict]:
    paint_path = tmp_path / "flat.png"
    spec_path = tmp_path / "flat_spec.png"
    render_path = tmp_path / "render.png"
    _write_image(paint_path, (512, 512), 1)
    _write_image(spec_path, (512, 512), 2)
    _write_image(render_path, (640, 360), 3)
    selected = {
        "path": str(paint_path.resolve()),
        "relative_path": paint_path.name,
        "review_status": "SELECTED_PAINT",
        "role": "paint",
        "sha256": _sha(paint_path),
        "size": [512, 512],
    }
    spec = {
        "path": str(spec_path.resolve()),
        "relative_path": spec_path.name,
        "review_status": "REJECTED_SPEC",
        "role": "spec",
        "sha256": _sha(spec_path),
        "size": [512, 512],
    }
    render = {
        "path": str(render_path.resolve()),
        "relative_path": render_path.name,
        "sha256": _sha(render_path),
        "size": [640, 360],
        "decision": "ACCEPT_PAIR_EVIDENCE",
        "confidence": 0.9,
        "calibration_authorized": False,
        "delivery_authorized": False,
        "dense_uv_correspondence_proved": False,
        "selected_paint_path": selected["path"],
        "selected_paint_relative_path": selected["relative_path"],
        "selected_paint_sha256": selected["sha256"],
        "spec_map_alternatives_excluded": [
            {"path": spec["path"], "sha256": spec["sha256"]}
        ],
    }
    review = {
        "$schema": SCHEMA,
        "cohorts": {
            "opaque_a": {
                "decision": "ACCEPT_COHORT_PAIR",
                "selected_paint": selected,
                "alternatives": [selected, spec],
                "renders": [render],
            },
            "opaque_abstain": {
                "decision": "ABSTAIN_VARIANT_AMBIGUITY",
                "alternatives": [selected],
                "renders": [],
            },
        },
    }
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps(review), encoding="utf-8")
    summary = {
        "$schema": SCHEMA,
        "manual_review_json": review_path.name,
        "manual_review_json_sha256": _sha(review_path),
    }
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    return summary_path, review_path, render_path, review


def _rewrite_review(summary_path: Path, review_path: Path, review: dict) -> None:
    review_path.write_text(json.dumps(review), encoding="utf-8")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["manual_review_json_sha256"] = _sha(review_path)
    summary_path.write_text(json.dumps(summary), encoding="utf-8")


def test_loads_only_hash_bound_accepted_pairs(tmp_path: Path) -> None:
    summary_path, _, _, _ = _build_manifest(tmp_path)
    pairs = load_accepted_pairs(summary_path)
    assert len(pairs) == 1
    assert pairs[0].cohort_id == "opaque_a"
    assert pairs[0].paint_path.name == "flat.png"


def test_tampered_image_hash_fails_closed(tmp_path: Path) -> None:
    summary_path, _, render_path, _ = _build_manifest(tmp_path)
    render_path.write_bytes(render_path.read_bytes() + b"tamper")
    with pytest.raises(ManifestValidationError, match="hash mismatch"):
        load_accepted_pairs(summary_path)


def test_selected_spec_fails_closed(tmp_path: Path) -> None:
    summary_path, review_path, _, review = _build_manifest(tmp_path)
    cohort = review["cohorts"]["opaque_a"]
    spec = cohort["alternatives"][1]
    cohort["selected_paint"] = {
        **spec,
        "review_status": "SELECTED_PAINT",
    }
    _rewrite_review(summary_path, review_path, review)
    with pytest.raises(ManifestValidationError, match="not paint"):
        load_accepted_pairs(summary_path)


def test_nonaccepted_render_in_accepted_cohort_fails_closed(tmp_path: Path) -> None:
    summary_path, review_path, _, review = _build_manifest(tmp_path)
    review["cohorts"]["opaque_a"]["renders"][0]["decision"] = "ABSTAIN"
    _rewrite_review(summary_path, review_path, review)
    with pytest.raises(ManifestValidationError, match="not individually accepted"):
        load_accepted_pairs(summary_path)


def _pair(cohort: str, paint_hash: str, render_hash: str) -> PairEvidence:
    return PairEvidence(
        cohort_id=cohort,
        paint_path=Path("flat"),
        paint_sha256=paint_hash,
        paint_size=(2048, 2048),
        render_path=Path("render"),
        render_sha256=render_hash,
        render_size=(1000, 500),
        confidence=1.0,
    )


def test_withheld_cohort_is_deterministic_across_input_order() -> None:
    pairs = [
        _pair("opaque_a", "a" * 64, "1" * 64),
        _pair("opaque_b", "b" * 64, "2" * 64),
        _pair("opaque_b", "b" * 64, "3" * 64),
        _pair("opaque_c", "c" * 64, "4" * 64),
    ]
    expected = choose_withheld_cohort(pairs)
    assert choose_withheld_cohort(list(reversed(pairs))) == expected
    assert choose_withheld_cohort([pairs[2], pairs[0], pairs[3], pairs[1]]) == expected


def test_duplicate_suppression_is_one_to_one_and_coordinate_unique() -> None:
    base = {
        "render_xy": [10.0, 10.0],
        "flat_xy": [20.0, 20.0],
        "scale_ratio": 1.0,
        "angle_delta": 0.0,
    }
    matches = [
        {**base, "render_index": 1, "flat_index": 2, "distance": 4.0},
        {**base, "render_index": 1, "flat_index": 3, "distance": 5.0},
        {**base, "render_index": 4, "flat_index": 2, "distance": 6.0},
        {
            **base,
            "render_index": 5,
            "flat_index": 6,
            "render_xy": [50.0, 50.0],
            "flat_xy": [60.0, 60.0],
            "distance": 7.0,
        },
    ]
    kept = suppress_duplicate_matches(matches)
    assert [(item["render_index"], item["flat_index"]) for item in kept] == [(1, 2), (5, 6)]


def _synthetic_match(index: int, flat_xy: tuple[float, float], render_xy: tuple[float, float]) -> dict:
    return {
        "render_index": index,
        "flat_index": index,
        "render_xy": list(render_xy),
        "flat_xy": list(flat_xy),
        "distance": 1.0 + index * 0.01,
        "scale_ratio": 1.0,
        "angle_delta": 0.0,
    }


def test_local_ransac_keeps_disconnected_models_local() -> None:
    matches: list[dict] = []
    for index, (x, y) in enumerate([(20, 20), (40, 25), (25, 50), (55, 55), (65, 30), (35, 70)]):
        matches.append(_synthetic_match(index, (x, y), (x + 100, y + 40)))
    offset = len(matches)
    for local_index, (x, y) in enumerate([(330, 330), (360, 335), (340, 370), (390, 390), (370, 350), (350, 395)]):
        matches.append(
            _synthetic_match(offset + local_index, (x, y), (0.8 * x - 20, 1.1 * y + 60))
        )
    labeled, models = fit_local_clusters(
        matches,
        flat_shape=(400, 400),
        grid=(4, 4),
        minimum_inliers=5,
    )
    assert len(models) == 2
    assert sum(item["accepted"] for item in labeled) == 12
    assert len({tuple(model["cell"]) for model in models}) == 2
    assert all(model["model_scope"] == "ONE_FIXED_FLAT_UV_GRID_CELL_ONLY" for model in models)


def test_empty_alpha_image_is_rejected(tmp_path: Path) -> None:
    image_path = tmp_path / "empty.png"
    _write_image(image_path, (300, 300), 8, alpha=0)
    with pytest.raises(ImageEvidenceError, match="alpha channel"):
        prepare_image(image_path, expected_size=(300, 300))


def test_pillow_fallback_decodes_production_style_tga(tmp_path: Path) -> None:
    image_path = tmp_path / "flat.tga"
    rgb = np.zeros((320, 320, 3), dtype=np.uint8)
    rgb[:, :, 0] = np.arange(320, dtype=np.uint8)[None, :]
    rgb[:, :, 1] = np.arange(320, dtype=np.uint8)[:, None]
    Image.fromarray(rgb, mode="RGB").save(image_path, format="TGA")
    prepared = prepare_image(image_path, expected_size=(320, 320))
    assert prepared.original_size == (320, 320)
    assert prepared.intensity_std > 3.0
