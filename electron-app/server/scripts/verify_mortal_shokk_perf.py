# -*- coding: utf-8 -*-
"""Verify the Mortal Shokk 2048-derivative perf fix is quality-neutral + measure speedup.

For each ms_* finish, render the swatch from the 4K source (SPB_MORTAL_SHOKK_USE_SMALL=0)
and from the baked 2048 derivative (=1), clearing the source caches between so each render
is a true cold decode. Reports per-finish mean-abs-diff (LSB, 0-255) + global SSIM, the
worst case, and the cold-render time for each source. Ship gate: meanLSB < 1.0 AND SSIM
>= 0.995 on every finish.  Run: python -B scripts/verify_mortal_shokk_perf.py
"""
import os, sys, io, time
os.environ.setdefault("SHOKKER_SKIP_SPEC_PREBAKE", "1")
os.environ.setdefault("SHOKKER_NO_CLEAN", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)

import numpy as np
from PIL import Image
import server
from engine.paint_v2 import cultural_mortal_shokk as ms


def clear_src_caches():
    try:
        ms._load_rgb_cached.cache_clear()
    except Exception:
        pass
    for c in ("_RESIZED_RGB_CACHE", "_SPEC_FULL_MASK_CACHE", "_FULL_MASK_CACHE"):
        try:
            getattr(ms, c).clear()
        except Exception:
            pass


def render(fid, sz):
    b = server._render_swatch_bytes("monolithic", fid, "888888", sz, 42)
    return np.asarray(Image.open(io.BytesIO(b)).convert("RGB"), np.float32)


def gssim(a, b):
    a = a / 255.0; b = b / 255.0
    ma, mb = a.mean(), b.mean()
    va, vb = a.var(), b.var()
    cov = ((a - ma) * (b - mb)).mean()
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    return float(((2 * ma * mb + c1) * (2 * cov + c2)) / ((ma * ma + mb * mb + c1) * (va + vb + c2)))


ids = list(ms._FINISH_IDS)
print("verifying %d ms_* finishes" % len(ids), flush=True)
worst_lsb, worst_ssim, worst_id = 0.0, 1.0, ""
t4k = t2k = 0.0
SZ_TIME, SZ_Q = 64, 256
for fid in ids:
    # perf timing at the flagged swatch size (64)
    os.environ["SPB_MORTAL_SHOKK_USE_SMALL"] = "0"; clear_src_caches()
    t = time.time(); render(fid, SZ_TIME); t4k += time.time() - t
    os.environ["SPB_MORTAL_SHOKK_USE_SMALL"] = "1"; clear_src_caches()
    t = time.time(); render(fid, SZ_TIME); t2k += time.time() - t
    # quality at 256
    os.environ["SPB_MORTAL_SHOKK_USE_SMALL"] = "0"; clear_src_caches(); a = render(fid, SZ_Q)
    os.environ["SPB_MORTAL_SHOKK_USE_SMALL"] = "1"; clear_src_caches(); b = render(fid, SZ_Q)
    lsb = float(np.abs(a - b).mean())
    s = gssim(a, b)
    if lsb > worst_lsb:
        worst_lsb, worst_id = lsb, fid
    worst_ssim = min(worst_ssim, s)
    flag = "" if (lsb < 1.0 and s >= 0.995) else "  <-- CHECK"
    print("  %-24s meanLSB=%.3f  SSIM=%.4f%s" % (fid, lsb, s, flag), flush=True)

print("-" * 60)
print("WORST: meanLSB=%.3f (%s)  minSSIM=%.4f" % (worst_lsb, worst_id, worst_ssim))
print("COLD RENDER @%d (sum over %d): 4K=%.1fs  2048=%.1fs  speedup=%.1fx"
      % (SZ_TIME, len(ids), t4k, t2k, t4k / max(t2k, 0.01)))
print("GATE: %s" % ("PASS (quality-neutral)" if (worst_lsb < 1.0 and worst_ssim >= 0.995) else "FAIL — review"))
