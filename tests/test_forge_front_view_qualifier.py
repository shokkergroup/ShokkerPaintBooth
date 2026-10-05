import numpy as np

from _forge_front_view_qualifier import qualify_front_mask


def test_balanced_direct_front_evidence_demands_front_ownership():
    mask = np.ones((10, 20), bool)
    proof = qualify_front_mask(mask, (0, 0), 10, 10, 10, 0.5, 100, 40, 0.05)
    assert proof["valid"] and proof["front_ownership_demand"]
    assert proof["bilateral_balance_error"] == 0.0


def test_one_sided_or_sparse_front_evidence_abstains():
    mask = np.zeros((10, 20), bool); mask[:, :4] = True
    proof = qualify_front_mask(mask, (0, 0), 10, 10, 10, 0.5, 20, 10, 0.10)
    assert not proof["valid"] and not proof["front_ownership_demand"]
