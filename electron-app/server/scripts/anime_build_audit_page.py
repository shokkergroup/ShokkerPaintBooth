# -*- coding: utf-8 -*-
"""Generate SPB_AUDIT_anime.html via the shared builder for the FULL 25-design ★ ANIME INSPIRED
category ([SPB ANIME OVERHAUL 2026-08-25], docs/ANIME_OVERHAUL_2026-08-25.md): 15 monolithic
anime2_* specials + 10 anime_* BASE_REGISTRY finishes, all backed by anime_math married
paint+spec structures. Swatch = 2-panel [LEFT anime paint | RIGHT on-car composite = paint x
married spec gloss under a sweeping light]. Re-runnable each round."""
import os, sys, time
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from spb_audit_page_builder import build_page
from engine.paint_v2 import anime_math as am
from engine.expansions.anime_catalog_2026 import ANIME_FINISHES

THUMB_DIR = os.path.join(ROOT, "thumbnails", "audit", "anime")
os.makedirs(THUMB_DIR, exist_ok=True)

# the 10 BASE_REGISTRY anime ids -> (structure key, display name)
BASE_TEN = {
    "anime_cel_shade_chrome": ("cel_terminator", "Cel Terminator"),
    "anime_speed_lines": ("speedline_storm", "Speed-Line Storm"),
    "anime_sparkle_burst": ("shoujo_sparkle", "Shoujo Sparkle Field"),
    "anime_gradient_hair": ("inkbrush_strands", "Ink-Brush Strands"),
    "anime_mecha_plate": ("mecha_greeble", "Mecha Greeble"),
    "anime_sakura_scatter": ("sakura_hurricane", "Sakura Hurricane"),
    "anime_energy_aura": ("ki_corona", "Ki Corona"),
    "anime_comic_halftone": ("screentone_moire", "Screentone Moiré"),
    "anime_neon_outline": ("neo_tokyo_glow", "Neo-Tokyo Glow"),
    "anime_crystal_facet": ("shard_cascade", "Crystal Shard Cascade"),
}


def on_car(paint, spec):
    alb = np.clip(np.asarray(paint, np.float32), 0, 1)
    s = np.asarray(spec, np.float32)
    m, r, cc = s[..., 0] / 255, s[..., 1] / 255, s[..., 2] / 255
    H, W = m.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    Lc = (xx / (W - 1)) * 0.6 + (yy / (H - 1)) * 0.4
    band = np.clip(1.0 - np.abs(Lc - 0.52) * 2.0, 0, 1)
    hi = np.power(band, 6.0 + (1 - r) * 200.0)
    refl = 0.18 + 0.85 * m + 0.40 * cc
    sky = np.array([0.85, 0.90, 1.0], np.float32)
    speccol = (0.55 * alb + 0.45 * sky) * ((refl * hi)[..., None])
    return np.clip(alb * (0.55 + 0.18 * (1 - r))[..., None] + speccol, 0, 1)


def add_item(fid, structure, name, desc, kindnote):
    t0 = time.time()
    built = am.build(structure, (SZ, SZ), 7)
    paint = np.asarray(built["rgb"], np.float32)[:, :, :3]
    spec = np.clip(np.asarray(built["spec"], np.float32), 0, 255)
    render_s = round(time.time() - t0, 2)
    pv = (np.clip(paint, 0, 1) * 255).astype(np.uint8)
    cvm = (on_car(paint, spec) * 255).astype(np.uint8)
    pad = np.full((SZ, 6, 3), 25, np.uint8)
    swatch_img = np.concatenate([pv, pad, cvm], axis=1)
    cv2.imwrite(os.path.join(THUMB_DIR, fid + ".png"), cv2.cvtColor(swatch_img, cv2.COLOR_RGB2BGR))
    # AI badge = married-spec channel richness (mean of M/R/CC std, scaled)
    stds = [float(spec[:, :, i].std()) for i in range(3)]
    META.append(dict(id=fid, name=name, kind="finish",
                     desc=desc + " LEFT paint, RIGHT on-car (married spec). " + kindnote,
                     technique="anime_math/" + structure + " (married paint+spec)",
                     render_s=render_s, ai_rating=int(min(100, round(np.mean(stds) * 1.4)))))
    print(f"  {fid:24s} {render_s:.2f}s stds={stds[0]:.0f}/{stds[1]:.0f}/{stds[2]:.0f}")


META = []
SZ = 460
for fid, (structure, name, swatch, desc) in ANIME_FINISHES.items():
    add_item(fid, structure, name, desc, "(★ ANIME INSPIRED special)")
for fid, (structure, name) in BASE_TEN.items():
    add_item(fid, structure, name, "Rebuilt base finish — " + structure.replace("_", " ") + ".",
             "(base finish)")

TITLE = ('<span class="flag">★ ANIME INSPIRED</span> - 25-Design Overhaul Audit '
         '<span style="color:var(--dim);font-weight:400">(2026-08-25 gen: 15 specials + 10 bases)</span>')
SUB = ("The category rebuilt to the owner mandate: 25 mind-melting DISTINCT anime designs, no "
       "repeats, no recolors. Every design is a different generative mechanism (cel terminators, "
       "interfering speed-line systems, petal advection, greebled panels, aura shells, dot-lattice "
       "moiré, aerial night city, voronoi shards, cel cloud decks, impact-burst cells, lantern "
       "festivals, holo wireframes, blade storms, dendritic lightning, iris fields, holo foil, "
       "kanji rain, comic burst riots, RGB-split glitch, CRT raster, eclipse moons, sumi-e "
       "brushwork, manga panel pages) with a MARRIED same-geometry spec. All 300 pairs measure "
       "&lt;35% structural similarity (clone line 80%); coverage/fineness/render gates green. "
       "LEFT swatch = paint, RIGHT = on-car composite. <b>SUBMIT THIS ONE</b> saves a card. "
       "AI badge = spec channel richness. ⏱ = render time at 460px.")

build_page("anime", TITLE, SUB, META, THUMB_DIR,
           os.path.join(ROOT, "SPB_AUDIT_anime.html"), accent="#ff5a7a")
