from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "smart_tga_hypothesis_ranker",
    ROOT / "scripts" / "smart_tga_hypothesis_ranker.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _row(proposal_id: str, score: float, variant: str = "raw_palette_role") -> dict:
    return {
        "proposal_id": proposal_id,
        "panel_name": "door_number_lower_side",
        "expanded_panel_bbox": [10, 20, 40, 30],
        "intrinsic_score": score,
        "rank_score": score,
        "corroborative_d4_similarity": 0.7,
        "provenance": {
            "assembly_variant": variant,
            "lab_lightness_rank": 3,
            "post_assembly_vertical_open_kernel_height": 1,
            "vertical_open_kernel_height": 5,
            "retained_components": [{"area": 20}],
        },
    }


def test_exact_mask_id_is_shape_aware_and_deterministic():
    first = np.asarray([[1, 0], [0, 1]], dtype=np.uint8)
    second = first.reshape(1, 4)
    assert MODULE.exact_mask_id(first) == MODULE.exact_mask_id(first.copy())
    assert MODULE.exact_mask_id(first) != MODULE.exact_mask_id(second)


def test_duplicate_family_preserves_every_proposal_and_zero_authority():
    mask = np.zeros((20, 30), dtype=np.uint8)
    mask[3:18, 8:22] = 1
    rows = [
        _row("door_number_lower_side:L1:V1:R:a", 0.7),
        _row(
            "door_number_lower_side:L1:V1:S:a",
            0.8,
            "enclosed_multicolor_silhouette",
        ),
    ]
    bank = MODULE.ExactMaskBank({row["proposal_id"]: mask.copy() for row in rows})
    families = MODULE.collapse_panel_families(
        rows, bank, "door_number_lower_side"
    )
    assert len(families) == 1
    assert families[0]["member_proposal_ids"] == [row["proposal_id"] for row in rows]
    assert families[0]["proposal_count"] == 2
    assert families[0]["ownership_authority"] is False
    assert families[0]["output_authority"] is False


def test_proposal_features_include_shape_holes_and_provenance_without_semantics():
    mask = np.zeros((30, 30), dtype=np.uint8)
    cv2 = pytest.importorskip("cv2")
    cv2.rectangle(mask, (4, 3), (25, 27), 1, -1)
    cv2.rectangle(mask, (10, 9), (18, 21), 0, -1)
    features = MODULE.proposal_features(_row("x", 0.5), mask)
    assert features.shape == (len(MODULE.FEATURE_NAMES),)
    assert features[MODULE.FEATURE_NAMES.index("hole_count")] == 1
    assert np.isfinite(features).all()


def test_rank_record_keeps_baseline_slots_and_only_adds_learned_slots(monkeypatch):
    rows, masks = [], {}
    for index in range(8):
        proposal_id = f"door_number_lower_side:L{index}:V1:R:{index}"
        row = _row(proposal_id, 1.0 - index / 20.0)
        rows.append(row)
        mask = np.zeros((20, 30), dtype=np.uint8)
        mask[2 + index : 8 + index, 3:20] = 1
        masks[proposal_id] = mask

    class FakeModel:
        @staticmethod
        def predict_proba(matrix):
            scores = np.linspace(0.0, 1.0, len(matrix))
            return np.column_stack([1.0 - scores, scores])

    record = {
        "paint_label": "test/car_num_1",
        "source": "unused.png",
        "exact_hypotheses": "unused.npz",
        "hypotheses": rows,
    }
    monkeypatch.setattr(
        MODULE.ExactMaskBank,
        "load",
        classmethod(lambda cls, path: MODULE.ExactMaskBank(masks)),
    )
    ranked, _ = MODULE._rank_record(record, FakeModel(), 3, 2)
    families = ranked["panels"][0]["families"]
    baseline = [family for family in families if family["baseline_review_slot"]]
    additions = [family for family in families if family["learned_rescue_slot"]]
    assert len(baseline) == 3
    assert len(additions) <= 2
    assert all(family["combined_review_shortlist"] for family in baseline + additions)
    assert all(family["output_authority"] is False for family in families)


def test_ranker_is_deterministic_and_never_exposes_authority():
    first = MODULE.new_ranker()
    second = MODULE.new_ranker()
    features = np.asarray(
        [[0.0] * len(MODULE.FEATURE_NAMES), [1.0] * len(MODULE.FEATURE_NAMES)] * 4
    )
    labels = np.asarray([0, 1] * 4)
    first.fit(features, labels)
    second.fit(features, labels)
    assert np.array_equal(first.predict_proba(features), second.predict_proba(features))
    assert not hasattr(first, "output_authority")
