from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from _forge_semantic_instance_gate import JOB_SCHEMA, PRODUCTION_THRESHOLDS, evaluate_semantic_instances


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_mask(path: Path, mask: np.ndarray) -> dict:
    Image.fromarray(np.where(mask, 255, 0).astype(np.uint8)).save(path)
    return {"path": path.name, "sha256": _sha(path)}


def _write_raster(path: Path, mask: np.ndarray) -> dict:
    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[mask] = (245, 210, 30, 255)
    Image.fromarray(rgba, "RGBA").save(path)
    return {"path": path.name, "sha256": _sha(path)}


def _job(root: Path, *, instances: int = 1, duplicate_full: bool = False, nonadjacent: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    canvas = (64, 64)
    domain = np.ones((20, 30), dtype=bool)
    domain_record = _write_mask(root / "domain.png", domain)
    rows = []
    for instance_index in range(instances):
        uv_base = np.zeros(canvas, dtype=bool)
        uv_base[5 + instance_index * 25:20 + instance_index * 25, 8:38] = True
        fragments = []
        for fragment_index in range(2):
            object_mask = domain.copy() if duplicate_full else np.zeros_like(domain)
            if not duplicate_full:
                object_mask[:, :15] = fragment_index == 0
                object_mask[:, 15:] = fragment_index == 1
            uv_mask = np.zeros(canvas, dtype=bool)
            source = uv_base.copy()
            uv_mask[:, :23] = source[:, :23] if fragment_index == 0 else False
            uv_mask[:, 23:] = source[:, 23:] if fragment_index == 1 else False
            oid = _write_mask(root / f"o_{instance_index}_{fragment_index}.png", object_mask)
            uid = _write_mask(root / f"u_{instance_index}_{fragment_index}.png", uv_mask)
            raster = _write_raster(root / f"r_{instance_index}_{fragment_index}.png", uv_mask)
            fragments.append({"id": f"part_{fragment_index}", "surface": ("hood" if fragment_index == 0 else ("rear" if nonadjacent else "nose")), "object_mask": oid, "uv_mask": uid, "raster": raster})
        rows.append({"id": f"hero_instance_{instance_index}", "master_id": "hero", "object_domain": domain_record, "fragments": fragments})
    job = {
        "$schema": JOB_SCHEMA,
        "canvas": [canvas[1], canvas[0]],
        "masters": [{"id": "hero", "expected_physical_instances": 1, "allowed_surfaces": ["hood", "nose", "rear"]}],
        "allowed_surface_adjacencies": [["hood", "nose"]],
        "instances": rows,
    }
    path = root / "job.json"
    path.write_text(json.dumps(job, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_one_object_disjointly_split_across_adjacent_surfaces_passes(tmp_path: Path) -> None:
    job = _job(tmp_path / "pass")
    result = evaluate_semantic_instances(job, tmp_path / "out")
    assert result["semantic_instance_ready"]
    assert not result["livery_ready"] and not result["psd_ready"] and not result["delivery_ready"]
    assert result["instances"][0]["metrics"]["object_overlap_pixels"] == 0
    assert result["masters"][0]["actual_physical_instances"] == 1


def test_complete_front_object_cannot_be_stamped_as_second_instance(tmp_path: Path) -> None:
    job = _job(tmp_path / "two", instances=2)
    result = evaluate_semantic_instances(job, tmp_path / "out")
    assert not result["semantic_instance_ready"]
    assert "master:hero:physical_cardinality" in result["blockers"]


def test_full_object_repeated_per_uv_island_is_rejected(tmp_path: Path) -> None:
    job = _job(tmp_path / "duplicate", duplicate_full=True)
    result = evaluate_semantic_instances(job, tmp_path / "out")
    assert not result["semantic_instance_ready"]
    assert result["instances"][0]["metrics"]["object_overlap_pixels"] == 600
    assert "instance:hero_instance_0:object_overlap" in result["blockers"]


def test_cross_surface_split_requires_declared_adjacency(tmp_path: Path) -> None:
    job = _job(tmp_path / "adjacency", nonadjacent=True)
    result = evaluate_semantic_instances(job, tmp_path / "out")
    assert not result["semantic_instance_ready"]
    assert "instance:hero_instance_0:surface_adjacency" in result["blockers"]


def test_alpha_outside_declared_uv_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "outside"
    job = _job(root)
    value = json.loads(job.read_text(encoding="utf-8"))
    record = value["instances"][0]["fragments"][0]["raster"]
    raster = root / record["path"]
    rgba = np.asarray(Image.open(raster).convert("RGBA")).copy()
    rgba[0, 0] = (255, 0, 0, 255)
    Image.fromarray(rgba, "RGBA").save(raster)
    record["sha256"] = _sha(raster)
    job.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = evaluate_semantic_instances(job, tmp_path / "out")
    assert not result["semantic_instance_ready"]
    assert "instance:hero_instance_0:alpha_outside_uv" in result["blockers"]


def test_missing_object_partition_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "missing"
    job = _job(root)
    value = json.loads(job.read_text(encoding="utf-8"))
    fragment = value["instances"][0]["fragments"][1]
    mask = np.zeros((20, 30), dtype=bool)
    fragment["object_mask"] = _write_mask(root / "missing_object.png", mask)
    job.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = evaluate_semantic_instances(job, tmp_path / "out")
    assert not result["semantic_instance_ready"]
    assert result["instances"][0]["metrics"]["object_missing_pixels"] == 300


def test_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    job = _job(tmp_path / "hash")
    value = json.loads(job.read_text(encoding="utf-8"))
    value["instances"][0]["fragments"][0]["uv_mask"]["sha256"] = "0" * 64
    job.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = evaluate_semantic_instances(job, tmp_path / "out")
    assert result["blockers"] == ["hero_instance_0_part_0_uv_mask_sha256_mismatch"]


def test_thresholds_are_production_locked(tmp_path: Path) -> None:
    job = _job(tmp_path / "threshold")
    value = json.loads(job.read_text(encoding="utf-8"))
    value["thresholds"] = {**PRODUCTION_THRESHOLDS, "maximum_object_overlap_pixels": 999.0}
    job.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = evaluate_semantic_instances(job, tmp_path / "out")
    assert result["blockers"] == ["threshold_overrides_forbidden"]


def test_independent_left_and_right_instances_are_allowed_when_evidenced(tmp_path: Path) -> None:
    root = tmp_path / "two_evidenced"
    job = _job(root, instances=2)
    value = json.loads(job.read_text(encoding="utf-8"))
    value["masters"][0]["expected_physical_instances"] = 2
    job.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = evaluate_semantic_instances(job, tmp_path / "out")
    assert result["semantic_instance_ready"]
    assert result["masters"][0]["actual_physical_instances"] == 2
