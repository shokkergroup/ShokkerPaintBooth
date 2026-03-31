"""
Rebuild all thumbnails using the full render pipeline.

Uses build_multi_zone at small size (default 128x128) so every finish
is rendered the same way as in-app.

You can run this by double-clicking in Windows Explorer - the script uses
its own file location to find the V5 folder and write thumbnails there.
For a visible result, double-click rebuild_thumbnails.bat instead (keeps
the window open).

From CMD/PowerShell (from V5 folder):
  python rebuild_thumbnails.py
  python rebuild_thumbnails.py --size 256
  python rebuild_thumbnails.py --type base
  python rebuild_thumbnails.py --type monolithic --key chameleon_arctic

Output: thumbnails/<base|pattern|monolithic>/<key>.png
Manifest: thumbnails/rebuild_manifest.json (ok + failed keys)
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime

# Run from V5 root so engine and config are importable
V5_ROOT = os.path.dirname(os.path.abspath(__file__))
if V5_ROOT not in sys.path:
    sys.path.insert(0, V5_ROOT)

# Default thumbnail size and output dir (config overrides if present)
DEFAULT_SIZE = 128
DEFAULT_OUTPUT = os.path.join(V5_ROOT, "thumbnails")


def safe_key(key):
    """Filename-safe key (no path chars)."""
    if not key:
        return "none"
    return str(key).replace("/", "_").replace("\\", "_").replace(":", "_").strip() or "none"


def make_zone_for_finish(finish_type, finish_key, default_base="living_matte"):
    """Build a single zone that covers full canvas (remaining) with the given finish."""
    if finish_type == "base":
        return {
            "name": f"Thumb-{finish_key}",
            "color": "remaining",
            "base": finish_key,
            "pattern": "none",
            "intensity": "100",
        }
    if finish_type == "pattern":
        return {
            "name": f"Thumb-{finish_key}",
            "color": "remaining",
            "base": default_base,
            "pattern": finish_key,
            "intensity": "100",
        }
    if finish_type == "monolithic":
        zone = {
            "name": f"Thumb-{finish_key}",
            "color": "remaining",
            "finish": finish_key,
            "intensity": "100",
        }
        # So gradient/ghost/mirror/3c/mc thumbnails use accurate colors (not generic)
        try:
            from finish_colors_lookup import get_finish_colors
            fc = get_finish_colors(finish_key)
            if fc:
                zone["finish_colors"] = fc
        except Exception:
            pass
        return zone
    raise ValueError(f"Unknown finish_type: {finish_type}")


def _get_fn_hash(fn):
    """Get a short MD5 hash of a function's source code for change detection."""
    try:
        import inspect
        src = inspect.getsource(fn)
        return hashlib.md5(src.encode()).hexdigest()[:12]
    except Exception:
        return "unknown"


def _generate_spec_preview_image_standalone(pattern_id, fn):
    """Generate 192x64 3-panel M/R/CC preview. Returns PIL Image."""
    import numpy as np
    from PIL import Image as _PILImage, ImageDraw as _ImageDraw

    shape = (64, 64)
    try:
        arr = fn(shape, 42, 1.0)
    except Exception as e:
        print(f"  WARN spec preview error {pattern_id}: {e}")
        return _PILImage.new('RGBA', (192, 64), (40, 40, 40, 255))

    arr = np.clip(arr, 0, 1).astype(np.float32)
    m_gray = (arr * 255).astype(np.uint8)
    r_gray = m_gray.copy()
    cc_gray = (255 - arr * 255).astype(np.uint8)

    out = np.zeros((64, 192, 4), dtype=np.uint8)
    out[:, 0:64, 0] = m_gray; out[:, 0:64, 1] = m_gray; out[:, 0:64, 2] = m_gray; out[:, 0:64, 3] = 255
    out[:, 64, :] = [30, 30, 30, 255]
    out[:, 65:129, 0] = r_gray; out[:, 65:129, 1] = r_gray; out[:, 65:129, 2] = r_gray; out[:, 65:129, 3] = 255
    out[:, 129, :] = [30, 30, 30, 255]
    out[:, 130:194, 0] = cc_gray; out[:, 130:194, 1] = cc_gray; out[:, 130:194, 2] = cc_gray; out[:, 130:194, 3] = 255

    img = _PILImage.fromarray(out, 'RGBA')
    draw = _ImageDraw.Draw(img)
    for label, x in [('M', 2), ('R', 67), ('CC', 132)]:
        draw.text((x + 1, 54), label, fill=(0, 0, 0, 200))
        draw.text((x, 53), label, fill=(255, 255, 255, 220))
    return img


