"""Tests for USER IMPORTS ingest + registry."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from PIL import Image

from engine.paint_v2 import user_imports, user_imports_ingest
from engine.paint_v2.user_imports_paths import ID_PREFIX


@pytest.fixture
def ui_tmp_dir(monkeypatch, tmp_path, request):
    import shutil
    d = tmp_path / request.node.name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir()
    monkeypatch.setenv("SPB_USER_IMPORTS_DIR", str(d))
    return d


def test_slugify_prefix():
    assert user_imports_ingest.slugify("My Cool Paint!").startswith(ID_PREFIX)


def test_import_paint_auto_spec(ui_tmp_dir):
    paint = ui_tmp_dir / "upload.png"
    Image.new("RGB", (512, 512), (40, 80, 120)).save(paint)
    entry = user_imports_ingest.import_paint_files([("upload.png", paint)], display_name="Test Blue")
    assert entry["id"].startswith(ID_PREFIX)
    assert entry["spec_mode"].startswith("auto")
    assert "import_dna" in entry
    assert (ui_tmp_dir / f"{entry['id']}_spec.png").exists()


def test_dna_classify_neon(ui_tmp_dir):
    from engine.paint_v2.user_imports_spec_dna import classify_style_from_image
    img = Image.new("RGB", (256, 256))
    px = img.load()
    for y in range(256):
        for x in range(256):
            px[x, y] = (255, 20 + (x % 80), 180 + (y % 40))
    style, analysis = classify_style_from_image(img, "neon test")
    assert style in ("casino_neon", "acid_wash", "comic_pop", "abstract_gradient")


def test_reload_registers_monolithic(ui_tmp_dir):
    paint = ui_tmp_dir / "upload.png"
    Image.new("RGB", (256, 256), (200, 50, 50)).save(paint)
    entry = user_imports_ingest.import_paint_files([("upload.png", paint)], display_name="Red Plate")
    mono = user_imports.reload_user_imports()
    assert entry["id"] in mono
    spec, paint_fn = mono[entry["id"]]
    import numpy as np

    shape = (64, 64)
    mask = np.ones(shape, dtype=np.float32)
    p = np.full((64, 64, 3), 0.5, dtype=np.float32)
    out = paint_fn(p, shape, mask, 42, 1.0, np.zeros(shape, dtype=np.float32))
    assert out.shape == (64, 64, 3)
    s = spec(shape, mask, 42, 1.0)
    assert s.shape == (64, 64, 4)


def test_delete_entry(ui_tmp_dir):
    paint = ui_tmp_dir / "upload.png"
    Image.new("RGB", (128, 128), (10, 10, 10)).save(paint)
    entry = user_imports_ingest.import_paint_files([("upload.png", paint)], display_name="Delete Me")
    fid = entry["id"]
    assert user_imports_ingest.delete_entry(fid)
    assert not (ui_tmp_dir / f"{fid}.png").exists()
    manifest = json.loads((ui_tmp_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["entries"] == []


def test_import_pattern(ui_tmp_dir):
    src = ui_tmp_dir / "hex.png"
    Image.new("RGB", (400, 400), (200, 200, 50)).save(src)
    entry = user_imports_ingest.import_pattern_files([("hex.png", src)], display_name="Hex Grid")
    assert entry["kind"] == "pattern"
    assert (ui_tmp_dir / f"{entry['id']}_pattern.png").exists()
    patterns = user_imports.reload_user_imports()
    assert entry["id"] in user_imports._USER_PATTERNS


def test_rebake_dna_spec(ui_tmp_dir):
    paint = ui_tmp_dir / "upload.png"
    Image.new("RGB", (128, 128), (30, 60, 90)).save(paint)
    entry = user_imports_ingest.import_paint_files([("upload.png", paint)], display_name="Rebake Me")
    fid = entry["id"]
    first_style = entry["import_dna"]["style"]
    updated = user_imports_ingest.rebake_dna_spec(fid)
    assert updated["id"] == fid
    assert updated["import_dna"]["style"] == first_style
    assert "dna_rebaked" in updated
    assert (ui_tmp_dir / f"{fid}_spec.png").exists()


def test_engine_preview_rejects_non_ui():
    from engine.paint_v2.user_imports_engine_preview import render_engine_uv_bytes
    import pytest

    with pytest.raises(ValueError):
        render_engine_uv_bytes("not_ui_foo")


def test_style_override():
    from engine.paint_v2.user_imports_ingest import normalize_paint_image
    from engine.paint_v2.user_imports_spec_dna import bake_import_spec_dna
    from PIL import Image

    img = normalize_paint_image(Image.new("RGB", (256, 256), (80, 80, 80)))
    result = bake_import_spec_dna(img, "override test", style_override="metal_flake", run_gauntlet=False)
    assert result.analysis.style == "metal_flake"


def test_dna_style_catalog():
    from engine.paint_v2.user_imports_spec_dna import DNA_STYLES, get_dna_style_catalog

    catalog = get_dna_style_catalog()
    assert len(catalog) == len(DNA_STYLES)
    assert catalog[0]["id"] == DNA_STYLES[0]
    assert catalog[0]["label"]
    assert catalog[0]["description"]
    # metal_flake is no longer the last catalog entry (more styles were
    # appended after it, e.g. holo_serpent). Look it up by id rather than
    # by tail position so this still proves the metal_flake style is present
    # with a human label.
    metal_flake_entry = next(e for e in catalog if e["id"] == "metal_flake")
    assert "metal flake" in metal_flake_entry["label"].lower()


def test_preview_detail_urls(ui_tmp_dir):
    paint = ui_tmp_dir / "upload.png"
    Image.new("RGB", (128, 128), (80, 120, 200)).save(paint)
    entry = user_imports_ingest.import_paint_files([("upload.png", paint)], display_name="Detail Test")
    fid = entry["id"]
    urls = user_imports_ingest.build_saved_preview_urls(fid)
    assert urls["preview_paint"].endswith(f"/paint-image/{fid}")
    assert urls["preview_channels"]["r"].endswith(f"/channel-preview/{fid}/r")


def test_guest_designer_catalog():
    from engine.paint_v2.guest_designers import get_catalog_for_picker

    entries = get_catalog_for_picker()
    assert any(e["id"] == "gd_lyons_black_rainbow_holo_x" for e in entries)
    lyons = next(e for e in entries if e["id"] == "gd_lyons_black_rainbow_holo_x")
    assert "Lyons" in lyons["group"]


def test_preview_import_payload(ui_tmp_dir):
    paint = ui_tmp_dir / "upload.png"
    Image.new("RGB", (256, 256), (120, 60, 200)).save(paint)
    payload = user_imports_ingest.preview_import([("upload.png", paint)], display_name="Preview Grid")
    assert payload["preview"].startswith("data:image/png;base64,")
    assert payload["preview_paint"].startswith("data:image/png;base64,")
    assert payload["preview_spec"].startswith("data:image/png;base64,")
    ch = payload["preview_channels"]
    assert set(ch.keys()) == {"r", "g", "b"}
    for key in ch:
        assert ch[key].startswith("data:image/png;base64,")


def test_channel_preview_png(ui_tmp_dir):
    paint = ui_tmp_dir / "upload.png"
    Image.new("RGB", (128, 128), (200, 100, 50)).save(paint)
    entry = user_imports_ingest.import_paint_files([("upload.png", paint)], display_name="Channel Split")
    fid = entry["id"]
    png = user_imports_ingest.render_channel_preview_png(fid, "r", width=256)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_resolve_preview_image(ui_tmp_dir):
    paint = ui_tmp_dir / "upload.png"
    Image.new("RGB", (256, 256), (50, 100, 150)).save(paint)
    entry = user_imports_ingest.import_paint_files([("upload.png", paint)], display_name="Preview Path")
    fid = entry["id"]
    path = user_imports_ingest.resolve_preview_image(fid)
    assert path.exists()
    assert path.name == f"{fid}_preview.png"


def test_export_all_packs(ui_tmp_dir):
    import zipfile

    paint = ui_tmp_dir / "upload.png"
    Image.new("RGB", (128, 128), (90, 40, 120)).save(paint)
    user_imports_ingest.import_paint_files([("upload.png", paint)], display_name="Batch One")
    from engine.paint_v2.user_imports_paths import DROP_PACK_EXT

    out = ui_tmp_dir / "packs" / f"shokk_drop_batch{DROP_PACK_EXT}"
    user_imports_ingest.export_all_packs(out)
    assert out.exists()
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert any(n.startswith("packs/") and n.endswith(DROP_PACK_EXT) for n in names)


def test_import_spec_overlay(ui_tmp_dir):
    src = ui_tmp_dir / "scratches.png"
    Image.new("RGBA", (256, 256), (180, 90, 40, 255)).save(src)
    entry = user_imports_ingest.import_spec_overlay_files(
        [("scratches.png", src)],
        display_name="Scratches",
        spec_m=1.0,
        spec_r=0.5,
        spec_c=0.25,
    )
    assert entry["kind"] == "spec_overlay"
    assert entry["spec_channel_strengths"]["M"] == 1.0
    assert entry["spec_channel_strengths"]["R"] == 0.5
    assert entry["spec_channel_strengths"]["C"] == 0.25
    user_imports.reload_user_imports()
    assert entry["id"] in user_imports._USER_SPEC_OVERLAYS
    fn = user_imports._USER_SPEC_OVERLAYS[entry["id"]]
    import numpy as np
    arr = fn((64, 64), 42, 1.0)
    assert arr.shape == (64, 64, 3)
    assert float(arr[:, :, 0].mean()) > float(arr[:, :, 1].mean())
    assert float(arr[:, :, 1].mean()) > float(arr[:, :, 2].mean())


def test_update_spec_overlay_channels(ui_tmp_dir):
    src = ui_tmp_dir / "holo.png"
    Image.new("RGBA", (128, 128), (200, 120, 60, 255)).save(src)
    entry = user_imports_ingest.import_spec_overlay_files([("holo.png", src)], display_name="Holo")
    updated = user_imports_ingest.update_spec_overlay_channels(
        entry["id"], spec_m=0.8, spec_r=1.2, spec_c=0.0
    )
    assert updated["spec_channel_strengths"]["C"] == 0.0
    user_imports.reload_user_imports()
    fn = user_imports._USER_SPEC_OVERLAYS[entry["id"]]
    import numpy as np
    arr = fn((32, 32), 1, 1.0)
    assert arr.shape == (32, 32, 3)
    assert float(arr[:, :, 2].max()) == 0.0


def test_preview_spec_overlay_import(ui_tmp_dir):
    src = ui_tmp_dir / "overlay.png"
    Image.new("RGBA", (256, 256), (100, 150, 200, 255)).save(src)
    payload = user_imports_ingest.preview_spec_overlay_import(
        [("overlay.png", src)],
        display_name="Black Rainbow Holo X",
        spec_m=1.0,
        spec_r=1.0,
        spec_c=1.0,
    )
    assert payload["suggested_intent"] == "spec_overlay"
    assert payload["preview_spec"].startswith("data:image/png;base64,")
    assert set(payload["preview_channels"].keys()) == {"r", "g", "b"}


# --- FRACTURE loader-gate regression (SHOKK DROP loop 2026-08-09) -------------
# "FRACTURE the spec" shipped 2026-06-16 and never worked: the import path
# intentionally bakes NO <id>_spec.png (the spec is derived from the paint plate
# at render time by _spec_from_fracture), but the catalog loader required
# _spec.png for every spec_mode except metallic_roughness — so every fractured
# entry was skipped before it could reach the render path built for it, and the
# owner's own ui_mag01_2 vanished. These tests pin the contract from BOTH ends so
# it cannot silently die again.

def test_fracture_import_bakes_no_spec_png(ui_tmp_dir):
    """The import side must tag spec_mode=fractured and write no _spec.png."""
    paint = ui_tmp_dir / "upload.png"
    img = Image.new("RGB", (256, 256), (20, 20, 24))
    px = img.load()
    for y in range(256):          # some edges/graphics for FRACTURE to trace
        for x in range(256):
            if (x // 16 + y // 16) % 2 == 0:
                px[x, y] = (210, 40, 90)
    img.save(paint)
    entry = user_imports_ingest.import_paint_files(
        [("upload.png", paint)], display_name="Fracture Me", fracture=True
    )
    assert entry["spec_mode"] == "fractured"
    assert (ui_tmp_dir / f"{entry['id']}.png").exists(), "paint plate must exist"
    assert not (ui_tmp_dir / f"{entry['id']}_spec.png").exists(), (
        "FRACTURE must NOT bake a spec PNG — the spec is derived at render time"
    )


def test_fractured_entry_loads_without_spec_png(ui_tmp_dir):
    """THE REGRESSION: a fractured entry must reach the registry and render.

    If the loader ever re-adds a blanket _spec.png requirement, this fails.
    """
    import numpy as np

    paint = ui_tmp_dir / "upload.png"
    img = Image.new("RGB", (256, 256), (15, 18, 22))
    px = img.load()
    for y in range(256):
        for x in range(256):
            if abs(x - y) < 6 or abs(x + y - 256) < 6:
                px[x, y] = (240, 200, 60)
    img.save(paint)
    entry = user_imports_ingest.import_paint_files(
        [("upload.png", paint)], display_name="Fracture Load", fracture=True
    )
    fid = entry["id"]

    mono = user_imports.reload_user_imports()
    assert fid in mono, (
        "fractured entry was dropped by the catalog loader — the FRACTURE gate "
        "regressed (see engine/paint_v2/user_imports.py)"
    )
    assert fid in {e["id"] for e in user_imports.get_catalog_entries()}
    assert fid in user_imports.get_finish_ids()

    # And it must actually render the (M, R, Cc, A) contract, not just load.
    spec_fn, paint_fn = mono[fid]
    shape = (64, 64)
    mask = np.ones(shape, dtype=np.float32)
    s = spec_fn(shape, mask, 42, 1.0)
    assert s.shape == (64, 64, 4) and s.dtype == np.uint8
    # FRACTURE = near-chrome metal + maxed clearcoat (its own docstring's values).
    assert s[:, :, 0].mean() > 150, "M channel should read near-chrome"
    assert s[:, :, 2].mean() > 150, "Cc channel should read maxed-gloss"


def test_export_all_packs_ids_subset(ui_tmp_dir):
    """export_all_packs(ids=...) exports only those entries; None = everything."""
    import zipfile

    from engine.paint_v2.user_imports_paths import DROP_PACK_EXT

    ids = []
    for i, color in enumerate([(90, 40, 120), (40, 120, 90), (120, 90, 40)]):
        p = ui_tmp_dir / f"upload{i}.png"
        Image.new("RGB", (128, 128), color).save(p)
        ids.append(
            user_imports_ingest.import_paint_files(
                [(p.name, p)], display_name=f"Subset {i}"
            )["id"]
        )

    want = [ids[0], ids[2]]
    out = ui_tmp_dir / "packs" / f"subset{DROP_PACK_EXT}"
    user_imports_ingest.export_all_packs(out, ids=want)
    with zipfile.ZipFile(out) as zf:
        packed = {n for n in zf.namelist() if n.startswith("packs/")}
        manifest_ids = [e["id"] for e in json.loads(zf.read("manifest.json"))["entries"]]
    assert packed == {f"packs/{i}{DROP_PACK_EXT}" for i in want}
    assert manifest_ids == want, "subset manifest must carry only the requested ids"

    # Whole-library behaviour must be untouched when ids is omitted.
    out_all = ui_tmp_dir / "packs" / f"all{DROP_PACK_EXT}"
    user_imports_ingest.export_all_packs(out_all)
    with zipfile.ZipFile(out_all) as zf:
        assert len(json.loads(zf.read("manifest.json"))["entries"]) == 3

    with pytest.raises(ValueError):
        user_imports_ingest.export_all_packs(ui_tmp_dir / "packs" / f"e{DROP_PACK_EXT}", ids=[])
    with pytest.raises(FileNotFoundError):
        user_imports_ingest.export_all_packs(
            ui_tmp_dir / "packs" / f"b{DROP_PACK_EXT}", ids=["ui_not_a_real_id"]
        )
