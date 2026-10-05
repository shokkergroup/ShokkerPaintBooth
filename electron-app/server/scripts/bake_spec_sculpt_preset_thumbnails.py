#!/usr/bin/env python3
"""
Bake REALISTIC preview thumbnails for every Spec Sculpt preset.

The Spec Sculpt Lab (spec-sculpt.html) lists ~125 presets
(engine/spec_sculpt/presets.py :: SPEC_SCULPT_PRESETS) as NAMES ONLY — people
cannot SEE what each finish looks like. This script renders a true finish preview
for each preset and saves a 256px PNG so the picker can show a real thumbnail
next to every name.

WHAT CHANGED (2026-06-05)
-------------------------
The old bake saved ``spec_preview_png_data_urls(spec)["composite"]`` — that is the
M->red / Roughness->green / Clearcoat->blue spec-MAP visualization, NOT a finish.
Every thumbnail came out as a flat green/red channel map, which tells a buyer
nothing about how the finish actually looks. This bake now renders the SAME way
the rest of the Paint Booth renders a finish swatch: it runs the finish through
``engine.preview_render`` as a full-canvas zone over the real chevy-truck livery and
keeps ``paint_rgb`` — the ACTUAL realistic finish on the paint (exactly the left/
realistic half of every picker swatch; see server._render_picker_split_snapshot_bytes).

The original 125 presets are single catalog finishes. The 50 newer Designer
Fusion presets deliberately blend two finishes. Single-finish cards still use
the picker zone renderer; multi-finish cards blend both real rendered appearances
using the authored weights so a fusion never lies by showing only its first half.

PIPELINE (per preset):
    1. spec = scratch_spec_from_any_paint(tex, seed, catalog_stack=preset.catalog)
       (the generated Spec Sculpt spec — saved to a TEMP PNG; passed as
       import_spec_map for contract/future-proofing. NOTE: import_spec_map seeds the
       engine's spec OUTPUT only; the realistic paint_rgb look comes from the zone's
       finish paint_fn, which is what the picker swatch shows.)
    2a. single finish -> the regular picker zone renderer
    2b. fusion -> both source appearances combined by authored recipe weights
    4. thumbnail = paint_rgb resized to 256 -> thumbnails/spec_sculpt_presets/{id}.png

A fixed seed keeps every thumbnail deterministic and consistent with the live
preview/generate path for the same finish+seed.

USAGE
-----
    C:\\Python313\\python.exe -B scripts/bake_spec_sculpt_preset_thumbnails.py
    C:\\Python313\\python.exe -B scripts/bake_spec_sculpt_preset_thumbnails.py --only mirror_chrome,carbon_fiber
    C:\\Python313\\python.exe -B scripts/bake_spec_sculpt_preset_thumbnails.py --scale 0.4 --thumb 256

Output:
    thumbnails/spec_sculpt_presets/{preset_id}.png   (256px, served at
        /thumbnails/spec_sculpt_presets/{preset_id}.png via the existing
        immutable-cache static route in server_routes/asset_routes.py)
    thumbnails/spec_sculpt_presets/_manifest.json    (ids, sizes, timings, seed)
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "thumbnails" / "spec_sculpt_presets"
MANIFEST_PATH = OUT_DIR / "_manifest.json"

# Canonical reference livery — the same chevy truck paint the Paint Booth ships as
# its example. Rendering each finish over a REAL livery (not a flat swatch) makes the
# finish read the way it will on a car.
REF_PAINT_CANDIDATES = [
    ROOT / "assets" / "defaults" / "shokker_paint_booth_chevy_truck.psd",
    ROOT / "shokker_paint_booth_chevy_truck.psd",
    ROOT / "SPB Chevy Truck Starting Example PSD.psd",
    ROOT / "assets" / "defaults" / "blank_canvas_2048_white.tga",
]

# Fixed seed so thumbnails are deterministic AND match the engine's preview/generate
# path for the same finish+seed.
BAKE_SEED = 9101

# Default render scale fed to preview_render. ~0.4 of the loaded render size gives
# crisp thumbnail detail at low cost (each preset renders in well under a second).
DEFAULT_PREVIEW_SCALE = 0.4
# Resolution the reference paint is loaded at before preview_scale is applied.
DEFAULT_RENDER_SIZE = 720


def _resolve_reference_paint() -> Path:
    for cand in REF_PAINT_CANDIDATES:
        if cand.is_file():
            return cand
    raise FileNotFoundError(
        "No reference paint found. Tried: " + ", ".join(str(c) for c in REF_PAINT_CANDIDATES)
    )


def _finish_type_for(finish_id: str, base_reg: set, mono_reg: set) -> str:
    """Classify a catalog finish id the same way the picker does.

    Catalog finishes are BASE or MONOLITHIC registry entries (patterns are never
    catalog finishes — see engine/spec_sculpt/catalog_blend.normalize_catalog_stack).
    A base finish is dispatched as zone["base"]; a monolithic as zone["finish"].
    For ids in BOTH registries, prefer base (matches _catalog_swatch_zone_for_preview).
    """
    if finish_id in base_reg:
        return "base"
    if finish_id in mono_reg:
        return "monolithic"
    # Unknown -> let the engine try it as a base (it will no-op cleanly if missing).
    return "base"


def _paint_rgb_to_uint8(paint_rgb) -> np.ndarray:
    arr = paint_rgb
    if arr is None or not hasattr(arr, "shape") or arr.size == 0:
        raise RuntimeError("preview_render returned empty paint_rgb")
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    elif arr.shape[-1] > 3:
        arr = arr[:, :, :3]
    return arr


def main() -> int:
    ap = argparse.ArgumentParser(description="Bake realistic Spec Sculpt preset thumbnails.")
    ap.add_argument("--render", type=int, default=DEFAULT_RENDER_SIZE,
                    help=f"Reference paint load resolution (default {DEFAULT_RENDER_SIZE}).")
    ap.add_argument("--scale", type=float, default=DEFAULT_PREVIEW_SCALE,
                    help=f"preview_render preview_scale 0.05-1.0 (default {DEFAULT_PREVIEW_SCALE}).")
    ap.add_argument("--thumb", type=int, default=256, help="Output PNG size (default 256).")
    ap.add_argument("--only", default="", help="Comma-separated preset ids to (re)bake only.")
    ap.add_argument("--missing", action="store_true", help="Bake only presets whose PNG asset is missing.")
    ap.add_argument("--seed", type=int, default=BAKE_SEED, help="Fixed render seed.")
    args = ap.parse_args()

    preview_scale = max(0.05, min(1.0, float(args.scale)))

    # Import the live server so we reuse the EXACT zone builder + engine the picker
    # uses — guarantees these thumbnails render the same pixels as every other swatch.
    import server
    engine = server.engine
    from engine.spec_sculpt.core import load_paint_rgb_float01
    from engine.spec_sculpt.generate import scratch_spec_from_any_paint
    from engine.spec_sculpt.presets import SPEC_SCULPT_PRESETS
    from engine.spec_sculpt.sun_sweep import derive_micro_normal, relight_frame
    from engine.registry import BASE_REGISTRY, MONOLITHIC_REGISTRY

    base_reg = set(BASE_REGISTRY.keys())
    mono_reg = set(MONOLITHIC_REGISTRY.keys())

    # [SPB-SPEC-SCULPT 2026-06-05] Render each finish on a CLEAN neutral swatch (gray 0.533),
    # exactly like regular SPB bakes its picker swatches — so the thumbnail shows JUST THE LOOK,
    # not a car model. (Owner: "it's baking in one of the car models. It should JUST be the look.")
    # paint_rgb (the visible thumbnail) comes from the zone finish paint_fn, so a neutral swatch
    # reads the finish's true character with nothing else in the frame.
    canvas = int(args.render)
    # Subtle vertical gradient (bright top -> dark bottom), neutral/no tint: gives metallics
    # something to reflect so chrome/carbon read as polished metal instead of flat gray, while
    # colored finishes stay true. No car model, still "just the look".
    _col = np.linspace(0.82, 0.26, canvas, dtype=np.float32).reshape(canvas, 1)
    _gray2d = np.broadcast_to(_col, (canvas, canvas))
    tex = np.stack([_gray2d, _gray2d, _gray2d], axis=2).astype(np.float32)
    orig_hw = (canvas, canvas)
    final_hw = (canvas, canvas)
    print(f"[ss-bake] render={args.render}  scale={preview_scale}  thumb={args.thumb}  seed={args.seed}")
    print(f"[ss-bake] clean neutral swatch {canvas}x{canvas} (no car model)")

    only = {x.strip() for x in args.only.split(",") if x.strip()} if args.only else None
    presets = [p for p in SPEC_SCULPT_PRESETS if (only is None or p["id"] in only)]
    if args.missing:
        presets = [p for p in presets if not (OUT_DIR / f"{p['id']}.png").is_file()]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[ss-bake] output -> {OUT_DIR}")
    print(f"[ss-bake] {len(presets)} preset(s) to bake\n")

    # Render the reference paint to a real PNG file once (preview_render needs a path).
    tmp_dir = Path(tempfile.mkdtemp(prefix="ss_bake_"))
    ref_paint_png = str(tmp_dir / "ref_paint.png")
    Image.fromarray((np.clip(tex, 0.0, 1.0) * 255.0).astype(np.uint8)).save(ref_paint_png)

    manifest = []
    baked = 0
    failed = 0
    t_start = time.perf_counter()

    try:
        for i, p in enumerate(presets, 1):
            pid = str(p["id"])
            catalog = [(str(f[0]), float(f[1])) for f in p.get("catalog", [])]
            t0 = time.perf_counter()
            spec_png = None
            try:
                if not catalog:
                    raise RuntimeError("preset has no catalog finish")
                finish_id = catalog[0][0]
                ftype = _finish_type_for(finish_id, base_reg, mono_reg)

                # (1) generate the Spec Sculpt spec for this finish (catalog path,
                # same call /api/spec-sculpt/batch uses) and write to a TEMP PNG.
                spec = scratch_spec_from_any_paint(
                    tex,
                    seed=int(args.seed),
                    chromatic_shift=bool(p.get("uses_chromatic", True)),
                    catalog_stack=catalog,
                )
                spec_png = str(tmp_dir / f"{pid}_spec.png")
                Image.fromarray(spec, mode="RGBA").save(spec_png)

                # (2) build the finish zone exactly like the picker swatch bake.
                zone = server._catalog_swatch_zone_for_preview(
                    ftype, finish_id, 0.533, 0.533, 0.533, canvas
                )

                # (3) render the REALISTIC finish on the livery. paint_rgb is the
                # actual finish-on-paint (the realistic swatch the Booth shows).
                # Render the finish's NATURAL look on the clean swatch (NO import_spec_map —
                # passing the generated spec here overrides the finish's own spec and flattens
                # metallics to dull gray). This matches the vibrant Pick-a-look grid + regular
                # SPB picker swatches.
                paint_rgb, _spec_out, _ms = engine.preview_render(
                    ref_paint_png,
                    [zone],
                    seed=int(args.seed),
                    preview_scale=preview_scale,
                )
                paint_rgb = _paint_rgb_to_uint8(paint_rgb)

                if len(catalog) > 1:
                    # A Designer Fusion has no single truthful zone renderer.
                    # Render every authored source finish, then combine those
                    # appearances using the exact preset weights. This preserves
                    # the color and micro-pattern identity of both halves.
                    layers = [np.asarray(paint_rgb, dtype=np.float32)]
                    weights = [max(0.0, float(catalog[0][1]))]
                    for layer_id, layer_weight in catalog[1:]:
                        layer_type = _finish_type_for(layer_id, base_reg, mono_reg)
                        layer_zone = server._catalog_swatch_zone_for_preview(
                            layer_type, layer_id, 0.533, 0.533, 0.533, canvas
                        )
                        layer_rgb, _layer_spec, _layer_ms = engine.preview_render(
                            ref_paint_png,
                            [layer_zone],
                            seed=int(args.seed),
                            preview_scale=preview_scale,
                        )
                        layers.append(np.asarray(_paint_rgb_to_uint8(layer_rgb), dtype=np.float32))
                        weights.append(max(0.0, float(layer_weight)))
                    weight_total = sum(weights) or float(len(weights))
                    paint_rgb = _paint_rgb_to_uint8(sum(
                        layer * (weight / weight_total) for layer, weight in zip(layers, weights)
                    ))
                    # Modulate the weighted paint appearance with the exact
                    # combined M/R/CC response. This preserves authored color
                    # while bringing back fusion-only microstructure that neither
                    # source paint render can show by itself.
                    ph, pw = paint_rgb.shape[:2]
                    tex_small = np.asarray(
                        Image.fromarray((tex * 255.0).astype(np.uint8)).resize((pw, ph), Image.LANCZOS),
                        dtype=np.float32,
                    ) / 255.0
                    spec_small = np.asarray(
                        Image.fromarray(spec, mode="RGBA").resize((pw, ph), Image.NEAREST),
                        dtype=np.uint8,
                    )
                    normal = derive_micro_normal(tex_small, spec_small, seed=int(args.seed))
                    material_light = np.asarray(
                        relight_frame(tex_small, spec_small, normal, (0.34, 0.46, 0.82), ambient=0.22),
                        dtype=np.float32,
                    ).mean(axis=2)
                    material_mean = max(1e-4, float(material_light.mean()))
                    response = np.clip(1.0 + 0.42 * (material_light / material_mean - 1.0), 0.62, 1.38)
                    paint_rgb = _paint_rgb_to_uint8(np.asarray(paint_rgb, np.float32) * response[..., None])
                    finish_id = " + ".join(fid for fid, _weight in catalog)
                    ftype = "fusion"

                # (4) thumbnail.
                img = Image.fromarray(paint_rgb)
                if img.size != (args.thumb, args.thumb):
                    img = img.resize((args.thumb, args.thumb), Image.LANCZOS)
                out_path = OUT_DIR / f"{pid}.png"
                img.save(out_path, format="PNG", optimize=True)

                dt = time.perf_counter() - t0
                baked += 1
                manifest.append({
                    "id": pid,
                    "label": p.get("label", pid),
                    "category": p.get("category", ""),
                    "finish_id": finish_id,
                    "finish_type": ftype,
                    "file": f"spec_sculpt_presets/{pid}.png",
                    "bytes": out_path.stat().st_size,
                    "ms": round(dt * 1000.0, 1),
                })
                if i <= 5 or i % 20 == 0 or i == len(presets):
                    print(f"  [{i:3d}/{len(presets)}]  {dt:4.1f}s  {pid:32s} "
                          f"{ftype:10s} {out_path.stat().st_size:>7d}B")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"  [{i:3d}/{len(presets)}]  FAIL  {pid}: {exc}")
            finally:
                if spec_png:
                    try:
                        Path(spec_png).unlink()
                    except Exception:
                        pass
    finally:
        try:
            Path(ref_paint_png).unlink()
        except Exception:
            pass
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    total = time.perf_counter() - t_start
    if (only or args.missing) and MANIFEST_PATH.is_file():
        try:
            previous = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            merged = {str(row.get("id")): row for row in previous.get("thumbs", []) if row.get("id")}
            merged.update({str(row.get("id")): row for row in manifest if row.get("id")})
            manifest = list(merged.values())
        except Exception:
            pass

    payload = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "reference_paint": "clean_swatch_neutral_0.533",
        "render_size": args.render,
        "preview_scale": preview_scale,
        "thumb_size": args.thumb,
        "seed": int(args.seed),
        "preview": "realistic_finish",  # paint_rgb from engine.preview_render (NOT spec channel-viz)
        "count": len(manifest),
        "run_count": baked,
        "failed": failed,
        "wall_seconds": round(total, 1),
        "route": "/thumbnails/spec_sculpt_presets/{id}.png",
        "thumbs": manifest,
    }
    MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print()
    print(f"[ss-bake] DONE. baked={baked} failed={failed} in {total:.1f}s")
    print(f"[ss-bake] manifest -> {MANIFEST_PATH}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
