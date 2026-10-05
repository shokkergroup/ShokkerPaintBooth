import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_dlm_exact_topology import build_exact_topology


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_mask(path, size, pixels):
    image = Image.new("L", size, 0)
    for x, y in pixels:
        image.putpixel((x, y), 255)
    image.save(path)


def _adapter(tmp_path, rows, *, name="adapter.json"):
    surfaces = {}
    for surface_id, pixels in rows:
        mask_path = tmp_path / f"{surface_id}.png"
        _write_mask(mask_path, (8, 6), pixels)
        surfaces[surface_id] = {
            "coverage_mask_path": mask_path.name,
            "mask_sha256": _sha(mask_path),
        }
    payload = {
        "$schema": "shokk-forge.template-adapter/v1",
        "adapter_id": "synthetic-dlm-topology",
        "livery_agnostic": True,
        "surfaces": surfaces,
    }
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _official(tmp_path):
    first = {(0, 0), (1, 0), (0, 1), (1, 1)}
    second = {(5, 3), (6, 3), (6, 4)}
    path = tmp_path / "official.png"
    _write_mask(path, (8, 6), first | second)
    return path, first, second


def test_exact_label_union_and_component_inventory(tmp_path):
    official, first, second = _official(tmp_path)
    adapter = _adapter(tmp_path, [("body.left", first), ("body.right", second)])

    report = build_exact_topology(official, adapter, tmp_path / "out")

    with Image.open(report["label_map"]["path"]) as label_image:
        assert label_image.mode == "I;16"
        labels = np.asarray(label_image, dtype=np.uint16)
    assert set(np.unique(labels)) == {0, 1, 2}
    assert int((labels > 0).sum()) == 7
    assert report["topology"]["official_pixel_count"] == 7
    assert report["topology"]["label_union_pixel_count"] == 7
    assert report["topology"]["unaccounted_official_pixel_count"] == 0
    assert report["topology"]["outside_official_label_pixel_count"] == 0
    assert report["topology"]["assigned_pixel_count"] == 7
    assert report["topology"]["unknown_abstain_pixel_count"] == 0
    assert report["topology"]["assigned_pixel_fraction"] == 1.0
    assert [row["pixel_count"] for row in report["islands"]] == [4, 3]
    assert [row["bbox"] for row in report["islands"]] == [[0, 0, 2, 2], [5, 3, 7, 5]]
    assert [row["physical_surface"] for row in report["islands"]] == [
        "body.left",
        "body.right",
    ]
    assert report["claims"]["correspondence"] is False
    assert report["claims"]["delivery_ready"] is False
    assert (tmp_path / "out" / "dlm_exact_topology_labels.png").is_file()
    assert (tmp_path / "out" / "dlm_exact_topology_inventory.json").is_file()
    qa_path = Path(report["qa_visual"]["path"])
    assert qa_path.is_file()
    assert report["qa_visual"]["sha256"] == _sha(qa_path)
    qa = np.asarray(Image.open(qa_path).convert("RGB"))
    assert tuple(qa[0, 0]) == (36, 190, 100)
    assert tuple(qa[2, 2]) == (0, 0, 0)

def test_partial_or_competing_surface_evidence_abstains(tmp_path):
    official, first, second = _official(tmp_path)
    partial_first = {(0, 0), (1, 0), (0, 1)}
    full_second = set(second)
    competitor = {(5, 3)}
    adapter = _adapter(
        tmp_path,
        [
            ("body.partial", partial_first),
            ("body.second", full_second),
            ("body.competitor", competitor),
        ],
    )

    report = build_exact_topology(official, adapter, tmp_path / "out")

    assert [row["topology_class"] for row in report["islands"]] == [
        "unknown_abstain",
        "unknown_abstain",
    ]
    assert [row["assignment_basis"] for row in report["islands"]] == [
        "no_surface_reaches_0.98",
        "competing_surface_overlap",
    ]
    assert report["topology"]["unknown_abstain_component_count"] == 2


def test_adapter_masks_are_clipped_and_bleed_is_reported_separately(tmp_path):
    official, first, second = _official(tmp_path)
    adapter = _adapter(
        tmp_path,
        [
            ("body.left", first | {(7, 5)}),
            ("body.right", second | {(3, 2), (4, 2)}),
        ],
    )

    report = build_exact_topology(official, adapter, tmp_path / "out")

    by_surface = {row["physical_surface"]: row for row in report["adapter_surfaces"]}
    assert by_surface["body.left"]["raw_pixel_count"] == 5
    assert by_surface["body.left"]["clipped_official_pixel_count"] == 4
    assert by_surface["body.left"]["adapter_bleed_pixel_count"] == 1
    assert by_surface["body.right"]["adapter_bleed_pixel_count"] == 2
    assert report["topology"]["adapter_bleed_union_pixel_count"] == 3
    assert report["topology"]["adapter_bleed_sum_pixel_count"] == 3
    assert report["topology"]["outside_official_label_pixel_count"] == 0
    assert all(row["topology_class"] == "paintable" for row in report["islands"])


def test_label_values_and_stable_ids_are_deterministic_across_adapter_order(tmp_path):
    official, first, second = _official(tmp_path)
    adapter_a = _adapter(
        tmp_path,
        [("body.left", first), ("body.right", second)],
        name="adapter-a.json",
    )
    adapter_b = _adapter(
        tmp_path,
        [("body.right", second), ("body.left", first)],
        name="adapter-b.json",
    )

    first_report = build_exact_topology(official, adapter_a, tmp_path / "first")
    second_report = build_exact_topology(official, adapter_b, tmp_path / "second")

    assert Path(first_report["label_map"]["path"]).read_bytes() == Path(
        second_report["label_map"]["path"]
    ).read_bytes()
    assert [row["id"] for row in first_report["islands"]] == [
        row["id"] for row in second_report["islands"]
    ]
    assert [row["label_value"] for row in first_report["islands"]] == [1, 2]

def test_diagonal_pixels_are_distinct_four_connected_components(tmp_path):
    official = tmp_path / "official-diagonal.png"
    diagonal = {(2, 2), (3, 3)}
    _write_mask(official, (8, 6), diagonal)
    adapter = _adapter(tmp_path, [("body.diagonal", diagonal)], name="adapter-diagonal.json")

    report = build_exact_topology(official, adapter, tmp_path / "diagonal-out")

    assert report["topology"]["connectivity"] == 4
    assert report["topology"]["component_count"] == 2
    assert [row["pixel_count"] for row in report["islands"]] == [1, 1]
