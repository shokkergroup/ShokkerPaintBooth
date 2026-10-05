from pathlib import Path

import numpy as np

from _forge_dlm_topology_evidence_classifier import classify_arrays, envelope_masks


ROOT = Path(__file__).resolve().parents[1]


def test_residuals_split_between_single_envelope_conflict_and_outside():
    labels = np.zeros((8, 12), dtype=np.int32)
    labels[1:3, 1:3] = 1
    labels[4:6, 5:7] = 2
    labels[1:3, 9:11] = 3
    missing = labels > 0
    variance = np.full(labels.shape, 70, dtype=np.uint8)
    a = np.zeros_like(missing); a[0:4, 0:4] = True; a[4:6, 5:6] = True
    b = np.zeros_like(missing); b[4:6, 6:7] = True
    result = classify_arrays(labels, missing, variance, {"a": a, "b": b}, 0.8)
    classes = {row["component_id"]: row["classification"] for row in result["components"]}
    assert classes == {1: "VERIFIED_ENVELOPE_RESIDUAL", 2: "MULTI_ENVELOPE_CONFLICT", 3: "OUTSIDE_VERIFIED_ENVELOPES"}


def test_authority_envelopes_scale_without_scheme_identity():
    authority = {"coordinate_space": [4, 4], "surfaces": {"panel": {"envelope_bbox": [1, 1, 3, 3]}}}
    masks = envelope_masks(authority, (8, 8))
    assert int(np.count_nonzero(masks["panel"])) == 16
    source = (ROOT / "_forge_dlm_topology_evidence_classifier.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "filename ==", "sponsor =="):
        assert forbidden not in source
