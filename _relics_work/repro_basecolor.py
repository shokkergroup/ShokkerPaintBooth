# -*- coding: utf-8 -*-
"""Reproduce the owner's ACTUAL workflow from a captured payload.

From output/job_render_.../zones_payload.json (the owner's own session):
    base_color_mode   = 'special'
    base_color_source = 'mono:ffo_broached'      <- the same finish
    base_strength     = 0.4                      <- the blend slider
    base_scale        = 0.2                      <- SCALED DOWN
    intensity         = '10'
    pattern           = 'metal_flake'

Renders the matrix so we can see which field is eating the colour, instead of
reasoning about code paths.
"""
import contextlib, io, logging, os, sys, tempfile, uuid
import numpy as np
from PIL import Image

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT); sys.path.insert(0, ROOT)
logging.disable(logging.CRITICAL)
_buf = io.StringIO()
with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
    import shokker_engine_v2 as eng

FID = sys.argv[1] if len(sys.argv) > 1 else "frl_bone_ash"
work = os.path.join(tempfile.gettempdir(), "spb_repro_" + uuid.uuid4().hex[:6])
os.makedirs(work, exist_ok=True)
src = np.zeros((256, 256, 3), np.uint8)
src[:, :] = (243, 60, 0)                     # the orange source paint from the capture
src_path = os.path.join(work, "src.png")
Image.fromarray(src).save(src_path)

# what the finish looks like on its own, for reference
spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[FID]
own = np.asarray(paint_fn(np.full((256, 256, 3), 0.5, np.float32), (256, 256),
                          np.ones((256, 256), np.float32), 51, 1.0, None), np.float32)
own8 = np.clip(own * 255, 0, 255).astype(np.uint8)
print(f"{FID} on its own      : mean RGB {own8.reshape(-1,3).mean(0).round(1)}")
print(f"source paint          : mean RGB {src.reshape(-1,3).mean(0).round(1)}")
print()


def run(tag, **extra):
    z = {"name": "Original Paint", "color": "remaining", "hard_edge": True,
         "finish": FID, "intensity": "100",
         "base_color_mode": "special", "base_color_source": "mono:" + FID,
         "base_color_strength": 1, "base_spec_strength": 1, "base_strength": 1.0}
    z.update(extra)
    out = os.path.join(work, tag); os.makedirs(out, exist_ok=True)
    with contextlib.redirect_stdout(_buf), contextlib.redirect_stderr(_buf):
        paint, _spec = eng.build_multi_zone(src_path, out, [z], seed=51, preview_mode=True)
    p = np.asarray(paint)
    p = np.clip(p * (255.0 if p.max() <= 1.001 else 1.0), 0, 255).astype(np.uint8)[:, :, :3]
    m = p.reshape(-1, 3).mean(0)
    d_src = float(np.abs(p.astype(float) - src.astype(float)).mean())
    verdict = "SOURCE ONLY (colour lost)" if d_src < 6 else "finish colour present"
    print(f"  {tag:34s} mean {m.round(1)}  diff-from-source {d_src:6.1f}  {verdict}")


print("BASE STRENGTH sweep (base_scale 1.0):")
for bs in (1.0, 0.5, 0.2):
    run(f"strength_{bs}", base_strength=bs)
print()
print("BASE SCALE sweep (base_strength 1.0):")
for sc in (1.0, 0.5, 0.2):
    run(f"scale_{sc}", base_scale=sc)
print()
print("The owner's exact capture (scale 0.2 + strength 0.4 + intensity 10 + pattern):")
run("owner_capture", base_scale=0.2, base_strength=0.4, intensity="10",
    pattern="metal_flake", pattern_intensity="100", pattern_opacity=1)
run("capture_no_pattern", base_scale=0.2, base_strength=0.4, intensity="10")
run("capture_no_intensity", base_scale=0.2, base_strength=0.4)
