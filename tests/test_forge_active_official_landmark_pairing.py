from __future__ import annotations

import copy

from _forge_active_official_landmark_pairing import (
    FALSE_CLAIMS,
    canonical_sha256,
    expected_surfaces,
    pair_landmarks,
    validate_ledger,
)


def _official_landmark(
    official_id: str,
    taxonomy_id: str,
    landmark_type: str,
    surface: str,
    side: str,
) -> dict:
    return {
        "id": official_id,
        "run96_taxonomy_id": taxonomy_id,
        "type": landmark_type,
        "physical_surface": surface,
        "physical_side": side,
        "xy": [100, 200],
        "confidence": 0.95,
        "evidence": {
            "crop_path": f"evidence/{official_id}.png",
            "crop_sha256": official_id.encode("utf-8").hex().ljust(64, "0")[:64],
        },
    }


def _active_landmark(taxonomy_id: str, landmark_type: str) -> dict:
    return {
        "id": taxonomy_id,
        "type": landmark_type,
        "xy_normalized": [0.25, 0.75],
        "confidence": 0.9,
    }


def _fixtures() -> tuple[dict, dict]:
    official = {
        "landmarks": [
            _official_landmark(
                "official.left.rear_arch_top",
                "rear_arch_top",
                "wheel_arch_extremum",
                "left_side",
                "left",
            ),
            _official_landmark(
                "official.right.rear_arch_top",
                "rear_arch_top",
                "wheel_arch_extremum",
                "right_side",
                "right",
            ),
            _official_landmark(
                "official.roof.left_front",
                "roof_left_front",
                "roof_deck_corner",
                "roof",
                "center",
            ),
            _official_landmark(
                "official.spoiler.inside.top_left",
                "spoiler_top_left",
                "spoiler_face_corner",
                "spoiler_inside",
                "center",
            ),
            _official_landmark(
                "official.spoiler.outside.top_left",
                "spoiler_top_left",
                "spoiler_face_corner",
                "spoiler_outside",
                "center",
            ),
            # Exact surface and type but deliberately different taxonomy: never compatible.
            _official_landmark(
                "official.left.rear_arch_right",
                "rear_arch_right",
                "wheel_arch_extremum",
                "left_side",
                "left",
            ),
        ],
        "abstentions": [
            {
                "id": "official.abstain.left.front_arch_left",
                "run96_taxonomy_id": "front_arch_left/front_arch_right",
                "physical_surface": "left_side",
                "physical_side": "left",
                "reason": "official topology evidence is insufficient",
            },
            {
                "id": "official.abstain.hood.centerline",
                "run96_taxonomy_id": "hood_nose_centerline_*",
                "physical_surface": "hood_nose",
                "physical_side": "center",
                "reason": "centerline member is not resolved",
            },
        ],
    }
    active = {
        "views": [
            {
                "source_index": 10,
                "source_path": "left.png",
                "source_sha256": "a" * 64,
                "source_size": [1000, 500],
                "camera_role": "left_profile",
                "physical_side": "left",
                "landmarks": [
                    _active_landmark("rear_arch_top", "wheel_arch_extremum"),
                    _active_landmark("front_arch_left", "wheel_arch_extremum"),
                ],
            },
            {
                "source_index": 11,
                "source_path": "right.png",
                "source_sha256": "b" * 64,
                "source_size": [1000, 500],
                "camera_role": "right_profile",
                "physical_side": "right",
                "landmarks": [
                    _active_landmark("rear_arch_top", "wheel_arch_extremum"),
                ],
            },
            {
                "source_index": 12,
                "source_path": "top.png",
                "source_sha256": "c" * 64,
                "source_size": [600, 1000],
                "camera_role": "top",
                "physical_side": "bilateral",
                "landmarks": [
                    _active_landmark("roof_left_front", "roof_deck_corner"),
                    _active_landmark("spoiler_top_left", "spoiler_face_corner"),
                    _active_landmark("hood_nose_centerline_left", "hood_nose_centerline"),
                ],
            },
        ]
    }
    return active, official


def _records_by_taxonomy(ledger: dict, taxonomy: str) -> list[dict]:
    return [record for record in ledger["records"] if record["active"]["id"] == taxonomy]


def test_expected_surfaces_are_physical_and_fail_closed() -> None:
    assert expected_surfaces(_active_landmark("rear_arch_top", "wheel_arch_extremum"), "left")[0] == ["left_side"]
    assert expected_surfaces(_active_landmark("rear_arch_top", "wheel_arch_extremum"), "bilateral")[0] == []
    assert expected_surfaces(_active_landmark("roof_left_front", "roof_deck_corner"), "bilateral")[0] == ["roof"]
    assert expected_surfaces(_active_landmark("deck_right_rear", "roof_deck_corner"), "bilateral")[0] == ["rear_deck_lid"]
    assert expected_surfaces(_active_landmark("unknown", "unknown_type"), "left")[0] == []


