"""Auto-Sculpt intelligence — PROTOTYPE v1 (2026-06-18 overnight).

Given a livery PAINT, suggest Spec Sculpt material presets that suit it, with reasons.
PURE + UNWIRED: a standalone heuristic that maps paint characteristics → existing
`SPEC_SCULPT_PRESETS` ids. It renders nothing, touches no spec/render/ingest code, and is
not wired into any flow — safe to iterate. The eventual feature (Auto-Sculpt) would call
this to pre-pick a material (and later, per-region material assignment).

⚠️ v1 heuristic — a STARTING point for the owner to tune, not a finished classifier. Suggestions
are existing preset ids so they're immediately actionable. NOT a replacement for the sacred
SHOKK DROP exact-import path (this is paint→material *suggestion*, never spec authoring).
"""
from __future__ import annotations

import numpy as np

# Material archetypes → a safe, known-existing preset id (verified present in presets.py).
_ARCHETYPES = {
    "matte":   ("frozen_matte",    "dark + low saturation → flat matte"),
    "carbon":  ("carbon_fiber",    "mid-tone + high edge density → woven carbon"),
    "chrome":  ("mirror_chrome",   "near-neutral + bright → mirror metal"),
    "brushed": ("brushed_titanium","near-neutral + mid + directional → brushed metal"),
    "candy":   ("candy_flow",      "saturated + bright → candy gloss"),
    "pearl":   ("circle_pearl",    "saturated + mid + soft → pearl"),
    "flake":   ("metal_flake",     "saturated + speckled detail → metal flake"),
    "holo":    ("holographic",     "very saturated + multi-hue → holographic"),
}


def _features(paint_rgb: np.ndarray) -> dict:
    a = np.asarray(paint_rgb, dtype=np.float32)
    if a.ndim == 3 and a.shape[2] > 3:
        a = a[:, :, :3]
    if a.size and a.max() > 1.5:
        a = a / 255.0
    a = np.clip(a, 0.0, 1.0)
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    luma = float((0.299 * R + 0.587 * G + 0.114 * B).mean())
    mx = np.max(a, axis=2); mn = np.min(a, axis=2)
    sat = float((np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)).mean())
    hue_spread = float(np.std(mx - mn))  # crude multi-hue proxy
    g = (0.299 * R + 0.587 * G + 0.114 * B)
    gy, gx = np.gradient(g)
    edge = float((np.abs(gx) + np.abs(gy)).mean())
    return {"luma": round(luma, 4), "saturation": round(sat, 4),
            "edge_density": round(edge, 5), "hue_spread": round(hue_spread, 4)}


def suggest_materials(paint_rgb: np.ndarray, *, top_n: int = 3) -> dict:
    """Return {features, suggestions:[{archetype, preset_id, score, reason}]} (ranked)."""
    f = _features(paint_rgb)
    luma, sat, edge, hue = f["luma"], f["saturation"], f["edge_density"], f["hue_spread"]
    bright = luma
    dark = 1.0 - luma
    neutral = max(0.0, min(1.0, 1.0 - sat / 0.18))   # ~1 near-gray, 0 once sat>0.18 (metals)
    edgey = min(1.0, edge * 30.0)                    # normalize edge density to ~0..1

    # v1.1 (2026-06-18): saturation, not brightness, drives candy — deep candy reds are
    # dark but vivid; pearl peaks at MID saturation (pastel), so high-sat paints read candy.
    scores = {
        "matte":   dark * (1.0 - sat) * 1.3,                                  # dark + desaturated
        "carbon":  neutral * edgey * 1.6,                                     # neutral + woven edges
        "chrome":  neutral * bright * 1.4,                                    # neutral + bright
        "brushed": neutral * (1.0 - min(1.0, abs(luma - 0.5) * 2.0)) * 1.0,   # neutral + mid-tone
        "candy":   (sat ** 1.2) * (0.55 + 0.45 * bright) * 1.5,               # saturation-driven gloss
        "pearl":   sat * (1.0 - sat) * 4.0 * (1.0 - min(1.0, abs(luma - 0.6) * 1.5)),  # mid-sat pastel
        "flake":   sat * edgey * 1.5,                                         # saturated + speckled
        "holo":    sat * hue * 8.0,                                           # saturated + multi-hue
    }
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:max(1, top_n)]
    suggestions = []
    for arch, sc in ranked:
        pid, reason = _ARCHETYPES[arch]
        suggestions.append({"archetype": arch, "preset_id": pid,
                            "score": round(float(sc), 4), "reason": reason})
    return {"features": f, "suggestions": suggestions}


def suggest_materials_by_region(paint_rgb: np.ndarray, *, grid: int = 4, top_n: int = 1) -> dict:
    """v2 — tile the paint into a grid×grid mesh and suggest a material per region.

    Enables per-panel material assignment (one paint can be candy on the hood, matte on the
    roof, carbon on the splitter). PURE + unwired. Returns {grid, regions:[{row,col,bbox,
    top, features}]}. A future Auto-Sculpt would group like-regions and build a per-zone spec.
    """
    a = np.asarray(paint_rgb, dtype=np.float32)
    if a.ndim == 3 and a.shape[2] > 3:
        a = a[:, :, :3]
    if a.size and a.max() > 1.5:
        a = a / 255.0
    H, W = a.shape[:2]
    g = max(1, int(grid))
    gh, gw = max(1, H // g), max(1, W // g)
    regions = []
    for r in range(g):
        for c in range(g):
            y0 = r * gh; y1 = H if r == g - 1 else (r + 1) * gh
            x0 = c * gw; x1 = W if c == g - 1 else (c + 1) * gw
            tile = a[y0:y1, x0:x1]
            res = suggest_materials(tile, top_n=top_n)
            regions.append({"row": r, "col": c, "bbox": [int(x0), int(y0), int(x1), int(y1)],
                            "top": res["suggestions"][0], "features": res["features"]})
    return {"grid": g, "regions": regions}


def format_suggestions(result: dict) -> str:
    f = result["features"]
    lines = [f"Auto-Sculpt v1 — features: luma={f['luma']} sat={f['saturation']} "
             f"edge={f['edge_density']} hue_spread={f['hue_spread']}", "  suggested materials:"]
    for s in result["suggestions"]:
        lines.append(f"   • {s['preset_id']:16} (score {s['score']:.2f}) — {s['reason']}")
    return "\n".join(lines)
