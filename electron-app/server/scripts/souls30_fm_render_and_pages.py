# -*- coding: utf-8 -*-
"""FRACTURED SOULS round 3 (30 finishes) + FRACTURED MINDS soul-retune —
render through the REAL registry entries and build both audit pages.

Page 1: SPB_AUDIT_fracturedsouls.html (category 'fracturedsouls', same backend
        category as rounds 1-2 so existing verdicts persist; rated cards
        auto-hide). All 30 souls, the 15 new ones marked NEW ROUND-3.
Page 2: SPB_AUDIT_fracturedminds_soul.html (category 'fracturedmindssoul',
        fresh round) — all 55 FM finishes re-dialed onto the winner physics.

Card image: canvas (raw crushed) | canvas LIFTED for visibility | combined spec.
"""
import os, sys, time, json
import numpy as np
import cv2

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import shokker_engine_v2 as E
from engine.color_science import feature_fineness, mip_survival
from spb_audit_page_builder import build_page

S = 2048

NEW_SOULS = {
    "fs_soul_loom": "WOVENLIGHT TWIST — the loom itself, crushed: two warped ribbon axes weave over/under with grooves + dive shadows + thread striations, but pre-crushed emerald x violet. The weave flashes TWO colors by sun angle (each ribbon family owns one).",
    "fs_widow_braid": "WOVENLIGHT TWIST — tri-axial braid: THREE warped strand families 60 degrees apart cycle on top like a braid. Three crushed hues (rose / petrol / amber) = three different flash colors from three sun geometries.",
    "fs_ghost_silk": "WOVENLIGHT TWIST — the thread striations alone: micro satin threads in crisp curtain panels, third-angle sheen pools decide WHERE the silk ignites; hue slides indigo->teal along the sheen.",
    "fs_shattered_prism": "Your '47 colors' idea distilled — a fine crystal mosaic where EVERY cell carries its own crushed hue. Borders + per-cell facet striations carve the aperture; each cell pops its own complement at its own angle.",
    "fs_oil_serpent": "Advected serpent currents — the strand hue follows the FLOW DIRECTION, so the same paint flashes different colors depending on which way the current bends around the panel.",
    "fs_hex_hive": "Dead hive — fine rotated honeycomb, three crushed hues cycling cell-by-cell (amber / umber / petrol), walls carve the aperture, a razor pore pin in every cell.",
    "fs_guilloche_ghost": "Banknote engine-turning — overlapping hairline harmonograph rosette nets (champagne + teal over crushed bronze); curve crossings pin razor glints.",
    "fs_petrol_halo": "Newton-ring packets — scattered interference halos of fine concentric rings whose hue cycles with ring index. Oil-on-water, crushed.",
    "fs_star_chart": "Grave-sky cartography — razor star pins, hairline constellation chords, three faint nebula hue washes under crushed indigo.",
    "fs_serpent_scale": "Imbricated scale rows — fine crescent rims + keeled centers, alternating crushed emerald/abyss rows that flash row-by-row.",
    "fs_nova_burst": "Scattered micro star-detonations, each with its own crushed hue halo — a six-color nova field on near-black violet.",
    "fs_circuit_soul": "Haunted circuitry — hairline traces walking a seed-rotated grid, via-dots pinned razor; copper vs teal trace families flash separately.",
    "fs_geode_vein": "Agate banding — warped contour bands cycling a five-hue crushed sequence (violet/teal/gold/rose/ice), druzy pin pockets every few bands.",
    "fs_moire_phantom": "CIRCULAR moire — two families of fine concentric rings interfere into wandering hyperbolic phantom curves; the beat decides which hue shows (steel-teal vs rose).",
    "fs_aurora_threads": "Curtain filaments — micro threads gated into crisp aurora curtains, hue sweeping green->teal->violet across the car. Many colors live in the paint at once.",
}

