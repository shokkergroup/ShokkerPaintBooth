from __future__ import annotations

import numpy as np

from _forge_surface_parameter_optimizer import coverage_guarded_score, make_local_validator


def test_local_validator_bounds_each_surface_around_its_own_calibration() -> None:
    initial = np.array([1.0, 0.6, 0.2, 0.35])
    valid = make_local_validator(initial, np.array([0.1, 0.15, 0.05, 0.08]))
    assert valid(np.array([1.05, 0.7, 0.18, 0.4]))
    assert not valid(np.array([1.2, 0.7, 0.18, 0.4]))
    assert not valid(np.array([1.0, 0.01, 0.2, 0.35]))


def test_coverage_guard_prevents_score_gain_by_hiding_pixels() -> None:
    assert coverage_guarded_score(94.0, 980, 1000, 0.97) == 94.0
    assert coverage_guarded_score(99.0, 800, 1000, 0.97) < 0.0
