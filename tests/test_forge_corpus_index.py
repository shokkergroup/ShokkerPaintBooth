from __future__ import annotations

import struct
from pathlib import Path

import pytest

from _forge_corpus_index import (
    SCHEMA,
    TGA_HEADER,
    build_index,
    classify_paint_role,
    paint_id,
    parse_tga_header,
)


def _write_tga(path: Path, *, width: int = 2048, height: int = 2048, descriptor: int = 0x28) -> None:
    header = TGA_HEADER.pack(0, 0, 2, 0, 0, 0, 0, 0, width, height, 32, descriptor)
    path.write_bytes(header + b"synthetic-pixels")


def test_tga_header_preserves_canvas_origin_and_alpha(tmp_path: Path) -> None:
    root = tmp_path / "corpus_header"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "car_101.tga"
    _write_tga(path)
    header = parse_tga_header(path)
    assert header["width"] == 2048
    assert header["height"] == 2048
    assert header["alpha_bits"] == 8
    assert header["origin"] == {"horizontal": "left", "vertical": "top"}
    assert header["supported_image_type"] is True


@pytest.mark.parametrize(
    ("name", "role", "identifier"),
    [
        ("car_123.tga", "plain_livery", "123"),
        ("car_num_456.tga", "numbered_livery", "456"),
        ("car_decal_789.tga", "decal_livery", "789"),
        ("car_spec_12.tga", "material_or_base", "12"),
        ("paint_base.tga", "material_or_base", None),
    ],
)
def test_generic_filename_roles(name: str, role: str, identifier: str | None) -> None:
    assert classify_paint_role(name) == role
    assert paint_id(name) == identifier


def test_holdout_is_quarantined_from_training_count(tmp_path: Path) -> None:
    root = tmp_path / "corpus_holdout"
    root.mkdir(parents=True, exist_ok=True)
    _write_tga(root / "car_1.tga")
    _write_tga(root / "car_num_2.tga")
    index = build_index([("family_a", root)], [], {"2"})
    assert index["$schema"] == SCHEMA
    assert index["tga_summary"]["file_count"] == 2
    assert index["tga_summary"]["training_count"] == 1
    assert index["tga_summary"]["holdout_count"] == 1
    holdout = next(row for row in index["tgas"] if row["paint_id"] == "2")
    assert holdout["holdout"] is True


def test_truncated_tga_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "corpus_truncated"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "bad.tga"
    path.write_bytes(struct.pack("<I", 7))
    with pytest.raises(ValueError, match="truncated"):
        parse_tga_header(path)


def test_cross_family_duplicate_and_identity_evidence(tmp_path: Path) -> None:
    root_a = tmp_path / "corpus_family_a"
    root_b = tmp_path / "corpus_family_b"
    root_a.mkdir(parents=True, exist_ok=True)
    root_b.mkdir(parents=True, exist_ok=True)
    _write_tga(root_a / "car_77.tga")
    _write_tga(root_a / "car_num_77.tga")
    _write_tga(root_b / "car_77.tga")
    index = build_index([("family_a", root_a), ("family_b", root_b)], [], set())
    summary = index["tga_summary"]
    assert summary["cross_family_sample_duplicate_group_count"] == 1
    assert summary["cross_family_sample_duplicate_file_count"] == 3
    assert summary["shared_id_pairs"] == [
        {"family_a": "family_a", "family_b": "family_b", "shared_paint_ids": 1}
    ]
    family_a = next(row for row in summary["families"] if row["family"] == "family_a")
    assert family_a["plain_number_pair_count"] == 1
