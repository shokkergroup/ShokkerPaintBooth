from __future__ import annotations

import numpy as np

from engine.spec_sculpt.decal_template_position import compute_template_position_evidence


PANEL_MAP = {
    "template":"test-template", "space":"100x100",
    "number_blocks":[{"name":"door", "bbox":[20,20,30,30]}],
    "sponsor_blocks":[{"name":"strip", "bbox":[60,20,30,20]}],
    "mandatory_decals":[{"name":"badge", "bbox":[5,70,20,20]}],
}


def test_template_position_evidence_is_scaled_exact_and_non_authoritative():
    mask = np.ones((20, 20), bool)
    evidence = compute_template_position_evidence((40, 40, 20, 20), mask, (200, 200), PANEL_MAP)
    assert evidence.best_number_fraction == 1.0
    assert evidence.best_sponsor_fraction == 0.0
    assert evidence.casts_votes is False
    assert evidence.ownership_authority is False


def test_template_position_evidence_distinguishes_sponsor_and_mandatory_blocks():
    mask = np.ones((20, 20), bool)
    sponsor = compute_template_position_evidence((125, 45, 20, 20), mask, (200, 200), PANEL_MAP)
    mandatory = compute_template_position_evidence((12, 145, 20, 20), mask, (200, 200), PANEL_MAP)
    assert sponsor.best_sponsor_fraction > 0.9
    assert sponsor.best_number_fraction == 0.0
    assert mandatory.best_mandatory_fraction > 0.9
