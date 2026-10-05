import numpy as np
from PIL import Image, ImageDraw, ImageFont

import _forge_embedded_split as splitter


def _synthetic_logo() -> np.ndarray:
    image = Image.new("RGBA", (340, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((5, 5, 334, 114), radius=18, fill="#0b6c3a", outline="white", width=5)
    draw.line((24, 92, 110, 24, 200, 94, 310, 20), fill="#e31b32", width=10)
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 52)
    draw.text((45, 30), "FORGE 11", font=font, fill="white", stroke_width=2, stroke_fill="#111111")
    return np.asarray(image, dtype=np.uint8)


def test_localize_finds_transformed_embedded_logo() -> None:
    exemplar = _synthetic_logo()
    target = np.zeros((420, 760, 4), dtype=np.uint8)
    target[:, :, :] = (24, 95, 58, 255)
    matrix = cv_matrix = np.float32([[1.0, 0.07, 195.0], [-0.03, 1.0, 145.0], [0.00008, -0.00005, 1.0]])
    warped = __import__("cv2").warpPerspective(exemplar, cv_matrix, (760, 420), flags=__import__("cv2").INTER_LINEAR, borderMode=__import__("cv2").BORDER_CONSTANT)
    alpha = warped[:, :, 3:4].astype(np.float32) / 255.0
    target[:, :, :3] = np.round(warped[:, :, :3] * alpha + target[:, :, :3] * (1.0 - alpha)).astype(np.uint8)
    result = splitter.localize(exemplar, target)
    assert result["accepted"], result
    assert result["inliers"] >= 7
    assert result["reprojection_rmse"] <= 6.0
    assert result["selected_pixels"] > 1000


def test_partition_recomposes_rgba_exactly() -> None:
    rng = np.random.default_rng(17)
    target = rng.integers(0, 256, size=(48, 64, 4), dtype=np.uint8)
    first = np.zeros((48, 64), dtype=bool)
    first[4:26, 7:28] = True
    second = np.zeros((48, 64), dtype=bool)
    second[20:44, 21:55] = True
    layers, remainder = splitter.partition_rgba(target, [first, second])
    union = remainder.copy()
    for layer in layers:
        union = np.bitwise_or(union, layer)
    assert np.array_equal(union, target)
    assert not np.logical_and(layers[0][:, :, 3] > 0, layers[1][:, :, 3] > 0).any()
    assert np.array_equal(splitter._normalized_rgba(splitter._recompose(layers, remainder)), splitter._normalized_rgba(target))


def test_spatial_duplicates_cluster_and_disagreements_abstain() -> None:
    mask = np.zeros((40, 60), dtype=bool)
    mask[10:30, 12:45] = True
    rows = [
        {"candidate": {"metadata": {"role": "decal", "surface": "left_strip", "side": "left", "mirror_policy": "preserve_readability", "psd_group": "40 SPONSORS & BRAND MARKS"}}, "localization": {"quality": 8.0, "_mask": mask}},
        {"candidate": {"metadata": {"role": "decal", "surface": "right_strip", "side": "right", "mirror_policy": "preserve_readability", "psd_group": "40 SPONSORS & BRAND MARKS"}}, "localization": {"quality": 7.0, "_mask": mask.copy()}},
    ]
    clusters = splitter._cluster_localizations(rows)
    assert len(clusters) == 1
    semantics = splitter.semantic_consensus(clusters[0])
    assert semantics["role"]["value"] == "decal"
    assert semantics["surface"]["value"] is None
    assert semantics["side"]["value"] is None


def test_localize_rejects_featureless_images() -> None:
    exemplar = np.zeros((100, 200, 4), dtype=np.uint8)
    exemplar[20:80, 20:180] = (255, 255, 255, 255)
    target = np.zeros((240, 420, 4), dtype=np.uint8)
    target[40:180, 30:390] = (20, 80, 30, 255)
    result = splitter.localize(exemplar, target)
    assert not result["accepted"]
    assert result["reason"] in {"insufficient_keypoints", "insufficient_ratio_matches"}
