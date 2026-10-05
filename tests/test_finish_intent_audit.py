"""Protect fairness: plain materials, missing evidence, and two-sided targets."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

spec = importlib.util.spec_from_file_location('intent_audit', Path(__file__).parents[1] / 'scripts/spb_finish_intent_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_missing_evidence_cannot_become_a_perfect_score():
    result = audit.evidence_interval({'name': 100}, {'name': 25, 'material': 75})
    assert result == {'lower': 25.0, 'upper': 100.0, 'coverage': .25, 'score': None}
    assert audit.evidence_interval({}, {'name': 25, 'material': 75})['lower'] == 0


def test_plain_and_dynamic_can_both_meet_their_contract():
    assert audit.band_fit(0, -1, 0, 2, 8) == 100
    assert audit.band_fit(80, 20, 60, 100, 140) == 100
    assert audit.band_fit(80, -1, 0, 2, 8) == 0
    assert audit.band_fit(0, 20, 60, 100, 140) == 0
    assert audit.band_fit(None, 0, 1, 2, 3) is None
    with pytest.raises(ValueError):
        audit.band_fit(1, 0, 0, 2, 3)


def test_quiet_chrome_has_high_median_and_zero_span_without_failure():
    result = audit.measure(Image.new('RGB', (32,32), (190,190,190)), Image.new('RGB',(32,32),(255,2,16)))
    assert result['channels']['M']['median'] == 255
    assert result['channels']['M']['robust_span'] == 0
    assert result['spec_states_16byte']['effective_bins'] == 1
    assert result['hue_families_1pct'] == 0


def test_one_hot_pixel_does_not_manufacture_broad_spec_response():
    spec = np.zeros((128,128,3), dtype=np.uint8)
    spec[0,0] = 255
    result = audit.measure(Image.new('RGB',(128,128)), Image.fromarray(spec))
    assert all(v['robust_span'] == 0 for v in result['channels'].values())
    assert result['spec_states_16byte']['bins_at_least_1pct'] == 1


def test_complete_evidence_has_no_unknown_interval():
    result = audit.evidence_interval({'a':80,'b':100}, {'a':3,'b':1})
    assert result == {'lower':85,'upper':85,'coverage':1,'score':85}
