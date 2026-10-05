import numpy as np

from engine.spec_sculpt.tiled_palette_semantics import (
    feature_matrix,
    forest_number_score,
    linear_semantic_scores,
    tiled_candidate_features,
)


def _candidate(mask, bbox=(12, 20, 12, 18), proposal_id="candidate"):
    mask = np.asarray(mask, dtype=bool)
    mask.setflags(write=False)
    return {
        "proposal_id": proposal_id,
        "proposal_bbox": list(bbox),
        "raw_support": mask,
        "owner_neutral": True,
        "ownership_authority": False,
        "provenance": {
            "palette_role": "chromatic_ink",
            "component_count": 2,
            "tile_origin_count": 3,
            "peer_d4_similarity": 0.91,
            "peer_count_at_0_82": 4,
            "template_number_fraction": 0.8,
            "template_sponsor_fraction": 0.1,
            "assembly_support": 0.5,
        },
    }


def test_intrinsic_features_are_d4_invariant_and_do_not_expose_identity():
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    image[20:38, 12:24] = (210, 55, 20)
    mask = np.zeros((18, 12), dtype=bool)
    mask[2:16, 2:5] = True
    mask[12:16, 2:10] = True
    first = tiled_candidate_features(image, _candidate(mask))

    rotated = np.rot90(mask)
    rotated_image = np.zeros_like(image)
    rotated_image[20:32, 12:30] = (210, 55, 20)
    second = tiled_candidate_features(
        rotated_image,
        _candidate(rotated, bbox=(12, 20, 18, 12), proposal_id="different"),
    )
    assert np.allclose(
        [first[f"shape_d4_{index:02d}"] for index in range(16)],
        [second[f"shape_d4_{index:02d}"] for index in range(16)],
        atol=1e-8,
    )
    assert not any("filename" in name or "paint" in name or "bbox_x" in name for name in first)


def test_feature_matrix_is_immutable_and_linear_scorer_abstains_without_authority():
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    image[20:38, 12:24] = (80, 220, 40)
    mask = np.ones((18, 12), dtype=bool)
    candidate = _candidate(mask)
    matrix, names, rows = feature_matrix(image, (candidate,))
    assert matrix.shape == (1, len(names))
    assert not matrix.flags.writeable
    assert len(rows) == 1
    model = {
        "feature_names": list(names),
        "mean": [0.0] * len(names),
        "scale": [1.0] * len(names),
        "classes": ["Number", "Sponsor"],
        "coefficients": [[0.0] * len(names), [0.0] * len(names)],
        "intercept": [0.0, 0.0],
        "abstain_probability": 0.6,
        "abstain_margin": 0.1,
    }
    scored = linear_semantic_scores(rows[0], model)
    assert scored["abstained"]
    assert scored["predicted_semantic"] == "uncertain"
    assert not scored["ownership_authority"]

    forest = {
        "feature_names": list(names),
        "trees": [{
            "feature": [0, -2, -2],
            "threshold": [float(matrix[0, 0]) - 1.0, -2.0, -2.0],
            "left": [1, -1, -1],
            "right": [2, -1, -1],
            "number_probability": [0.5, 0.1, 0.9],
        }],
    }
    assert forest_number_score(rows[0], forest) == 0.9
