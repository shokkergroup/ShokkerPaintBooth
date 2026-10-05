# FM + SOULS hard gate: spec physics + lane coverage + feature size + perf @1024
#
# 2026-06-12 (round 6, owner mandate): FRACTURED MINDS was re-dialed onto the
# SOUL physics (winner contract from the Blood Marble forensics — M ~252,
# B railed 255, G = floor 30 + design lanes). The old GHST/PINK/PASTEL spec
# profiles are RETIRED; the FM section now gates the LIVE registry entries
# (the fractured_minds_soul_2026 wrapper output), which is what actually ships.
#
# FRACTURED SOULS section unchanged in spirit: raw SOULS dict == live entries.
import time, sys
import numpy as np
import cv2
sys.path.insert(0, '.')
import shokker_engine_v2 as eng
import engine.expansions.fractured_souls_2026 as fsouls

W = 1024
only = sys.argv[1:] if len(sys.argv) > 1 else None
fails = 0

# ── FRACTURED MINDS (live wrapped entries, soul physics) ────────────────────
mask = np.ones((W, W), np.float32)
gray = np.full((W, W, 3), 0.5, np.float32)
fm_ids = sorted(k for k in eng.MONOLITHIC_REGISTRY if k.startswith("fm_"))
print(f"{'finish':<18} {'Mmean':>6} {'Gmean':>6} {'lane%':>6} {'Bmean':>6} {'sizpx':>6} {'V99':>5} {'sec':>5}  verdict")
for fid in fm_ids:
    if only and fid not in only and fid[3:] not in only:
        continue
    sfn, pfn = eng.MONOLITHIC_REGISTRY[fid]
    t0 = time.time()
    spec = sfn((W, W, 3), mask, 12345, 1.0)
    paint = pfn(gray, (W, W, 3), mask, 12345, 1.0, None)
    dt_s = time.time() - t0
    M = spec[..., 0].astype(np.float32)
    G = spec[..., 1].astype(np.float32)
    B = spec[..., 2].astype(np.float32)
    lanes = (G > 50).astype(np.uint8)
    lane_frac = float(lanes.mean())
    probs = []
    if M.mean() < 240: probs.append("Mlow")
    if not (30 <= G.mean() <= 62): probs.append("Gmean")
    if B.mean() < 250: probs.append("Bweak")
    if not (0.015 <= lane_frac <= 0.45): probs.append(f"LANE{lane_frac:.2f}")
    if lanes.any():
        dt = cv2.distanceTransform(lanes, cv2.DIST_L2, 3)
        size2048 = float(np.median(dt[lanes > 0]) * 2 * 2)
        # fine-detail bar: lanes are hairlines/rims — fat blobs are blotch
        if size2048 > 28: probs.append(f"BLOTCH{size2048:.0f}")
    else:
        size2048 = 0.0
    pv = paint.max(2)
    v99 = float(np.percentile(pv, 99))
    if not (0.08 <= v99 <= 0.60): probs.append(f"CRUSH{v99:.2f}")
    if dt_s > 2.6: probs.append("PERF")
    verdict = "OK" if not probs else "FAIL " + ",".join(probs)
    if probs: fails += 1
    print(f"{fid[3:]:<18} {M.mean():6.0f} {G.mean():6.0f} {100*lane_frac:5.1f}% {B.mean():6.0f} {size2048:6.1f} {v99:5.2f} {dt_s:5.2f}  {verdict}")

# ── FRACTURED SOULS contract gate (owner lab physics 2026-06-12) ────────────
# clearcoat = power supply (B >= 234), roughness = aperture (G mean <= 70,
# closed fraction <= 5%), metal = amplifier (M >= 228), paint pre-crushed.
print()
print(f"{'soul':<20} {'Mmean':>6} {'Gmean':>6} {'Ghi%':>5} {'Bmean':>6} {'crush':>6} {'sec':>5}  verdict")
for fid in sorted(fsouls.SOULS):
    if only and fid not in only and fid[3:] not in only and "fs_" not in (only[0] if only else ""):
        continue
    t0 = time.time()
    F = fsouls.SOULS[fid]["fields"](W, W, 12345)
    M, G, B = fsouls.SOULS[fid]["spec"](F, 12345, W, W)
    art, k = fsouls.SOULS[fid]["paint"](F, None)
    dt_s = time.time() - t0
    zero = np.zeros((W, W), np.float32)
    M = np.clip(np.asarray(M, np.float32) + zero, 0, 255)
    G = np.clip(np.asarray(G, np.float32) + zero, 0, 255)
    B = np.clip(np.asarray(B, np.float32) + zero, 0, 255)
    probs = []
    if M.mean() < 228: probs.append("Mlow")
    if G.mean() > 70: probs.append("Ghigh")
    if float((G > 110).mean()) > 0.05: probs.append("Gclosed")
    if B.mean() < 234: probs.append("Bweak")
    if dt_s > 2.2: probs.append("PERF")
    v = float(np.asarray(art, np.float32).mean())
    if not (0.03 < v < 0.30): probs.append(f"CRUSH{v:.2f}")
    verdict = "OK" if not probs else "FAIL " + ",".join(probs)
    if probs: fails += 1
    print(f"{fid[3:]:<20} {M.mean():6.0f} {G.mean():6.0f} {float((G > 110).mean()) * 100:4.1f}% {B.mean():6.0f} {v:6.2f} {dt_s:5.2f}  {verdict}")

print(f"\nFAILED: {fails}")
