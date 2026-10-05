from pathlib import Path

import numpy as np

from _forge_dlm_verified_residual_completion import complete_arrays


ROOT = Path(__file__).resolve().parents[1]


def test_only_single_envelope_rows_with_declared_split_are_added():
    labels = np.zeros((6, 8), dtype=np.int32); labels[1:3, 1:3] = 1; labels[1:3, 5:7] = 2
    official = labels > 0
    index = np.zeros_like(labels, dtype=np.uint8); index[0, 0] = 1
    envelope = np.zeros_like(official); envelope[1:3, 1:3] = True
    rows = [
        {"component_id": 1, "classification": "VERIFIED_ENVELOPE_RESIDUAL", "dominant_surface": "panel"},
        {"component_id": 2, "classification": "VERIFIED_ENVELOPE_RESIDUAL", "dominant_surface": "unsplit"},
    ]
    completed, audit = complete_arrays(labels, official, {"body": index}, {"panel": envelope, "unsplit": official}, rows, {"panel": {"registry": "body", "surface_index": 2}})
    assert int(np.count_nonzero(completed["body"] == 2)) == 4
    assert [row["status"] for row in audit] == ["COMPLETED", "ABSTAIN_NO_PHYSICAL_SPLIT"]


def test_reusable_module_has_no_livery_identity_branch():
    source = (ROOT / "_forge_dlm_verified_residual_completion.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "filename ==", "sponsor =="):
        assert forbidden not in source
