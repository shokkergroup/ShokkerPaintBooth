from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from demo.backend.build_snapshots import (
    THUMBNAIL_DIMENSIONS,
    THUMBNAIL_TILE_SIZE,
    _renderer_zone,
    _square_field,
    _write_thumbnail,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "demo" / "product-manifest.json"
SNAPSHOTS = ROOT / "demo" / "backend" / "assets" / "snapshots"
THUMBNAILS = ROOT / "demo" / "backend" / "assets" / "thumbnails"

# These BASE_REGISTRY materials have authored paint construction.  They were
# the exact cards flattened by the old blanket solid-color snapshot payload.
AUTHORED_BASE_IDS = {
    "fo_lava_lamp",
    "cherry_polka",
    "tac_frozen_bank",
    "beetle_ground",
    "butterfly_swallowtail",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_renderer_zone_preserves_authored_base_paint_and_monolithic_color_contract():
    authored_fn = object()
    noop_fn = object()

    class FakeEngine:
        BASE_REGISTRY = {
            "authored": {"paint_fn": authored_fn},
            "foundation": {"paint_fn": noop_fn},
        }
        MONOLITHIC_REGISTRY = {"mono": {}}

        @staticmethod
        def _base_paint_fn_is_noop(fn):
            return fn is noop_fn

    authored = _renderer_zone(FakeEngine, "authored", "base")
    foundation = _renderer_zone(FakeEngine, "foundation", "base")
    monolithic = _renderer_zone(FakeEngine, "mono", "monolithic")

    assert authored["base_color_mode"] == "authored_swatch"
    assert foundation["base_color_mode"] == "source"
    assert monolithic["base_color_mode"] == "authored_swatch"


def test_thumbnail_writer_is_a_deterministic_literal_paint_spec_split(tmp_path: Path):
    yy, xx = np.mgrid[0:48, 0:64]
    paint = np.stack(
        ((xx * 7 + yy * 3) % 256, (xx * 2 + yy * 11) % 256, (xx + yy * 5) % 256),
        axis=2,
    ).astype(np.uint8)
    spec = np.stack(
        ((255 - xx * 3) % 256, (yy * 13) % 256, (xx * 9 + yy) % 256),
        axis=2,
    ).astype(np.uint8)
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    _write_thumbnail(paint, spec, first)
    _write_thumbnail(paint, spec, second)

    assert _sha256(first) == _sha256(second)
    with Image.open(first) as image:
        assert image.format == "PNG"
        assert image.size == THUMBNAIL_DIMENSIONS
        actual = np.asarray(image.convert("RGB"))
    assert np.array_equal(actual[:, :THUMBNAIL_TILE_SIZE], _square_field(paint))
    assert np.array_equal(actual[:, THUMBNAIL_TILE_SIZE:], _square_field(spec))


def test_shipping_thumbnail_inventory_is_complete_truthful_and_nonflat():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    finishes = manifest["finishes"]
    expected_ids = {item["id"] for item in finishes}
    visible_ids = {item["id"] for item in finishes if item.get("visible", True)}
    actual_ids = {path.stem for path in THUMBNAILS.glob("*.png")}

    assert len(visible_ids) == 29
    assert expected_ids - visible_ids == {"fs_core_emerald"}
    assert actual_ids == expected_ids

    hashes: dict[str, str] = {}
    for finish_id in sorted(expected_ids):
        snapshot_path = SNAPSHOTS / f"{finish_id}.npz"
        thumbnail_path = THUMBNAILS / f"{finish_id}.png"
        assert snapshot_path.is_file()
        with np.load(snapshot_path, allow_pickle=False) as payload:
            paint = np.asarray(payload["paint"], dtype=np.uint8)
            spec = np.asarray(payload["spec"], dtype=np.uint8)
        with Image.open(thumbnail_path) as image:
            assert image.format == "PNG"
            assert image.size == THUMBNAIL_DIMENSIONS
            thumbnail = np.asarray(image.convert("RGB"))

        left = thumbnail[:, :THUMBNAIL_TILE_SIZE]
        right = thumbnail[:, THUMBNAIL_TILE_SIZE:]
        assert np.array_equal(left, _square_field(paint)), finish_id
        assert np.array_equal(right, _square_field(spec)), finish_id
        assert float(thumbnail.std()) > 2.0, finish_id
        assert float(right.std()) > 2.0, finish_id
        if finish_id in AUTHORED_BASE_IDS:
            spatial_std = np.std(paint.astype(np.float32), axis=(0, 1))
            assert float(spatial_std.max()) > 2.0, finish_id
        hashes[finish_id] = _sha256(thumbnail_path)

    # A duplicate output would mean at least one card had silently fallen back
    # to another material's swatch or fields.
    assert len(set(hashes.values())) == len(expected_ids)
