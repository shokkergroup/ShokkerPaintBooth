# -*- coding: utf-8 -*-
"""Sun Sweep HERO GIF generator — turn catalog finishes into shareable, looping angle-flash showcases.
Renders each finish to paint+spec via the SAME unified path the server route uses, sweeps a virtual sun,
and writes a smooth PING-PONG GIF per finish + a contact-sheet montage. No server, no restart needed.

Usage: py -3 scripts/sunsweep_hero_gifs.py [id1,id2,...]   (default = curated spatially-colourful set)
"""
import os, sys, importlib.util, time
import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "electron-app", "server"))
OUTDIR = os.path.join(ROOT, "_reworks_2026", "hero_gifs")
os.makedirs(OUTDIR, exist_ok=True)

# Curated finishes whose ALBEDO varies spatially in colour -> Sun Sweep makes colour TRAVEL (best wow).
DEFAULT_IDS = [
    "optics2_thinfilm", "optics2_holo", "optics2_dvd", "optics2_aurora",
    "materials2_titanium", "materials2_crystal",
    "grd_iridescent", "grd_holo_foil",
]

_ss_spec = importlib.util.spec_from_file_location("sun_sweep", os.path.join(ROOT, "engine", "spec_sculpt", "sun_sweep.py"))
ss = importlib.util.module_from_spec(_ss_spec); _ss_spec.loader.exec_module(ss)


def render_paint_spec(reg, normalize, finish_id, size):
    entry = reg.get(finish_id)
    if entry is None:
        return None, None
    if isinstance(entry, (tuple, list)) and len(entry) >= 2:
        spec_fn, paint_fn = entry[0], entry[1]
    elif isinstance(entry, dict):
        spec_fn, paint_fn = entry.get("spec_fn"), entry.get("paint_fn")
    else:
        return None, None
    if not callable(spec_fn) or not callable(paint_fn):
        return None, None
    shape = (size, size)
    mask = np.ones(shape, np.float32)
    try:
        sp = spec_fn(shape, mask, 51, 1.0)
    except TypeError:
        sp = spec_fn(shape, 51, 1.0, 128, 80)
    sp = normalize(sp, shape, strict_shapes=True)
    neutral = np.ones((size, size, 3), np.float32) * 0.5
    paint = np.clip(np.asarray(paint_fn(neutral, shape, mask, 51, 1.0, 0.10), np.float32)[:, :, :3], 0, 1)
    return paint, sp


def main():
    ids = (sys.argv[1].split(",") if len(sys.argv) > 1 else DEFAULT_IDS)
    import shokker_engine_v2 as e
    from server_routes.spec_result_support import normalize_spec_result_to_rgba as normalize
    reg = e.MONOLITHIC_REGISTRY
    import cv2
    SZ = 340
    contact = []
    for fid in ids:
        t = time.time()
        paint, spec = render_paint_spec(reg, normalize, fid, SZ)
        if paint is None:
            print(f"  skip {fid}: not renderable"); continue
        frames = ss.sun_sweep(paint, spec, n_frames=24, elevation_deg=34)
        # PING-PONG for a seamless back-and-forth loop (smoother than a hard wrap)
        loop = frames + frames[-2:0:-1]
        ss.frames_to_gif(loop, os.path.join(OUTDIR, f"hero_{fid}.gif"), fps=18, max_size=SZ)
        tvar = float(np.stack([np.clip(f, 0, 1).mean(-1) for f in frames]).std(0).mean())
        kb = os.path.getsize(os.path.join(OUTDIR, f"hero_{fid}.gif")) / 1024
        print(f"  {fid:22s} {time.time()-t:.1f}s tvar={tvar:.3f} {kb:.0f}KB")
        # contact sheet = the brightest frame (the 'ignited' moment)
        bi = int(np.argmax([np.clip(f, 0, 1).mean() for f in frames]))
        tile = (np.clip(frames[bi], 0, 1) * 255).astype(np.uint8)
        cv2.putText(tile, fid[:20], (6, SZ - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(tile, fid[:20], (6, SZ - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        contact.append(cv2.copyMakeBorder(tile, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=(15, 15, 15)))
    if contact:
        nc = 4
        while len(contact) % nc:
            contact.append(np.full_like(contact[0], 15))
        rows = [np.concatenate(contact[i:i+nc], 1) for i in range(0, len(contact), nc)]
        cv2.imwrite(os.path.join(OUTDIR, "_contact_sheet.png"), np.concatenate(rows, 0))
        print("WROTE contact sheet + GIFs to _reworks_2026/hero_gifs/")


if __name__ == "__main__":
    main()
