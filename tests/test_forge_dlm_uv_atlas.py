import hashlib
import json

from PIL import Image

from _forge_dlm_uv_atlas import validate_atlas


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mask(path, pixels):
    image = Image.new("L", (4, 2), 0)
    for x, y in pixels:
        image.putpixel((x, y), 255)
    image.save(path)


def _mask_ref(path, count):
    return {
        "path": path.name,
        "sha256": _sha(path),
        "channel": "luma",
        "threshold": 0,
        "pixel_count": count,
    }


def _orientation(direction=None):
    value = {"rotation_degrees": 0, "flip_x": False, "flip_y": False}
    if direction is not None:
        value["reading_direction"] = direction
    return value


def _triangle():
    return {
        "uv": [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
        "car_space": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
    }


def _atlas(tmp_path):
    official = tmp_path / "official.png"
    left = tmp_path / "left.png"
    right = tmp_path / "right.png"
    calibration = tmp_path / "calibration.png"
    _mask(official, [(x, y) for y in range(2) for x in range(4)])
    _mask(left, [(0, 0), (1, 0), (0, 1), (1, 1)])
    _mask(right, [(2, 0), (3, 0), (2, 1), (3, 1)])
    calibration.write_bytes(b"fixed simulator UV calibration")
    payload = {
        "$schema": "shokk-forge.dlm-uv-atlas/v2",
        "atlas_id": "dlm.official.v2",
        "template": {
            "id": "iracing.dirt_late_model",
            "official_mask": _mask_ref(official, 8),
        },
        "official_pixel_count": 8,
        "islands": [
            {
                "id": "dlm.body.left.main",
                "mask": _mask_ref(left, 4),
                "topology_class": "paintable",
                "physical_surface": "body.left.main",
                "stored_orientation": _orientation(),
                "readable_transform": _orientation("front_to_rear"),
                "adjacent_island_ids": ["dlm.body.right.main"],
                "delivery_surface": True,
            },
            {
                "id": "dlm.body.right.main",
                "mask": _mask_ref(right, 4),
                "topology_class": "paintable",
                "physical_surface": "body.right.main",
                "stored_orientation": _orientation(),
                "readable_transform": _orientation("rear_to_front"),
                "adjacent_island_ids": ["dlm.body.left.main"],
                "delivery_surface": True,
            },
        ],
        "correspondence": [
            {
                "physical_surface": surface,
                "method": "sim_decoded_uv_car_space_v1" if index else "triangulated_uv_car_space_v1",
                "calibration_id": f"fixed.rig.{index}",
                "calibration_source": {
                    "path": calibration.name,
                    "sha256": _sha(calibration),
                },
                "confidence": 0.98,
                "coverage_fraction": 1.0,
                "decoded_sample_count": 12,
                "triangles": [_triangle()],
            }
            for index, surface in enumerate(("body.left.main", "body.right.main"))
        ],
    }
    path = tmp_path / "atlas.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _edit(path, mutate):
    payload = json.loads(path.read_text())
    mutate(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_accepts_complete_hashed_disjoint_calibrated_atlas(tmp_path):
    report = validate_atlas(_atlas(tmp_path))
    assert report["valid"], report["blockers"]
    assert report["topology"]["accounted_pixel_count"] == 8
    assert report["topology"]["overlap_pixel_count"] == 0
    assert report["correspondence"]["missing_delivery_surfaces"] == []


def test_recomputes_overlap_and_unaccounted_instead_of_trusting_totals(tmp_path):
    path = _atlas(tmp_path)
    right = tmp_path / "right.png"
    _mask(right, [(1, 0), (2, 0), (1, 1), (2, 1)])
    _edit(
        path,
        lambda payload: payload["islands"][1].update({"mask": _mask_ref(right, 4)}),
    )
    report = validate_atlas(path)
    assert not report["valid"]
    assert report["topology"]["overlap_pixel_count"] == 2
    assert report["topology"]["unaccounted_pixel_count"] == 2


def test_hash_mismatch_and_declared_pixel_lie_are_rejected(tmp_path):
    path = _atlas(tmp_path)
    _edit(
        path,
        lambda payload: payload["islands"][0]["mask"].update(
            {"sha256": "0" * 64, "pixel_count": 99}
        ),
    )
    report = validate_atlas(path)
    assert not report["valid"]
    assert any("sha256 mismatch" in item for item in report["blockers"])
    assert any("declared 99, actual 4" in item for item in report["blockers"])


def test_unknown_abstain_is_accounted_but_blocks_delivery(tmp_path):
    path = _atlas(tmp_path)
    _edit(
        path,
        lambda payload: payload["islands"][1].update(
            {"topology_class": "unknown_abstain", "delivery_surface": False}
        ),
    )
    report = validate_atlas(path)
    assert not report["valid"]
    assert report["topology"]["accounted_pixel_count"] == 8
    assert report["topology"]["unknown_abstain_ids"] == ["dlm.body.right.main"]


def test_delivery_surface_rejects_bbox_affine_or_missing_calibration(tmp_path):
    path = _atlas(tmp_path)
    _edit(
        path,
        lambda payload: payload["correspondence"][0].update(
            {"method": "bbox_affine_v1", "calibration_id": ""}
        ),
    )
    report = validate_atlas(path)
    assert not report["valid"]
    assert any("uncalibrated/unsupported" in item for item in report["blockers"])
    assert any("stable calibration_id" in item for item in report["blockers"])


def test_delivery_surface_requires_nondegenerate_piecewise_mapping(tmp_path):
    path = _atlas(tmp_path)
    _edit(
        path,
        lambda payload: payload["correspondence"][0].update(
            {
                "confidence": 0.5,
                "coverage_fraction": 0.8,
                "triangles": [
                    {
                        "uv": [[0, 0], [1, 1], [2, 2]],
                        "car_space": [[0, 0, 0], [1, 0, 0], [2, 0, 0]],
                    }
                ],
            }
        ),
    )
    report = validate_atlas(path)
    assert not report["valid"]
    assert any("below 0.900" in item for item in report["blockers"])
    assert any("below 0.9900" in item for item in report["blockers"])
    assert any("degenerate UV triangle" in item for item in report["blockers"])
    assert any("degenerate car-space triangle" in item for item in report["blockers"])


def test_adjacency_must_reference_known_islands_and_be_reciprocal(tmp_path):
    path = _atlas(tmp_path)
    _edit(
        path,
        lambda payload: payload["islands"][1].update({"adjacent_island_ids": []}),
    )
    report = validate_atlas(path)
    assert not report["valid"]
    assert any("is not reciprocal" in item for item in report["blockers"])


def test_broad_surface_mask_cannot_pose_as_one_uv_island(tmp_path):
    path = _atlas(tmp_path)
    left = tmp_path / "left.png"
    _mask(left, [(0, 0), (1, 1)])
    _edit(
        path,
        lambda payload: payload["islands"][0].update({"mask": _mask_ref(left, 2)}),
    )
    report = validate_atlas(path)
    assert not report["valid"]
    assert any("one exact connected UV island required" in item for item in report["blockers"])

def test_shared_uint16_label_map_can_define_exact_island_masks(tmp_path):
    path = _atlas(tmp_path)
    labels_path = tmp_path / "island-labels.png"
    labels = Image.new("I;16", (4, 2), 0)
    for y in range(2):
        for x in range(4):
            labels.putpixel((x, y), 1 if x < 2 else 2)
    labels.save(labels_path)
    label_hash = _sha(labels_path)

    def use_labels(payload):
        for value, island in enumerate(payload["islands"], start=1):
            island["mask"] = {
                "path": labels_path.name,
                "sha256": label_hash,
                "channel": "label16",
                "value": value,
                "pixel_count": 4,
            }

    _edit(path, use_labels)
    report = validate_atlas(path)
    assert report["valid"], report["blockers"]
    assert report["topology"]["accounted_pixel_count"] == 8
    assert report["topology"]["island_count"] == 2
