from __future__ import annotations

import numpy as np

from scripts.smart_tga_clip_anchor_extension_train import (
    FEATURE_NAMES,
    _constrain_one_best,
    _mask_intrinsics,
    _operational_pairs,
    _pixel_sha256,
    _safe_threshold,
)
from scripts.smart_tga_clipseg_zero_shot_probe import (
    PROMPTS,
    _safe_threshold as _zero_shot_safe_threshold,
    _score_modes,
)


def test_source_content_hash_uses_decoded_pixels_only() -> None:
    pixels = np.arange(7 * 9 * 3, dtype=np.uint8).reshape(7, 9, 3)

    assert _pixel_sha256(pixels) == _pixel_sha256(pixels.copy())
    changed = pixels.copy()
    changed[0, 0, 0] ^= 1
    assert _pixel_sha256(pixels) != _pixel_sha256(changed)


def test_mask_intrinsics_are_translation_and_quarter_turn_neutral() -> None:
    support = np.zeros((24, 32), dtype=bool)
    support[4:20, 8:12] = True
    support[16:20, 8:26] = True
    rgb = np.zeros((24, 32, 3), dtype=np.uint8)
    rgb[support] = (210, 40, 70)

    base = _mask_intrinsics(rgb, support, 2)
    rotated = _mask_intrinsics(np.rot90(rgb), np.rot90(support), 2)

    assert base.shape == rotated.shape == (20,)
    assert np.allclose(base[:5], rotated[:5], atol=1e-5)
    # Hu moments are theoretically rotation invariant; tolerate OpenCV rounding.
    assert np.allclose(base[7:14], rotated[7:14], atol=2e-3)
    assert np.allclose(base[14:], rotated[14:], atol=2e-3)


def test_operational_negative_pairs_are_number_anchor_first() -> None:
    data = {
        "groups": np.asarray(["paint", "paint", "paint", "paint"]),
        "blocks": np.asarray(["upper", "lower", "deck", "lower"]),
        "semantic": np.asarray([0, 1, 1, 0], dtype=np.int64),
    }

    positive, negative = _operational_pairs(np.arange(4), data)

    assert positive.tolist() == [[1, 2]]
    assert len(negative) == 3
    assert np.all(data["semantic"][negative[:, 0]] == 1)
    assert np.all(data["semantic"][negative[:, 1]] == 0)


def test_one_best_and_safe_threshold_preserve_abstention_contract() -> None:
    score = np.asarray([0.98, 0.97, 0.93, 0.90, 0.20])
    truth = np.asarray([True, False, True, False, False])
    keys = np.asarray(["a", "a", "b", "c", "c"])
    control = np.asarray([False, False, False, True, True])

    constrained = _constrain_one_best(score, score >= 0.89, keys)
    threshold = _safe_threshold(truth, score, keys, control, precision_floor=0.90)
    accepted = _constrain_one_best(score, score >= threshold, keys)

    assert constrained.tolist() == [True, False, True, True, False]
    assert np.any(accepted & truth)
    assert not np.any(accepted & ~truth & control)
    assert truth[accepted].mean() >= 0.90


def test_anchor_extension_features_exclude_identity_and_absolute_position() -> None:
    forbidden = ("filename", "paint_id", "car", "source_hash", "bbox", "absolute")

    assert not any(token in name for name in FEATURE_NAMES for token in forbidden)
    assert FEATURE_NAMES[0] == "clip_silhouette_orbit_similarity"


def test_zero_shot_prompt_and_score_contract_is_owner_neutral() -> None:
    category = {
        "complete_number": np.asarray([0.8, 0.4]),
        "number_fragment": np.asarray([0.5, 0.7]),
        "sponsor": np.asarray([0.2, 0.6]),
        "paint": np.asarray([0.3, 0.1]),
    }

    modes = _score_modes(category)

    assert set(modes) == {
        "complete_raw", "complete_minus_fragment",
        "complete_minus_nonnumber", "complete_minus_all",
    }
    assert np.allclose(modes["complete_minus_fragment"], [0.3, -0.3])
    forbidden = ("car_num_", ".tga", "bbox", "dirtlatemodel 350", "dirtlatemodel 358")
    assert not any(token in prompt for values in PROMPTS.values() for prompt in values for token in forbidden)


def test_zero_shot_threshold_refuses_uncertain_and_control_errors() -> None:
    truth = np.asarray([True, True, False, False, False])
    explicit = np.asarray([True, True, True, False, True])
    score = np.asarray([0.99, 0.95, 0.94, 0.93, 0.10])
    stress = np.asarray([False, False, False, False, True])

    threshold = _zero_shot_safe_threshold(truth, explicit, score, stress)
    accepted = score >= threshold

    assert accepted.tolist() == [True, True, False, False, False]
    assert not np.any(accepted & ~explicit)
    assert not np.any(accepted & stress)
