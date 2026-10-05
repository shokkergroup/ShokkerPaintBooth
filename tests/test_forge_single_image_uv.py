import numpy as np

from _forge_single_image_uv import confidence_fuse, homologous_profile_role


def test_confidence_fuse_uses_one_winner_per_pixel():
    first = {
        "rgb": np.array([[[255, 0, 0], [255, 0, 0]]], dtype=np.uint8),
        "confidence": np.array([[0.8, 0.2]], dtype=np.float32),
        "observed": np.array([[True, True]]),
    }
    second = {
        "rgb": np.array([[[0, 0, 255], [0, 0, 255]]], dtype=np.uint8),
        "confidence": np.array([[0.3, 0.9]], dtype=np.float32),
        "observed": np.array([[True, True]]),
    }
    rgb, confidence = confidence_fuse([first, second])
    assert rgb.tolist() == [[[255, 0, 0], [0, 0, 255]]]
    assert np.allclose(confidence, [[0.8, 0.9]])


def test_confidence_fuse_rejects_shape_mismatch():
    splat = {"rgb": np.zeros((1, 1, 3), dtype=np.uint8), "confidence": np.zeros((1, 1)), "observed": np.zeros((1, 1), dtype=bool)}
    bad = {"rgb": np.zeros((2, 1, 3), dtype=np.uint8), "confidence": np.zeros((2, 1)), "observed": np.zeros((2, 1), dtype=bool)}
    try:
        confidence_fuse([splat, bad])
    except ValueError as error:
        assert "shape mismatch" in str(error)
    else:
        raise AssertionError("shape mismatch should fail")


def test_homologous_profile_role_is_explicit_and_never_front_rear():
    assert homologous_profile_role("left_profile") == "right_profile"
    assert homologous_profile_role("right_profile") == "left_profile"
    assert homologous_profile_role("front_view") is None