def _generate_spec_metal_image_standalone(pattern_id, fn):
    """Generate 128x128 metallic surface simulation. Returns PIL Image."""
    import numpy as np
    from PIL import Image as _PILImage

    shape = (128, 128)
    try:
        arr = fn(shape, 42, 1.0)
    except Exception as e:
        print(f"  WARN spec metal error {pattern_id}: {e}")
        return _PILImage.new('RGBA', (128, 128), (60, 60, 60, 255))

    arr = np.clip(arr, 0, 1).astype(np.float32)
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    base_lighting = np.clip(1.0 - (xx / w * 0.4 + yy / h * 0.3), 0.2, 1.0)
    specular_sharpness = 1.0 - arr * 0.8
    ambient = 0.25
    final_lum = np.clip(base_lighting * arr * specular_sharpness + ambient * (1.0 - arr), 0, 1)
    r_ch = np.clip(final_lum * 0.88 + 0.06, 0, 1)
    g_ch = np.clip(final_lum * 0.92 + 0.04, 0, 1)
    b_ch = np.clip(final_lum * 1.05 + 0.02, 0, 1)

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, 0] = (r_ch * 255).astype(np.uint8)
    rgba[:, :, 1] = (g_ch * 255).astype(np.uint8)
    rgba[:, :, 2] = (b_ch * 255).astype(np.uint8)
    rgba[:, :, 3] = 255
    return _PILImage.fromarray(rgba, 'RGBA')


