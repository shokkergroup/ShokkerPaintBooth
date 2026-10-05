# -*- coding: utf-8 -*-
"""Flash Map report — render finishes' specs and score/visualise their angle-flash POTENTIAL, so you
can instantly see which finishes pop on track vs read as dead matte (catches lazy uniform panels).

Python mirror of the verified JS core in electron-app/server/paint-booth-flashmap.js (same formula:
flash = clamp(pot*(0.10+1.5*contrast)); pot=0.50*(1-R)+0.32*M+0.18*ccStrength; contrast=clamp(sd*4)).
Keep the two in sync. No server/restart. Output: _reworks_2026/flash_map/.
"""
import os, sys
import numpy as np

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "electron-app", "server"))
OUT = os.path.join(ROOT, "_reworks_2026", "flash_map")
os.makedirs(OUT, exist_ok=True)

# mix of likely-poppy (flaky/varied) and likely-flat finishes to show the coverage spread
DEFAULT_IDS = ["optics2_holo", "materials2_crystal", "materials2_titanium", "optics2_dvd",
               "materials2_liquid", "materials2_forged", "grd_iridescent", "carbon_fiber_2x2"]


def clearcoat_strength(cc):
    s = np.clip((255.0 - cc) / (255.0 - 16.0), 0, 1)
    return np.where(cc < 1, 0.0, s)


def flash_map(spec_u8, win=2):
    import cv2
    M = spec_u8[..., 0].astype(np.float32) / 255.0
    R = spec_u8[..., 1].astype(np.float32) / 255.0
    cc = clearcoat_strength(spec_u8[..., 2].astype(np.float32))
    pot = np.clip(0.50 * (1 - R) + 0.32 * M + 0.18 * cc, 0, 1).astype(np.float32)
    k = 2 * win + 1
    mean = cv2.boxFilter(pot, -1, (k, k))
    mean2 = cv2.boxFilter(pot * pot, -1, (k, k))
    var = np.clip(mean2 - mean * mean, 0, None)
    contrast = np.clip(np.sqrt(var) * 4.0, 0, 1)
    flash = np.clip(pot * (0.10 + 1.5 * contrast), 0, 1).astype(np.float32)
    cov = 100.0 * float((flash >= 0.30).mean())
    dead = 100.0 * float((flash < 0.12).mean())
    hot = 100.0 * float((flash >= 0.55).mean())
    heat = cv2.applyColorMap((flash * 255).astype(np.uint8), cv2.COLORMAP_TURBO)  # BGR cold->hot
    return flash, heat, cov, dead, hot


def render_spec(reg, normalize, fid, size):
    entry = reg.get(fid)
    if not (isinstance(entry, (tuple, list)) and len(entry) >= 2):
        return None
    spec_fn = entry[0]
    shape = (size, size)
    mask = np.ones(shape, np.float32)
    try:
        sp = spec_fn(shape, mask, 51, 1.0)
    except TypeError:
        sp = spec_fn(shape, 51, 1.0, 128, 80)
    return normalize(sp, shape, strict_shapes=True)


def main():
    import cv2
    ids = (sys.argv[1].split(",") if len(sys.argv) > 1 else DEFAULT_IDS)
    import shokker_engine_v2 as e
    from server_routes.spec_result_support import normalize_spec_result_to_rgba as normalize
    reg = e.MONOLITHIC_REGISTRY
    SZ = 300
    rows = []
    tiles = []
    for fid in ids:
        spec = render_spec(reg, normalize, fid, SZ)
        if spec is None:
            print(f"  skip {fid}"); continue
        flash, heat, cov, dead, hot = flash_map(spec)
        cv2.imwrite(os.path.join(OUT, f"flashmap_{fid[:24]}.png"), heat)
        rows.append((fid, cov, dead, hot))
        verdict = "DEAD/lazy" if cov < 20 else ("POPS" if cov > 60 else "ok")
        lab = f"{fid[:18]} {cov:.0f}%"
        t = heat.copy()
        cv2.putText(t, lab, (6, SZ - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(t, lab, (6, SZ - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        tiles.append(cv2.copyMakeBorder(t, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=(15, 15, 15)))
        print(f"  {fid:24s} flash-coverage={cov:5.1f}%  dead={dead:5.1f}%  hot={hot:5.1f}%  [{verdict}]")
    if tiles:
        nc = 4
        while len(tiles) % nc:
            tiles.append(np.full_like(tiles[0], 15))
        sheet = np.concatenate([np.concatenate(tiles[i:i+nc], 1) for i in range(0, len(tiles), nc)], 0)
        cv2.imwrite(os.path.join(OUT, "_flash_coverage_sheet.png"), sheet)
        rows.sort(key=lambda r: r[1])
        print("\nRanked lazy->poppy:")
        for fid, cov, dead, hot in rows:
            print(f"  {cov:5.1f}%  {fid}")
        print("WROTE _reworks_2026/flash_map/ (heatmaps + _flash_coverage_sheet.png)")


if __name__ == "__main__":
    main()
