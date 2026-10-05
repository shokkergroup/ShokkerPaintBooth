from __future__ import annotations

import numpy as np

from engine.spec_sculpt.number_context_members import (
    assemble_member_mask,
    grow_member_mask,
    member_feature_mapping,
)


def _instance(instance_id: str, bbox: list[int], color: tuple[int, int, int]) -> dict:
    width, height = bbox[2], bbox[3]
    return {
        "instance_id": instance_id,
        "bbox": bbox,
        "local_mask": np.ones((height, width), bool),
        "mean_rgb": color,
        "std_rgb": (2, 3, 4),
        "shape_occupancy": (1.0,) * 16,
        "area_fraction": 0.01,
        "fill_ratio": 1.0,
        "edge_density": 0.2,
        "strong_gradient_fraction": 0.1,
        "texture_entropy": 0.3,
        "perceptual_lightness": 60.0,
        "perceptual_chroma": 25.0,
        "ocr_alpha_coverage": 0.0,
        "ocr_digit_coverage": 0.4,
        "ocr_max_coverage": 0.4,
    }


def test_member_features_and_masks_are_intrinsic_and_immutable() -> None:
    proposal = {"bbox": [2, 2, 8, 6]}
    seed = _instance("seed", [3, 3, 3, 3], (230, 210, 30))
    neighbour = _instance("neighbour", [7, 3, 2, 3], (228, 208, 32))
    mapping = member_feature_mapping(neighbour, proposal, seed)

    assert len(mapping) == 51
    assert all(np.isfinite(list(mapping.values())))
    assert not any("filename" in name or "owner" in name for name in mapping)

    core, selected = assemble_member_mask(
        proposal["bbox"], [seed, neighbour], [0.91, 0.49], threshold=0.8,
    )
    assert selected == ["seed"]
    assert int(np.count_nonzero(core)) == 9
    assert not core.flags.writeable

    rgb = np.zeros((12, 12, 3), np.uint8)
    rgb[3:6, 3:9] = (230, 210, 30)
    grown = grow_member_mask(rgb, proposal["bbox"], core, color_distance=8, support_radius=3)
    assert int(np.count_nonzero(grown)) >= int(np.count_nonzero(core))
    assert not grown.flags.writeable

