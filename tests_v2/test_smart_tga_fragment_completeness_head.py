import numpy as np

from scripts.smart_tga_fragment_completeness_head import _veto_only_threshold
from scripts.smart_tga_merge_boundary_states import STATE_TO_TARGET


def test_direct_boundary_states_have_explicit_non_authoritative_targets():
    assert STATE_TO_TARGET == {
        "complete_number_copy": ("Number", True),
        "number_fragment": ("Number", False),
        "sponsor_glyph": ("Sponsor", False),
        "paint_or_template": ("Paint/livery", False),
        "ambiguous_crop": ("uncertain", None),
    }


def test_certainty_policy_can_only_veto_baseline_candidates():
    data = {
        "known": np.asarray([True, True, False, True]),
        "uncertain": np.asarray([False, False, True, False]),
        "family": np.asarray([True, True, False, False]),
        "complete": np.asarray([True, False, False, False]),
        "control": np.asarray([False, False, False, True]),
    }
    baseline = np.asarray([True, True, True, False])
    certainty = np.asarray([0.9, 0.8, 0.2, 0.99])
    threshold, summary = _veto_only_threshold(data, baseline, certainty)
    accepted = baseline & (certainty >= threshold)
    assert accepted.tolist() == [True, True, False, False]
    assert not np.any(accepted & ~baseline)
    assert summary["inner_true"] == 2
    assert summary["inner_precision"] == 1.0


def test_veto_policy_does_not_buy_entry_for_high_certainty_non_baseline_row():
    data = {
        "known": np.asarray([True, True]),
        "uncertain": np.asarray([False, False]),
        "family": np.asarray([True, False]),
        "complete": np.asarray([True, False]),
        "control": np.asarray([False, False]),
    }
    baseline = np.asarray([True, False])
    certainty = np.asarray([0.7, 0.999])
    threshold, _ = _veto_only_threshold(data, baseline, certainty)
    accepted = baseline & (certainty >= threshold)
    assert accepted.tolist() == [True, False]
