from pathlib import Path

import numpy as np

from _forge_dlm_conflict_voronoi_resolver import resolve_arrays


ROOT = Path(__file__).resolve().parents[1]


def test_unique_nearest_seed_resolves_and_tie_band_abstains():
    shape = (9, 13)
    conflict = np.zeros(shape, dtype=bool); conflict[3:6, 2:11] = True
    left = np.zeros(shape, dtype=bool); left[3:6, 0:2] = True
    right = np.zeros(shape, dtype=bool); right[3:6, 11:13] = True
    envelope = np.ones(shape, dtype=bool)
    result = resolve_arrays(conflict, {"left": left, "right": right}, {"left": envelope, "right": envelope}, 20, 1.5)
    assert np.count_nonzero(result["assignments"]["left"]) > 0
    assert np.count_nonzero(result["assignments"]["right"]) > 0
    assert np.count_nonzero(result["abstained"]) > 0
    assert not np.any(result["assignments"]["left"] & result["assignments"]["right"])


def test_surface_contract_is_livery_neutral():
    source = (ROOT / "_forge_dlm_conflict_voronoi_resolver.py").read_text(encoding="utf-8").lower()
    for forbidden in ("waffle", "domino", "crystal", "sex wax", "sponsor ==", "filename =="):
        assert forbidden not in source
