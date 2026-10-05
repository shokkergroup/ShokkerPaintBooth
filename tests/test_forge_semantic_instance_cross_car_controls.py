from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from _forge_semantic_instance_gate import JOB_SCHEMA, evaluate_semantic_instances


CANVAS = (96, 96)
OBJECT_SHAPE = (24, 36)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(path: Path) -> dict[str, str]:
    return {"path": path.name, "sha256": _sha(path)}


def _mask(path: Path, value: np.ndarray) -> dict[str, str]:
    Image.fromarray(np.where(value, 255, 0).astype(np.uint8)).save(path)
    return _record(path)


def _raster(path: Path, value: np.ndarray, colour: tuple[int, int, int]) -> dict[str, str]:
    rgba = np.zeros((*value.shape, 4), dtype=np.uint8)
    rgba[value] = (*colour, 255)
    Image.fromarray(rgba, "RGBA").save(path)
    return _record(path)


def _fragment(surface: str, object_x: tuple[int, int], uv_rect: tuple[int, int, int, int]) -> dict:
    return {"surface": surface, "object_x": list(object_x), "uv_rect": list(uv_rect)}


def _waffle_contract() -> dict:
    return {
        "control_id": "waffle_front_single_instance",
        "masters": [{
            "id": "front_brand_lockup",
            "expected_physical_instances": 1,
            "allowed_surfaces": ["hood", "nose"],
            "instances": [{
                "id": "front_brand_primary",
                "fragments": [
                    _fragment("hood", (0, 18), (8, 8, 32, 26)),
                    _fragment("nose", (18, 36), (34, 8, 58, 26)),
                ],
            }],
        }],
        "adjacencies": [["hood", "nose"]],
    }


def _dominos_contract() -> dict:
    return {
        "control_id": "dominos_two_evidenced_side_numbers",
        "masters": [{
            "id": "side_number",
            "expected_physical_instances": 2,
            "allowed_surfaces": ["left_side", "left_fender", "right_side", "right_fender"],
            "instances": [
                {"id": "side_number_left", "fragments": [
                    _fragment("left_side", (0, 25), (8, 10, 32, 28)),
                    _fragment("left_fender", (25, 36), (32, 10, 44, 28)),
                ]},
                {"id": "side_number_right", "fragments": [
                    _fragment("right_side", (0, 25), (52, 10, 76, 28)),
                    _fragment("right_fender", (25, 36), (76, 10, 88, 28)),
                ]},
            ],
        }],
        "adjacencies": [["left_side", "left_fender"], ["right_side", "right_fender"]],
    }


def _crystal_contract() -> dict:
    return {
        "control_id": "crystal_numbers_and_sponsor_split",
        "masters": [
            {
                "id": "side_number",
                "expected_physical_instances": 2,
                "allowed_surfaces": ["left_side", "right_side"],
                "instances": [
                    {"id": "side_number_left", "fragments": [_fragment("left_side", (0, 36), (8, 10, 34, 32))]},
                    {"id": "side_number_right", "fragments": [_fragment("right_side", (0, 36), (56, 10, 82, 32))]},
                ],
            },
            {
                "id": "sponsor_line",
                "expected_physical_instances": 1,
                "allowed_surfaces": ["left_side", "left_fender"],
                "instances": [{"id": "sponsor_line_left", "fragments": [
                    _fragment("left_side", (0, 22), (10, 50, 45, 62)),
                    _fragment("left_fender", (22, 36), (45, 50, 68, 62)),
                ]}],
            },
        ],
        "adjacencies": [["left_side", "left_fender"]],
    }


def _sex_wax_contract() -> dict:
    return {
        "control_id": "sex_wax_three_evidenced_round_logos",
        "masters": [{
            "id": "round_logo",
            "expected_physical_instances": 3,
            "allowed_surfaces": ["left_side", "right_side", "roof"],
            "instances": [
                {"id": "round_logo_left", "fragments": [_fragment("left_side", (0, 36), (8, 8, 30, 30))]},
                {"id": "round_logo_right", "fragments": [_fragment("right_side", (0, 36), (38, 8, 60, 30))]},
                {"id": "round_logo_roof", "fragments": [_fragment("roof", (0, 36), (68, 8, 90, 30))]},
            ],
        }],
        "adjacencies": [],
    }


SCHEME_CONTRACTS = {
    "waffle": _waffle_contract,
    "dominos": _dominos_contract,
    "crystal_lake": _crystal_contract,
    "sex_wax": _sex_wax_contract,
}


