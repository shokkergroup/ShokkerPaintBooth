"""SHOKK THE WORLD contact-sheet / A-B QA tool.

Renders the EXACT Spec Sculpt "Shokk the World" gallery (source paint + N look
composites) to a single PNG, computed FUNCTION-LEVEL from the on-disk engine code —
so you can visually A/B a change to engine/spec_sculpt/ WITHOUT restarting the server
(the live /api/spec-sculpt/batch only reflects code loaded at the server's last restart).

Why this exists (SPB-SPEC-SCULPT, 2026-06-02, iteration 8): the batch "composite" preview
is literally np.stack([metallic, roughness, clearcoat]) (engine/spec_sculpt/preview.py).
Earlier function-level sheets looked wrong because they used the engine's DEFAULT emphasis
instead of the batch's explicit per-look emphasis. This tool replicates the batch pipeline
in server.py::api_spec_sculpt_batch EXACTLY:
    var_seed   = base_seed + i*17
    emphasis   = [highlights, saturated, shadows, highlights, desaturated][i % 5]
    spec       = scratch_spec_from_any_paint(tex, seed=var_seed, chromatic_shift=True,
                                             catalog_stack=cat, paint_emphasis=emphasis,
                                             paint_emphasis_strength=0.5)
    composite  = stack(spec[...,0], spec[...,1], spec[...,2])
Validated against the live batch: mean|pixel diff| ~15/255 (server warm noise-cache vs a
fresh process); visually identical.

NEVER deploys / never calls /generate. Recipes come from the live GET /api/spec-sculpt/world
when reachable (matches the gallery's star-weighted picks exactly), else pick_diverse locally.

Usage:
    python scripts/spec_sculpt_world_contact_sheet.py [--out PATH] [--paint PATH]
        [--seed 9101] [--n 24] [--compare-live]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

EMPH = ("highlights", "saturated", "shadows", "highlights", "desaturated")
DEFAULT_PAINT = os.path.join("assets", "defaults", "shokker_paint_booth_chevy_truck.psd")
SERVER = "http://localhost:59876"


def _world_recipes(seed: int, n: int):
    """Exact gallery recipes from the live server (star-weighted); fall back to local pick."""
    try:
        url = f"{SERVER}/api/spec-sculpt/world?seed={seed}&n={n}"
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.load(r)
        if d.get("success") and d.get("recipes"):
            return d["recipes"], "live /world"
    except Exception:
        pass
    from engine.spec_sculpt.spec_index import pick_diverse
    picks = pick_diverse(n, seed=int(seed))
    return [{"label": p["name"], "catalog": [[p["id"], 1.0]]} for p in picks], "local pick_diverse (no star_ids)"


def _live_composites(paint: str, seed: int):
    """Decode the running batch's composite previews (for --compare-live), keyed by label."""
    body = json.dumps({"paint_file": paint, "seed": seed, "chromatic_shift": True}).encode()
    req = urllib.request.Request(f"{SERVER}/api/spec-sculpt/batch", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    out = {}
    for v in d.get("variations", []):
        u = v["previews"]["composite"]
        out[v["label"]] = np.asarray(Image.open(io.BytesIO(
            __import__("base64").b64decode(u.split(",", 1)[1]))).convert("RGB")).astype(np.int16)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("_perf", "shokk_world_contact.png"))
    ap.add_argument("--paint", default=DEFAULT_PAINT)
    ap.add_argument("--seed", type=int, default=9101)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--size", type=int, default=320)
    ap.add_argument("--compare-live", action="store_true")
    args = ap.parse_args()

    from engine.spec_sculpt.core import load_paint_rgb_float01
    from engine.spec_sculpt.generate import scratch_spec_from_any_paint
    from engine.spec_sculpt.catalog_blend import normalize_catalog_stack

    paint = os.path.abspath(args.paint)
    if not os.path.isfile(paint):
        print(f"paint not found: {paint}")
        return 2
    recipes, src = _world_recipes(args.seed, args.n)
    print(f"recipes from: {src}  ({len(recipes)} looks)")
    tex, _, _ = load_paint_rgb_float01(paint, target_size=args.size)

    live = _live_composites(paint, args.seed) if args.compare_live else None
    diffs = []
    tiles = [("SOURCE PAINT", "", Image.fromarray((np.clip(tex, 0, 1) * 255).astype("uint8")))]
    for i, rec in enumerate(recipes[: args.n]):
        cat = normalize_catalog_stack(rec.get("catalog"))
        if not cat:
            continue
        var_seed = (int(args.seed) + i * 17) & 0xFFFFFFFF
        spec = scratch_spec_from_any_paint(tex, seed=var_seed, chromatic_shift=True,
                                           catalog_stack=cat, paint_emphasis=EMPH[i % 5],
                                           paint_emphasis_strength=0.5)
        comp = np.stack([spec[:, :, 0], spec[:, :, 1], spec[:, :, 2]], axis=2).astype(np.uint8)
        lab = str(rec.get("label", f"Look {i+1}"))[:30]
        fid = str((rec.get("catalog") or [["?"]])[0][0])  # finish id -> paste into world_denylist.json to curate
        if live is not None and lab in live and live[lab].shape == comp.shape:
            diffs.append(float(np.abs(comp.astype(np.int16) - live[lab]).mean()))
        tiles.append((lab, fid, Image.fromarray(comp, "RGB")))

    cols = 5
    cell, lh = 252, 32  # taller label bar: line 1 = pretty name, line 2 = finish id (for denylist curation)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + lh)), (16, 16, 20))
    draw = ImageDraw.Draw(sheet)
    for i, (lab, fid, img) in enumerate(tiles):
        x, y = (i % cols) * cell, (i // cols) * (cell + lh)
        draw.rectangle([x, y, x + cell - 2, y + lh - 1], fill=(40, 40, 52))
        draw.text((x + 4, y + 2), lab, fill=(255, 210, 90) if i == 0 else (210, 210, 225))
        if fid:
            draw.text((x + 4, y + 17), fid[:42], fill=(120, 200, 255))  # the id to copy into world_denylist.json
        sheet.paste(img.resize((cell - 4, cell - 4)), (x + 2, y + lh))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    sheet.save(os.path.abspath(args.out))
    print(f"SAVED {os.path.abspath(args.out)}  {sheet.size}  ({len(tiles)-1} looks)")
    if diffs:
        print(f"vs LIVE batch: mean|diff|={np.mean(diffs):.2f}/255 (0=exact; ~15 = warm noise-cache)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
