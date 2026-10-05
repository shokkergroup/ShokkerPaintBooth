# -*- coding: utf-8 -*-
"""Calibrate the RELICS gates against finishes the owner has already approved:
the old RELIC best, a KINTSUGI keeper, and the X LAB gold standard. One engine
boot, luma-correct metrics, one line each."""
import io, os, sys, time, contextlib, logging
import numpy as np, cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
os.chdir(ROOT); sys.path.insert(0, ROOT)
logging.disable(logging.CRITICAL)
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    import shokker_engine_v2 as eng

REFS = ["fre_lapis_inlay", "fre_ivory_mosaic", "fki_golden_river",
        "fca_crown_jewels", "fcw_gold_mainspring", "xlab_hologram_metal",
        "fo_rune_lattice"]
SHAPE = (2048, 2048); MASK = np.ones(SHAPE, bool)


def band_score(L):
    F = np.fft.fftshift(np.abs(np.fft.fft2(L - L.mean())) ** 2)
    n = L.shape[0]
    yy, xx = np.mgrid[0:n, 0:n] - n // 2
    r = np.hypot(xx, yy)
    return float(F[(r >= 64) & (r <= 256)].sum() / max(F[r >= 2].sum(), 1e-9))


for fid in REFS:
    if fid not in eng.MONOLITHIC_REGISTRY:
        print(f"--   {fid:24s} not registered"); continue
    spec_fn, paint_fn = eng.MONOLITHIC_REGISTRY[fid]
    base = np.full(SHAPE + (3,), 128, np.uint8)
    t0 = time.time()
    p = paint_fn(base.copy(), SHAPE, MASK, 51, 1.0, None)
    try:
        s = spec_fn(SHAPE, MASK, 51, 1.0)
    except TypeError:
        s = spec_fn(SHAPE, 51, 1.0)
    dt = time.time() - t0
    p = np.asarray(p, np.float32)
    p8 = np.clip(p * (255.0 if p.max() <= 1.5 else 1.0), 0, 255).astype(np.uint8)
    s8 = np.asarray(s)[..., :3].astype(np.float32)
    lum = (0.299 * p8[..., 0] + 0.587 * p8[..., 1] + 0.114 * p8[..., 2]).astype(np.float32)
    fine = float(np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 6)).mean())
    small = cv2.resize(p8, (512, 512), interpolation=cv2.INTER_AREA)
    L = (0.299 * small[..., 0] + 0.587 * small[..., 1] + 0.114 * small[..., 2]).astype(np.float32)
    sm = cv2.resize(s8, (512, 512), interpolation=cv2.INTER_AREA)
    stds = [float(sm[..., i].std()) for i in range(3)]
    Lz = (L - L.mean()) / (L.std() + 1e-6)
    corr = max(abs(float(((sm[..., i] - sm[..., i].mean()) / (stds[i] + 1e-6) * Lz).mean()))
               for i in range(3))
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    sat = hsv[..., 1].astype(np.float32) / 255.0
    hue = hsv[..., 0].astype(np.float32) / 179.0
    good = hue[sat > 0.18]
    hb = int((np.histogram(good, bins=12, range=(0, 1))[0] > max(good.size, 1) * 0.02).sum()) if good.size > 100 else 0
    live = sum(1 for ty in range(8) for tx in range(8)
               if small[ty * 64:(ty + 1) * 64, tx * 64:(tx + 1) * 64].std() > 6.0)
    print(f"REF  {fid:24s} {dt:5.2f}s band={band_score(L):.2f} live={live}/64 "
          f"fineLuma={fine:5.1f} meanL={lum.mean():5.1f} hues={hb} sat={sat.mean():.2f} "
          f"spec={stds[0]:3.0f}/{stds[1]:3.0f}/{stds[2]:3.0f} corr={corr:.2f}", flush=True)
