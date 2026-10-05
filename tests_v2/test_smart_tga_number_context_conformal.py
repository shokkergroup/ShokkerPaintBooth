import numpy as np

from engine.spec_sculpt.number_context_conformal import (
    PROPOSAL_FEATURE_NAMES,
    proposal_score_features,
    select_ranked_pixels,
)


def test_proposal_features_are_intrinsic_finite_and_complete():
    scores = np.asarray([[0.1, 0.9, 0.8], [0.0, 0.4, 0.7]], dtype=np.float32)
    raw = np.asarray([[1, 1, 1], [0, 1, 1]], dtype=bool)
    hypotheses = {
        "raw_instance_union": raw,
        "seed_palette": np.asarray([[0, 1, 1], [0, 0, 1]], dtype=bool),
        "border_contrast": np.asarray([[0, 1, 0], [0, 1, 1]], dtype=bool),
        "hybrid_evidence": np.asarray([[0, 1, 1], [0, 1, 1]], dtype=bool),
        "seeded_graphcut": np.asarray([[0, 1, 1], [0, 0, 1]], dtype=bool),
    }
    values = proposal_score_features(scores, hypotheses)
    assert tuple(values) == PROPOSAL_FEATURE_NAMES
    assert len(values) == 26
    assert np.isfinite(np.asarray(list(values.values()), dtype=np.float64)).all()
    assert not any(token in name for name in values for token in ("filename", "car", "bbox"))


def test_ranked_selection_is_exact_immutable_and_raw_bounded():
    scores = np.asarray([[0.1, 0.9, 0.8], [0.7, 0.6, 1.0]], dtype=np.float32)
    raw = np.asarray([[1, 1, 1], [1, 1, 0]], dtype=bool)
    selected = select_ranked_pixels(scores, raw, 0.4)
    assert selected.sum() == 2
    assert selected[0, 1]
    assert selected[0, 2]
    assert not selected[1, 2]
    assert selected.flags.writeable is False
