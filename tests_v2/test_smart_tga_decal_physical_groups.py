import numpy as np

from engine.spec_sculpt.decal_instances import (
    DecalCandidateInstance,
    DecalInstanceFeatures,
    OwnerHypothesis,
)
from engine.spec_sculpt.decal_physical_groups import (
    derive_physical_decal_groups,
    extract_physical_decal_group_features,
    physical_decal_group_telemetry,
)


def _instance(name, bbox, owner="sponsors"):
    width, height = bbox[2:]
    mask = np.ones((height, width), bool)
    return DecalCandidateInstance(
        instance_id=name,
        bbox=bbox,
        area=int(mask.sum()),
        local_mask=mask,
        candidate_ids=(name,),
        source_stages=("test",),
        sources=("test",),
        owner_hypotheses=(OwnerHypothesis(owner, (name,), 1, 1.0, int(mask.sum())),),
    )


def _features(name, *, lightness=0.64, hue=140.0, role="mid_neutral", owner="sponsors"):
    return DecalInstanceFeatures(
        instance_id=name,
        area_fraction=0.001,
        bbox_normalized=(0.0, 0.0, 0.1, 0.1),
        border_distance_fraction=0.1,
        fill_ratio=0.55,
        aspect_ratio=0.5,
        shape_occupancy=(0.5,) * 16,
        edge_density=0.12,
        strong_gradient_fraction=0.1,
        texture_entropy=0.2,
        mean_rgb=(160.0, 160.0, 160.0),
        std_rgb=(30.0, 30.0, 30.0),
        perceptual_lightness=lightness,
        perceptual_chroma=0.07,
        perceptual_hue_degrees=hue,
        palette_role=role,
        ocr_max_coverage=0.0,
        ocr_alpha_coverage=0.0,
        ocr_digit_coverage=0.0,
        ocr_token_count=0,
        proposed_owners=(owner,),
        proposal_conflict=False,
    )


def test_physical_groups_preserve_exact_disjoint_pixels_without_authority():
    instances = (
        _instance("a", (10, 10, 8, 24)),
        _instance("b", (22, 11, 8, 23)),
        _instance("c", (34, 10, 7, 24)),
    )
    features = tuple(_features(item.instance_id) for item in instances)
    groups = derive_physical_decal_groups(instances, features)
    assert len(groups) == 1
    group = groups[0]
    assert group.instance_ids == ("a", "b", "c")
    assert group.area == sum(item.area for item in instances)
    assert group.area < group.local_mask.size  # gaps were not filled
    telemetry = physical_decal_group_telemetry(instances, features)
    assert telemetry["adds_pixels"] is False
    assert telemetry["casts_votes"] is False
    assert telemetry["ownership_authority"] is False
    records = extract_physical_decal_group_features(
        groups, instances, features, image_shape=(64, 64),
    )
    assert len(records) == 1
    assert records[0].member_count == 3
    assert records[0].sponsor_member_fraction == 1.0
    assert records[0].number_member_fraction == 0.0
    assert records[0].fill_ratio < 1.0


def test_physical_groups_abstain_without_palette_and_proposal_corroboration():
    instances = (
        _instance("a", (10, 10, 8, 24), owner="numbers"),
        _instance("b", (22, 10, 8, 24), owner="sponsors"),
    )
    features = (
        _features("a", lightness=0.1, role="dark_neutral", owner="numbers"),
        _features("b", lightness=0.9, role="chromatic", owner="sponsors"),
    )
    assert derive_physical_decal_groups(instances, features) == ()


def test_physical_groups_reject_body_scale_bounding_groups():
    instances = (
        _instance("a", (0, 0, 200, 200)),
        _instance("b", (180, 0, 200, 200)),
    )
    features = tuple(_features(item.instance_id) for item in instances)
    assert derive_physical_decal_groups(
        instances, features, image_shape=(512, 512), max_bbox_fraction=0.08,
    ) == ()
