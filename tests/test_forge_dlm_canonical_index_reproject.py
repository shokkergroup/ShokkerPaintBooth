import numpy as np

from _forge_dlm_canonical_index_reproject import reproject_index


def test_reprojection_extends_source_and_preserves_existing_owner():
    existing = np.zeros((5, 5), dtype=np.uint8); existing[2, 2] = 1; existing[1, 1] = 2; existing[0, 0] = 2
    target = np.zeros((5, 5), dtype=np.uint8); target[1:4, 1:4] = 1; target[0, 0] = 2
    completed, rows = reproject_index(existing, target, [np.eye(3), np.eye(3)])
    assert completed[1, 1] == 2
    assert rows[0]["blocked_by_existing_owner_pixels"] == 1
    assert rows[0]["added_canonical_pixels"] == 7
    assert rows[1]["roundtrip_target_recall"] == 1.0
