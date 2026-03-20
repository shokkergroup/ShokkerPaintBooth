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
import json
import os
import sys
import tempfile

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


def main():
    ap = argparse.ArgumentParser(description="Rebuild thumbnails via full render pipeline")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE, help="Thumbnail width/height (default 128)")
    ap.add_argument("--output", type=str, default=DEFAULT_OUTPUT, help="Output dir for thumbnails (default: V5/thumbnails)")
    ap.add_argument("--type", choices=("base", "pattern", "monolithic", "all"), default="all", help="Which registry to build")
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

    expected_total = len(BASE_REGISTRY) + len(PATTERN_REGISTRY) + len(MONOLITHIC_REGISTRY)
    print(f"Registries (V5): {len(BASE_REGISTRY)} bases, {len(PATTERN_REGISTRY)} patterns, {len(MONOLITHIC_REGISTRY)} monolithics -> {expected_total} thumbnails expected")

    out_root = os.path.abspath(args.output)
    os.makedirs(out_root, exist_ok=True)
    print(f"Output directory (absolute): {out_root}")

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
