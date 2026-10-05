import numpy as np

from scripts.smart_tga_visual_prototype_train import prototype_features


def _unit(*values):
    vector = np.asarray(values, np.float64)
    return vector / np.linalg.norm(vector)


def test_visual_prototype_margin_prefers_nearest_semantic_bank():
    bank = np.asarray([
        _unit(1.0, 0.0, 0.0),
        _unit(0.9, 0.1, 0.0),
        _unit(0.0, 1.0, 0.0),
        _unit(0.0, 0.9, 0.1),
    ])
    number = np.asarray([True, True, False, False])
    sponsor = np.asarray([False, False, True, True])
    query = np.asarray([_unit(0.98, 0.02, 0.0), _unit(0.02, 0.98, 0.0)])
    features = prototype_features(bank, number, sponsor, query)
    assert features["number_minus_sponsor_top1"][0] > 0.8
    assert features["number_minus_sponsor_top1"][1] < -0.8


def test_visual_prototype_topk_is_bounded_when_bank_is_small():
    bank = np.asarray([_unit(1.0, 0.0), _unit(0.0, 1.0)])
    number = np.asarray([True, False])
    sponsor = np.asarray([False, True])
    features = prototype_features(bank, number, sponsor, bank)
    assert np.isfinite(features["number_minus_nonnumber_top3"]).all()
