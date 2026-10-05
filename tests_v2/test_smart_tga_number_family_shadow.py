import numpy as np
import pytest
from sklearn.ensemble import ExtraTreesClassifier

from engine.spec_sculpt.number_family_shadow import PortableExtraTrees, pair_features as runtime_pair_features
from scripts.smart_tga_number_family_pair_bank import pair_features as offline_pair_features
from scripts.smart_tga_number_family_pair_probe import export_extra_trees_npz


def _rle(mask):
    flat = np.asarray(mask, np.uint8).ravel()
    counts = []
    value = 0
    run = 0
    for item in flat:
        if int(item) == value:
            run += 1
        else:
            counts.append(run)
            value = int(item)
            run = 1
    counts.append(run)
    return {"shape": list(mask.shape), "counts": counts}


def _record(mask, owners, stages):
    mask = np.asarray(mask, np.uint8)
    return {
        "local_mask": mask,
        "mask_rle": _rle(mask),
        "bbox_normalized": [0.2, 0.3, 0.1, 0.08],
        "shape_occupancy": list(np.arange(16, dtype=float) / 15.0),
        "area_fraction": 0.01,
        "fill_ratio": 0.44,
        "aspect_ratio": 1.7,
        "edge_density": 0.21,
        "texture_entropy": 0.31,
        "strong_gradient_fraction": 0.12,
        "perceptual_lightness": 0.7,
        "perceptual_chroma": 0.2,
        "perceptual_hue_degrees": 350.0,
        "ocr_alpha_coverage": 0.1,
        "ocr_digit_coverage": 0.2,
        "ocr_max_coverage": 0.2,
        "mean_rgb": [220.0, 180.0, 40.0],
        "palette_role": "light_chroma",
        "proposed_owners": owners,
        "source_stages": stages,
        "proposal_conflict": len(owners) > 1,
    }


def test_runtime_pair_features_match_offline_training_features():
    left = _record([[0, 1, 1], [0, 1, 0], [1, 1, 0]], ["numbers"], ["gpu_model_raw"])
    right = _record([[1, 1], [0, 1], [0, 1]], ["sponsors", "numbers"], ["template_raw"])
    offline = offline_pair_features(left, right)
    runtime = runtime_pair_features(left, right)
    for name, value in runtime.items():
        assert value == pytest.approx(offline[name], abs=1e-12), name


def test_portable_extra_trees_matches_sklearn_probabilities(tmp_path):
    rng = np.random.default_rng(4)
    x = rng.normal(size=(80, 4))
    y = x[:, 0] + x[:, 2] > 0.1
    model = ExtraTreesClassifier(n_estimators=12, min_samples_leaf=2, random_state=3).fit(x, y)
    path = tmp_path / "forest.npz"
    names = ["a", "b", "c", "d"]
    export_extra_trees_npz(
        model, names, decision_threshold=0.7, mutual_threshold=0.5,
        output=path, version="test",
    )
    portable = PortableExtraTrees(path)
    for row, expected in zip(x[:12], model.predict_proba(x[:12])[:, 1]):
        assert portable.score(dict(zip(names, row))) == pytest.approx(expected, abs=1e-12)