def _rebuild_spec_patterns(args, out_root):
    """Rebuild spec overlay pattern thumbnails (M/R/CC preview + metal sim)."""
    try:
        from engine.spec_patterns import PATTERN_CATALOG
    except ImportError as e:
        print(f"  ERROR: Cannot import PATTERN_CATALOG: {e}", file=sys.stderr)
        return

    spec_dir = os.path.join(out_root, 'spec_patterns')
    spec_metal_dir = os.path.join(out_root, 'spec_patterns_metal')
    os.makedirs(spec_dir, exist_ok=True)
    os.makedirs(spec_metal_dir, exist_ok=True)

    # Load manifest for hash-based skip
    manifest_path = os.path.join(out_root, '_manifest.json')
    manifest = {"version": 2, "spec_patterns": {}, "bases": {}, "patterns": {}, "monolithics": {}}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
        except Exception:
            pass
    sp_manifest = manifest.get('spec_patterns', {})

    pattern_items = list(PATTERN_CATALOG.items())
    # Filter to specific key if --key provided
    if args.key:
        pattern_items = [(k, v) for k, v in pattern_items if k == args.key]

    total = len(pattern_items)
    print(f"Spec pattern thumbnails: {total} patterns -> {spec_dir}")
    generated = 0
    skipped = 0
    errors = 0

    for i, (pattern_id, fn) in enumerate(pattern_items):
        thumb_path = os.path.join(spec_dir, f"{pattern_id}.png")
        metal_path = os.path.join(spec_metal_dir, f"{pattern_id}.png")
        current_hash = _get_fn_hash(fn)
        cached_entry = sp_manifest.get(pattern_id, {})

        # Skip if both exist and hash matches
        if (os.path.exists(thumb_path) and os.path.exists(metal_path)
                and cached_entry.get('hash') == current_hash
                and not args.key):  # Always regen when specific key requested
            skipped += 1
            continue

        pct = int(100 * (i + 1) / total) if total else 0
        if not args.quiet:
            if (i + 1) % max(1, total // 10) == 0 or i == 0 or i == total - 1:
                print(f"  [{pct:3d}%] {i + 1}/{total} - spec/{pattern_id}")
        try:
            img = _generate_spec_preview_image_standalone(pattern_id, fn)
            img.save(thumb_path)
            metal_img = _generate_spec_metal_image_standalone(pattern_id, fn)
            metal_img.save(metal_path)
            sp_manifest[pattern_id] = {
                'hash': current_hash,
                'generated': datetime.utcnow().isoformat()
            }
            generated += 1
        except Exception as e:
            errors += 1
            print(f"  FAIL spec/{pattern_id}: {e}")

    manifest['spec_patterns'] = sp_manifest
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    print(f"Spec thumbnails done: {generated} generated, {skipped} cached, {errors} errors. Manifest: {manifest_path}")


def main():
    ap = argparse.ArgumentParser(description="Rebuild thumbnails via full render pipeline")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE, help="Thumbnail width/height (default 128)")
    ap.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="Output dir for thumbnails (default: V5/thumbnails)")
    ap.add_argument("--type", choices=("base", "pattern", "monolithic", "spec", "all"), default="all", help="Which registry to build (spec = spec overlay patterns)")
    ap.add_argument("--key", type=str, default=None, help="Build only this key (requires --type)")
    ap.add_argument("--quiet", action="store_true", help="Less console output")
    args = ap.parse_args()

    try:
        from PIL import Image
        import numpy as np
        # Use same registries as server_v5 so every finish the UI can show gets a thumbnail
        from engine.registry import BASE_REGISTRY, PATTERN_REGISTRY, MONOLITHIC_REGISTRY
        import shokker_engine_v2 as _legacy
        _legacy.BASE_REGISTRY = BASE_REGISTRY
        _legacy.PATTERN_REGISTRY = PATTERN_REGISTRY
        _legacy.MONOLITHIC_REGISTRY = MONOLITHIC_REGISTRY
        build_multi_zone = _legacy.build_multi_zone
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Run from Shokker Paint Booth V5 folder with dependencies installed.", file=sys.stderr)
        sys.exit(1)

    out_root = os.path.abspath(args.output)
    os.makedirs(out_root, exist_ok=True)
    print(f"Output directory (absolute): {out_root}")

    # Spec pattern generation (handled separately from base/pattern/monolithic pipeline)
    if args.type in ('all', 'spec'):
        _rebuild_spec_patterns(args, out_root)
        if args.type == 'spec':
            return  # Only spec requested — skip base/pattern/monolithic rebuild

    expected_total = len(BASE_REGISTRY) + len(PATTERN_REGISTRY) + len(MONOLITHIC_REGISTRY)
    print(f"Registries (V5): {len(BASE_REGISTRY)} bases, {len(PATTERN_REGISTRY)} patterns, {len(MONOLITHIC_REGISTRY)} monolithics -> {expected_total} thumbnails expected")

    # Monolithic multi-color and patterns need larger canvas (256/512) so noise/tiling shows properly at scale before downsampling
    def _render_size_for_task(ftype):
        if ftype == "pattern":
            return max(args.size, 512)  # Give patterns a large canvas so details tile correctly
        return max(args.size, 256) if ftype == "monolithic" else args.size

    # Single gray source - we'll recreate at correct size per task when mixing base/pattern/mono
    with tempfile.TemporaryDirectory(prefix="shokker_thumb_") as tmp:
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir, exist_ok=True)

        manifest = {"ok": [], "fail": []}
        tasks = []

        if args.type == "all":
            for key in sorted(BASE_REGISTRY.keys()):
                tasks.append(("base", key))
            for key in sorted(PATTERN_REGISTRY.keys()):
                if key and key != "none":
                    tasks.append(("pattern", key))
            for key in sorted(MONOLITHIC_REGISTRY.keys()):
                tasks.append(("monolithic", key))
        elif args.type and args.key:
            tasks = [(args.type, args.key)]
        else:
            reg = {"base": BASE_REGISTRY, "pattern": PATTERN_REGISTRY, "monolithic": MONOLITHIC_REGISTRY}.get(args.type)
            if reg:
                for key in sorted(reg.keys()):
                    tasks.append((args.type, key))
            else:
                tasks = []

        if not tasks:
            print("No keys to build.")
            return

        print(f"Building {len(tasks)} thumbnails -> {out_root} (monolithic at 256px, others at {args.size}px)")
        total = len(tasks)
        for i, (finish_type, finish_key) in enumerate(tasks):
            pct = int(100 * (i + 1) / total) if total else 0
            if not args.quiet:
                # Progress every 10% or every 25 items, whichever is more frequent
                if (i + 1) % max(1, total // 10) == 0 or (i + 1) % 25 == 0 or i == 0 or i == total - 1:
                    print(f"  [{pct:3d}%] {i + 1}/{total} - {finish_type}/{finish_key}")
            rsize = _render_size_for_task(finish_type)
            source_png = os.path.join(tmp, f"thumb_src_{rsize}.png")
            if not os.path.exists(source_png):
                gray = np.full((rsize, rsize, 3), 0x88, dtype=np.uint8)
                Image.fromarray(gray).save(source_png)
            zone = make_zone_for_finish(finish_type, finish_key)
            zones = [zone]
            try:
                paint_rgb, _, _ = build_multi_zone(
                    source_png, out_dir, zones,
                    iracing_id="23371", seed=42,
                    save_debug_images=False,
                )
                subdir = os.path.join(out_root, finish_type)
                os.makedirs(subdir, exist_ok=True)
                path = os.path.join(subdir, f"{safe_key(finish_key)}.png")
                if paint_rgb.shape[0] != args.size or paint_rgb.shape[1] != args.size:
                    from PIL import Image as PILImage
                    img = PILImage.fromarray(paint_rgb)
                    img = img.resize((args.size, args.size), PILImage.LANCZOS)
                    img.save(path)
                else:
                    Image.fromarray(paint_rgb).save(path)
                manifest["ok"].append(f"{finish_type}/{finish_key}")
            except Exception as e:
                manifest["fail"].append({"key": f"{finish_type}/{finish_key}", "error": str(e)})
                if not args.quiet:
                    print(f"  FAIL {finish_type}/{finish_key}: {e}")

        manifest_path = os.path.join(out_root, "rebuild_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        n_ok, n_fail = len(manifest["ok"]), len(manifest["fail"])
        print(f"Done. OK: {n_ok}, Failed: {n_fail}. Expected: {expected_total}. Manifest: {manifest_path}")
        if n_fail > 0:
            print(f"Failed keys (re-run with --type and --key to retry):")
            for entry in manifest["fail"][:20]:
                print(f"  {entry.get('key', entry)}: {entry.get('error', '')[:60]}")
            if n_fail > 20:
                print(f"  ... and {n_fail - 20} more (see {manifest_path})")
        if manifest["ok"]:
            first_ok = manifest["ok"][0]
            ft, fk = first_ok.split("/", 1)
            first_path = os.path.join(out_root, ft, safe_key(fk) + ".png")
            print(f"First PNG: {os.path.abspath(first_path)} (server uses same dir when run from V5)")


if __name__ == "__main__":
    main()
