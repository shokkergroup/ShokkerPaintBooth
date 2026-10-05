from __future__ import annotations

import pytest

from scripts.smart_tga_instance_feature_bank import attach_review_links, build_feature_bank


def _inspection(*, records=None, authority=False, casts_votes=False):
    features = {
        "ownership_authority": authority,
        "casts_votes": casts_votes,
    }
    if records is not None:
        features["records"] = records
    return {
        "paint_label": "dirtlatemodel 350/car_num_1.tga",
        "route_adjudicator_shadow": {
            "candidate_evidence": {
                "decal_instances": {
                    "ownership_authority": False,
                    "casts_votes": False,
                    "features": features,
                }
            }
        },
    }


def test_feature_bank_is_durable_sorted_and_owner_neutral():
    bank = build_feature_bank([_inspection(records=[
        {"instance_id": "di:b", "bbox": [4, 5, 6, 7]},
        {"instance_id": "di:a", "bbox": [1, 2, 3, 4]},
    ])])
    assert bank["schema"] == "smart-tga-instance-feature-bank-v1"
    assert bank["paint_count"] == 1
    assert bank["instance_count"] == 2
    assert [item["instance_id"] for item in bank["records"]] == ["di:a", "di:b"]
    assert bank["ownership_authority"] is False
    assert bank["casts_votes"] is False


def test_feature_bank_requires_explicit_full_export_and_rejects_authority():
    with pytest.raises(ValueError, match="FEATURE_EXPORT=1"):
        build_feature_bank([_inspection()])
    with pytest.raises(ValueError, match="rejected authority"):
        build_feature_bank([_inspection(records=[], authority=True)])


def test_review_links_are_overlap_gated_ambiguous_and_never_authoritative():
    bank = {
        "records": [
            {"paint_label": "p", "instance_id": "di:a", "bbox": [10, 10, 20, 20]},
            {"paint_label": "p", "instance_id": "di:b", "bbox": [40, 10, 20, 20]},
        ]
    }
    labels = [{
        "paint_label": "p",
        "component_labels": [
            {"layer": "numbers", "component_index": 1, "expected_bbox": [11, 11, 18, 18], "target_layer": "numbers", "label": "true_number", "family_id": "number:24"},
            {"layer": "sponsors", "component_index": 2, "expected_bbox": [10, 10, 50, 20], "target_layer": "sponsors", "label": "wide_logo"},
            {"layer": "paint", "component_index": 3, "expected_bbox": [80, 50, 5, 5], "target_layer": "paint", "label": "livery"},
        ],
    }]
    linked = attach_review_links(bank, labels)
    assert [item["status"] for item in linked["review_links"]] == [
        "matched_for_review", "ambiguous", "unmatched"
    ]
    assert linked["review_links"][0]["instance_id"] == "di:a"
    assert linked["review_links"][0]["review_family_id"] == "number:24"
    assert all(item["ownership_authority"] is False for item in linked["review_links"])
    assert all(item["human_review_required"] is True for item in linked["review_links"])