FM_DESC = ("SOUL-PHYSICS RETUNE — design kept verbatim, spec re-dialed to the winner "
           "contract you proved on Blood Marble (metal ~252, clearcoat railed 255, "
           "roughness = gloss floor 30 + fine aperture lanes traced from the design's "
           "own geometry), paint crushed-but-COLORFUL (less crushed than the souls).")


def label(bgr, text):
    cv2.rectangle(bgr, (0, bgr.shape[0] - 22), (bgr.shape[1] - 1, bgr.shape[0] - 1), (12, 12, 12), -1)
    cv2.putText(bgr, text, (7, bgr.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (210, 210, 210), 1, cv2.LINE_AA)
    return bgr


def ai_rating(paint, mip, fine):
    f = paint.mean(2); bands = 0.0
    for sg in (1.5, 6.0, 24.0):
        lo = cv2.GaussianBlur(f, (0, 0), sg); bands += min(float(np.abs(f - lo).mean()) / 0.04, 1.0); f = lo
    clip = float(((paint <= 0.002) | (paint >= 0.998)).mean())
    return int(np.clip(round(22 + bands * 12 + mip * 14 + fine * 22 - clip * 25), 1, 100))


def crop(a):
    return (np.clip(a[768:1280, 768:1280], 0, 1) * 255).astype(np.uint8)


def card(fid, out_dir, lifted=False):
    spec_fn, paint_fn = E.MONOLITHIC_REGISTRY[fid]
    mask = np.ones((S, S), np.float32)
    base = np.full((S, S, 3), 0.5, np.float32)
    t0 = time.perf_counter()
    paint = np.clip(np.asarray(paint_fn(base, (S, S), mask, 42, 1.0, 1.0), np.float32)[:, :, :3], 0, 1)
    sp = np.asarray(spec_fn((S, S), mask, 42, 1.0), np.float32)
    dt = time.perf_counter() - t0
    spec = np.clip(sp[:, :, :3] / 255.0, 0, 1)
    fin = feature_fineness(paint, full_size=S); mip = mip_survival(paint)
    ai = ai_rating(paint, mip, fin.get("fine_fraction", 0.5))
    tiles = [label(cv2.cvtColor(crop(paint), cv2.COLOR_RGB2BGR), "canvas (1:1 crop, ships this dark)")]
    if lifted:
        lift = np.clip(paint, 0, 1) ** 0.42
        tiles.append(label(cv2.cvtColor(crop(lift), cv2.COLOR_RGB2BGR), "same canvas LIFTED (design preview)"))
    tiles.append(label(cv2.cvtColor(crop(spec), cv2.COLOR_RGB2BGR), "spec  R=M G=R B=Cc"))
    sep = np.full((512, 4, 3), 24, np.uint8)
    img = tiles[0]
    for t in tiles[1:]:
        img = np.hstack([img, sep, t])
    cv2.imwrite(os.path.join(out_dir, fid + ".png"), img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    return ai, mip, dt


# ── Page 1: FRACTURED SOULS (all 30) ────────────────────────────────────────
OUT1 = os.path.join(ROOT, "thumbnails", "audit", "fracturedsouls")
os.makedirs(OUT1, exist_ok=True)
old_meta = {m["id"]: m for m in json.load(open(os.path.join(ROOT, "scripts", "fracturedsouls_audit_meta.json"), encoding="utf-8"))}
import engine.expansions.fractured_souls_2026 as fsouls
meta1 = []
print("=== FRACTURED SOULS (30) ===")
for fid in sorted(fsouls.SOULS):
    ai, mip, dt = card(fid, OUT1, lifted=True)
    short = fid.replace("fs_", "")
    if fid in NEW_SOULS:
        name = short.replace("_", " ").title()
        desc = "NEW ROUND-3 — " + NEW_SOULS[fid] + " Ships on the winner physics from your Blood Marble card (M252 / B255-rail / G-lanes)."
    else:
        prev = old_meta.get(fid, {})
        name = prev.get("name", short.replace("_", " ").title())
        desc = prev.get("desc", "FRACTURED SOULS finish.")
    print("%-24s ai%3d  %.2fs" % (fid, ai, dt))
    meta1.append({"id": fid, "name": name, "kind": "finish", "desc": desc,
                  "ai_rating": ai, "mip": round(float(mip), 2), "render_s": round(dt, 2)})
json.dump(meta1, open(os.path.join(ROOT, "scripts", "fracturedsouls_audit_meta.json"), "w", encoding="utf-8"), indent=1)

TITLE1 = ('<span class="flag">💀 FRACTURED SOULS — ROUND 3: THE EXPANSION TO 30</span> '
          '<span style="color:var(--dim);font-weight:400">(15 new souls on the winner physics from your Blood Marble card — M252 / B255-rail / G-lanes; 3 of them are deliberate WOVENLIGHT twists)</span>')
SUB1 = ("All 30 souls on one page — cards you already rated stay hidden. The 15 NEW ROUND-3 cards: "
        "3 Wovenlight-construction twists (Soul Loom / Widow Braid / Ghost Silk), the '47 colors' "
        "Shattered Prism, and 11 more fine-detail multi-hue designs. Every card ships drag-and-drop "
        "(no sliders): paint pre-crushed, clearcoat railed 255, metal 252, design in the roughness lanes. "
        "LEFT = canvas as it ships (dark), MIDDLE = same canvas lifted so you can see the design, "
        "RIGHT = combined spec. Ritual: drop on a zone + daytime track.")
build_page("fracturedsouls", TITLE1, SUB1, meta1, OUT1, os.path.join(ROOT, "SPB_AUDIT_fracturedsouls.html"), accent="#c33")
print("WROTE SPB_AUDIT_fracturedsouls.html (%d cards)" % len(meta1))

# ── Page 2: FRACTURED MINDS soul retune (all 55) ────────────────────────────
OUT2 = os.path.join(ROOT, "thumbnails", "audit", "fracturedmindssoul")
os.makedirs(OUT2, exist_ok=True)
fm_ids = sorted(k for k in E.MONOLITHIC_REGISTRY if k.startswith("fm_"))
meta2 = []
print("=== FRACTURED MINDS soul retune (%d) ===" % len(fm_ids))
for fid in fm_ids:
    ai, mip, dt = card(fid, OUT2, lifted=True)
    name = fid.replace("fm_", "").replace("_", " ").title()
    print("%-24s ai%3d  %.2fs" % (fid, ai, dt))
    meta2.append({"id": fid, "name": name, "kind": "finish", "desc": FM_DESC,
                  "ai_rating": ai, "mip": round(float(mip), 2), "render_s": round(dt, 2)})
json.dump(meta2, open(os.path.join(ROOT, "scripts", "fracturedmindssoul_audit_meta.json"), "w", encoding="utf-8"), indent=1)

TITLE2 = ('<span class="flag">🧠 FRACTURED MINDS — THE SOUL RETUNE (all 55)</span> '
          '<span style="color:var(--dim);font-weight:400">(your mandate: same designs, rebuilt with the Blood Marble winner physics + colorful crush)</span>')
SUB2 = ("Every FRACTURED MINDS finish re-dialed: spec = metal 252 / clearcoat railed 255 / roughness "
        "floor 30 with fine aperture lanes traced from each design's OWN geometry (no blotch — blob "
        "interiors return to gloss floor, only rims/veins/threads carry lanes). Paint = crushed but "
        "COLORFUL (deliberately less crushed than the souls, saturation boosted). "
        "LEFT = canvas as it ships, MIDDLE = lifted preview, RIGHT = combined spec. "
        "This page supersedes the round-5 pastel page.")
build_page("fracturedmindssoul", TITLE2, SUB2, meta2, OUT2, os.path.join(ROOT, "SPB_AUDIT_fracturedminds_soul.html"), accent="#7a5cff")
print("WROTE SPB_AUDIT_fracturedminds_soul.html (%d cards)" % len(meta2))