def build_control_job(root: Path, scheme: str, contract: dict | None = None) -> Path:
    """Materialize a data-only scheme contract; gate code remains identity blind."""

    root.mkdir(parents=True, exist_ok=True)
    value = deepcopy(contract if contract is not None else SCHEME_CONTRACTS[scheme]())
    masters = []
    instances = []
    colour_seed = 0
    for master in value["masters"]:
        master_id = master["id"]
        masters.append({
            "id": master_id,
            "expected_physical_instances": master["expected_physical_instances"],
            "allowed_surfaces": master["allowed_surfaces"],
        })
        domain = np.ones(OBJECT_SHAPE, dtype=bool)
        domain_record = _mask(root / f"{master_id}_domain.png", domain)
        for instance in master["instances"]:
            fragments = []
            for index, fragment in enumerate(instance["fragments"]):
                object_mask = np.zeros(OBJECT_SHAPE, dtype=bool)
                start, stop = fragment["object_x"]
                object_mask[:, start:stop] = True
                uv_mask = np.zeros(CANVAS, dtype=bool)
                x0, y0, x1, y1 = fragment["uv_rect"]
                uv_mask[y0:y1, x0:x1] = True
                prefix = f"{instance['id']}_{index}"
                object_record = _mask(root / f"{prefix}_object.png", object_mask)
                uv_record = _mask(root / f"{prefix}_uv.png", uv_mask)
                colour_seed += 1
                colour = (55 + colour_seed * 31 % 190, 55 + colour_seed * 53 % 190, 55 + colour_seed * 71 % 190)
                raster_record = _raster(root / f"{prefix}_raster.png", uv_mask, colour)
                fragments.append({
                    "id": f"part_{index}",
                    "surface": fragment["surface"],
                    "object_mask": object_record,
                    "uv_mask": uv_record,
                    "raster": raster_record,
                })
            instances.append({
                "id": instance["id"],
                "master_id": master_id,
                "object_domain": domain_record,
                "fragments": fragments,
            })
    job = {
        "$schema": JOB_SCHEMA,
        "canvas": [CANVAS[1], CANVAS[0]],
        "control_id": value["control_id"],
        "scheme_identity_is_data_only": scheme,
        "masters": masters,
        "allowed_surface_adjacencies": value["adjacencies"],
        "instances": instances,
    }
    path = root / "semantic_contract.json"
    path.write_text(json.dumps(job, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("scheme", tuple(SCHEME_CONTRACTS))
def test_four_scheme_contracts_pass_the_same_identity_blind_gate(tmp_path: Path, scheme: str) -> None:
    job = build_control_job(tmp_path / f"{scheme}_pass", scheme)
    result = evaluate_semantic_instances(job, tmp_path / f"{scheme}_pass_out")
    assert result["semantic_instance_ready"]
    assert not result["livery_ready"]
    assert not result["psd_ready"]
    assert not result["delivery_ready"]
    assert all(row["ready"] for row in result["masters"])
    assert all(row["ready"] for row in result["instances"])


def test_waffle_duplicate_front_lockup_is_rejected(tmp_path: Path) -> None:
    contract = _waffle_contract()
    for fragment in contract["masters"][0]["instances"][0]["fragments"]:
        fragment["object_x"] = [0, 36]
    job = build_control_job(tmp_path / "waffle_duplicate", "waffle", contract)
    result = evaluate_semantic_instances(job, tmp_path / "waffle_duplicate_out")
    assert not result["semantic_instance_ready"]
    assert result["instances"][0]["metrics"]["object_overlap_pixels"] == 864
    assert "instance:front_brand_primary:object_overlap" in result["blockers"]


def test_dominos_third_unevidenced_side_number_is_rejected(tmp_path: Path) -> None:
    contract = _dominos_contract()
    third = deepcopy(contract["masters"][0]["instances"][0])
    third["id"] = "side_number_unevidenced"
    third["fragments"][0]["uv_rect"] = [8, 66, 32, 84]
    third["fragments"][1]["uv_rect"] = [32, 66, 44, 84]
    contract["masters"][0]["instances"].append(third)
    job = build_control_job(tmp_path / "dominos_third", "dominos", contract)
    result = evaluate_semantic_instances(job, tmp_path / "dominos_third_out")
    assert not result["semantic_instance_ready"]
    assert result["masters"][0]["actual_physical_instances"] == 3
    assert "master:side_number:physical_cardinality" in result["blockers"]


def test_crystal_clipped_sponsor_partition_is_rejected(tmp_path: Path) -> None:
    contract = _crystal_contract()
    sponsor = contract["masters"][1]["instances"][0]
    sponsor["fragments"][1]["object_x"] = [22, 22]
    job = build_control_job(tmp_path / "crystal_clipped", "crystal_lake", contract)
    result = evaluate_semantic_instances(job, tmp_path / "crystal_clipped_out")
    assert not result["semantic_instance_ready"]
    sponsor_result = next(row for row in result["instances"] if row["master_id"] == "sponsor_line")
    assert sponsor_result["metrics"]["object_missing_pixels"] == 336
    assert "instance:sponsor_line_left:object_missing" in result["blockers"]


def test_sex_wax_two_instances_cannot_claim_the_same_uv_pixels(tmp_path: Path) -> None:
    contract = _sex_wax_contract()
    instances = contract["masters"][0]["instances"]
    instances[2]["fragments"][0]["uv_rect"] = list(instances[0]["fragments"][0]["uv_rect"])
    job = build_control_job(tmp_path / "sex_wax_overlap", "sex_wax", contract)
    result = evaluate_semantic_instances(job, tmp_path / "sex_wax_overlap_out")
    assert not result["semantic_instance_ready"]
    assert result["masters"][0]["same_master_uv_overlap_pixels"] == 484
    assert "master:round_logo:same_master_uv_overlap" in result["blockers"]


def test_reusable_gate_contains_no_cross_car_identity_branches() -> None:
    source = Path("_forge_semantic_instance_gate.py").read_text(encoding="utf-8").lower()
    for identity in ("waffle", "dominos", "crystal_lake", "sex_wax"):
        assert identity not in source