def test_pairing_emits_unique_ambiguous_and_abstain_without_guessing() -> None:
    active, official = _fixtures()
    ledger = pair_landmarks(active, official)
    assert ledger["metrics"] == {
        "active_landmark_count": 6,
        "unique_pair_count": 3,
        "ambiguous_pair_count": 1,
        "abstain_count": 2,
        "distinct_official_anchor_count_in_unique_pairs": 3,
        "preserved_official_abstention_count": 2,
        "transform_count": 0,
        "mirrored_count": 0,
        "polarity_inference_count": 0,
        "livery_pixel_read_count": 0,
    }
    assert validate_ledger(ledger, active_manifest=active, official_manifest=official) == []


def test_left_and_right_active_evidence_never_cross_pairs() -> None:
    active, official = _fixtures()
    ledger = pair_landmarks(active, official)
    pairs = _records_by_taxonomy(ledger, "rear_arch_top")
    assert len(pairs) == 2
    by_side = {record["view"]["physical_side"]: record for record in pairs}
    assert by_side["left"]["compatible_official_candidates"][0]["official_id"] == "official.left.rear_arch_top"
    assert by_side["right"]["compatible_official_candidates"][0]["official_id"] == "official.right.rear_arch_top"


def test_pairing_requires_exact_taxonomy_and_type() -> None:
    active, official = _fixtures()
    ledger = pair_landmarks(active, official)
    left_rear = [
        record
        for record in _records_by_taxonomy(ledger, "rear_arch_top")
        if record["view"]["physical_side"] == "left"
    ][0]
    assert [item["official_id"] for item in left_rear["compatible_official_candidates"]] == [
        "official.left.rear_arch_top"
    ]


def test_spoiler_face_ambiguity_is_preserved_instead_of_face_inference() -> None:
    active, official = _fixtures()
    spoiler = _records_by_taxonomy(pair_landmarks(active, official), "spoiler_top_left")[0]
    assert spoiler["status"] == "ambiguous"
    assert {item["physical_surface"] for item in spoiler["compatible_official_candidates"]} == {
        "spoiler_inside",
        "spoiler_outside",
    }


def test_official_abstentions_are_exactly_preserved_and_matched() -> None:
    active, official = _fixtures()
    ledger = pair_landmarks(active, official)
    assert ledger["official_abstentions"] == official["abstentions"]
    assert ledger["official_abstentions_sha256"] == canonical_sha256(official["abstentions"])
    front = _records_by_taxonomy(ledger, "front_arch_left")[0]
    assert front["status"] == "abstain"
    assert front["matched_official_abstention_ids"] == ["official.abstain.left.front_arch_left"]


def test_validate_rejects_status_candidate_count_drift() -> None:
    active, official = _fixtures()
    ledger = pair_landmarks(active, official)
    broken = copy.deepcopy(ledger)
    _records_by_taxonomy(broken, "spoiler_top_left")[0]["status"] = "unique"
    assert any("unique status requires one candidate" in error for error in validate_ledger(broken))


def test_validate_rejects_side_taxonomy_type_and_surface_drift() -> None:
    active, official = _fixtures()
    ledger = pair_landmarks(active, official)
    mutations = {
        "physical_side": ("right", "candidate side mismatch"),
        "run96_taxonomy_id": ("rear_arch_right", "candidate taxonomy mismatch"),
        "type": ("wrong_type", "candidate type mismatch"),
        "physical_surface": ("roof", "candidate surface mismatch"),
    }
    for key, (value, expected_error) in mutations.items():
        broken = copy.deepcopy(ledger)
        target = [
            record
            for record in _records_by_taxonomy(broken, "rear_arch_top")
            if record["view"]["physical_side"] == "left"
        ][0]
        target["compatible_official_candidates"][0][key] = value
        assert any(expected_error in error for error in validate_ledger(broken)), key


def test_validate_rejects_transform_polarity_mirroring_or_pixel_provenance() -> None:
    active, official = _fixtures()
    ledger = pair_landmarks(active, official)
    for key in ("transform_solved", "polarity_inferred", "mirrored", "active_source_pixels_read", "livery_pixels_used"):
        broken = copy.deepcopy(ledger)
        broken["records"][0]["provenance"][key] = True
        assert any(key in error for error in validate_ledger(broken)), key


def test_all_dense_delivery_and_calibration_claims_remain_false() -> None:
    active, official = _fixtures()
    ledger = pair_landmarks(active, official)
    assert all(ledger["claims"][claim] is False for claim in FALSE_CLAIMS)
    assert len(ledger["records"]) == sum(len(view["landmarks"]) for view in active["views"])

