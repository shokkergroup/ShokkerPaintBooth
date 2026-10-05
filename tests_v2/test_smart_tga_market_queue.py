from pathlib import Path

from scripts.smart_tga_market_queue import (
    filename_intent,
    inventory,
    market_segment,
    select_queue,
)


def _paint(root: Path, folder: str, filename: str) -> Path:
    path = root / folder / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fixture")
    return path


def test_owner_filename_contract_is_explicit():
    assert filename_intent("car_num_23371.tga") == "numbered"
    assert filename_intent("car_num_team_23371.tga") == "numbered"
    assert filename_intent("car_23371.tga") == "non_numbered_control"
    assert filename_intent("car_team_23371.tga") == "non_numbered_control"
    assert filename_intent("car_decal_23371.tga") is None
    assert filename_intent("car_num_.tga") is None


def test_duplicate_family_filename_across_roots_is_sampled_once(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    _paint(first, "dirtlatemodel 358", "car_num_42.tga")
    _paint(second, "dirtlatemodel 358", "car_num_42.tga")
    records = inventory([first, second])
    assert len(records) == 1
    assert records[0].path.startswith(str(first.resolve()))


def test_only_release_market_families_enter_inventory(tmp_path):
    _paint(tmp_path, "dirtlatemodel 358", "car_num_1.tga")
    _paint(tmp_path, "stockcars2 arcachevy25", "car_num_2.tga")
    _paint(tmp_path, "trucks silverado2019", "car_num_3.tga")
    _paint(tmp_path, "bmwlmdh", "car_num_4.tga")
    records = inventory([tmp_path])
    assert {r.segment for r in records} == {
        "dirt_late_model", "nascar_stock_car", "truck",
    }
    assert all("bmwlmdh" not in r.path for r in records)


def test_exact_plain_car_pair_is_ranked_for_safety_audit(tmp_path):
    control = _paint(tmp_path, "dirtlatemodel 358", "car_17.tga")
    _paint(tmp_path, "dirtlatemodel 358", "car_num_17.tga")
    records = inventory([tmp_path])
    numbered = next(r for r in records if r.filename_intent == "numbered")
    assert numbered.priority == 0
    assert numbered.paired_control == str(control.resolve())


def test_queue_is_numbered_heavy_and_segment_balanced(tmp_path):
    folders = ("dirtlatemodel 358", "stockcars2 arcachevy25", "trucks fordf150")
    for folder_index, folder in enumerate(folders):
        for sample in range(5):
            _paint(tmp_path, folder, f"car_num_{folder_index}{sample}.tga")
        _paint(tmp_path, folder, f"car_{folder_index}.tga")
    selected = select_queue(inventory([tmp_path]), limit=10, control_fraction=0.10)
    assert sum(r.filename_intent == "numbered" for r in selected) == 9
    assert sum(r.filename_intent == "non_numbered_control" for r in selected) == 1
    numbered_segments = [r.segment for r in selected if r.filename_intent == "numbered"]
    assert numbered_segments.count("dirt_late_model") == 3
    assert numbered_segments.count("nascar_stock_car") == 3
    assert numbered_segments.count("truck") == 3


def test_queue_diversifies_vehicle_folders_within_segment(tmp_path):
    for sample in range(6):
        _paint(tmp_path, "dirtlatemodel 350", f"car_num_{sample}.tga")
    _paint(tmp_path, "dirtlatemodel 358", "car_num_90.tga")
    selected = select_queue(inventory([tmp_path]), limit=2, control_fraction=0.0)
    assert {record.source_family for record in selected} == {
        "dirtlatemodel 350", "dirtlatemodel 358",
    }


def test_market_segment_does_not_expand_to_unrequested_racing_families():
    assert market_segment("Dirt Late Model") == "dirt_late_model"
    assert market_segment("stockcars chevy gen4cup") == "nascar_stock_car"
    assert market_segment("protrucks pro4truck") == "truck"
    assert market_segment("porsche963gtp") is None
