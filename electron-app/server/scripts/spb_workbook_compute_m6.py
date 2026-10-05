#!/usr/bin/env python3
"""
SPB Finish Quality Workbook — Metric M6: Intent-Aware Floor / Ceiling.

Each category has an expected signature on measurable axes. Matte categories
should be QUIET (low fine energy, low spec range), candy/pearl should be
SATURATED + LUSH SPEC, geometric should be HIGH frequency, etc.

For each finish:
  - Look up its category profile.
  - For each axis the profile opines on, check if the finish's percentile rank
    falls inside the expected band.
  - Score = (passes / opinions) × 100.

Categories without a profile get score=null (we don't punish unknown intent).

Output: _workbook_metrics/m6_intent_floor_ceiling.{json,js}
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

# Defend against Windows cp1252 stdout when category names contain Unicode
# like ★ ✨ — print statements with these would crash and the JSON write
# would be skipped. Match the pattern used in spb_workbook_compute_m7.py.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCORECARD = PROJECT_ROOT / "paint-booth-0-catalog-scorecard.js"
OUT_DIR = PROJECT_ROOT / "_workbook_metrics"
OUT_DIR.mkdir(exist_ok=True)

AXES = [
    "paintFineEnergy",
    "paintResidualEnergy",
    "paintBlockEnergy",
    "paintColorPopulation",
    "paintSaturationMean",
    "specMRange",
    "specRRange",
    "specCcRange",
    "specChannelIndependence",
]

LO, MID, HI = "LO", "MID", "HI"

# Floor / ceiling per direction. Tuple = (floor_rank, ceiling_rank) in [0,1].
# Matte/clean: ceiling at 0.4 (must be in lower 40%).
# Mid: 0.30..0.70 band.
# High: floor at 0.6 (must be in upper 40%).
DIRECTION_BAND = {
    LO:  (0.00, 0.40),
    MID: (0.30, 0.70),
    HI:  (0.60, 1.00),
}

# Category → axis → direction. Sparse; if a category has no profile, score=null.
# Direction reflects what the category SHOULD look like, not what the catalog
# currently measures. This is the metric's whole job: catch the mismatch.
CATEGORY_PROFILES: dict[str, dict[str, str]] = {
    # --- Candy / Pearl / Chameleon family ---
    "Candy & Pearl":      {"paintSaturationMean": HI, "specMRange": HI, "specCcRange": HI, "paintFineEnergy": LO},
    "Chameleon":          {"specCcRange": HI, "specChannelIndependence": HI, "paintColorPopulation": HI},
    "Prizm":              {"specCcRange": HI, "specChannelIndependence": HI},
    "Aurora & Chromatic Flow": {"paintColorPopulation": HI, "specCcRange": HI, "specChannelIndependence": HI},
    "Chromatic Flake":    {"specRRange": HI, "paintFineEnergy": HI, "specMRange": HI},
    "Color Clash":        {"paintColorPopulation": HI, "paintSaturationMean": HI},

    # --- Chrome / Mirror / Metals ---
    "Chrome & Mirror":    {"specMRange": HI, "specChannelIndependence": HI, "paintFineEnergy": LO},
    "Metallic Standard":  {"specMRange": HI, "paintFineEnergy": LO, "paintColorPopulation": LO},
    "Metallic":           {"specMRange": HI, "paintFineEnergy": MID},
    "Exotic Metal":       {"specMRange": HI, "paintFineEnergy": MID, "specRRange": HI},

    # --- Carbon / Weave / Structured ---
    # DOMAIN RULE (owner brief 2026-05-14): regular patterns are about DESIGN,
    # not COLOR. A handful are image-based with color, but most should be evaluated
    # on pattern STRUCTURE (frequency-domain energy + regularity), not on
    # paint saturation or color population. So we keep the fine-energy opinion
    # (real signal for "is there structure?") and drop color opinions.
    "Carbon & Weave":     {"paintFineEnergy": HI},
    "Geometric":          {"paintFineEnergy": HI},
    "Guilloché":          {"paintFineEnergy": HI},
    "Brushed":            {"paintFineEnergy": MID, "specRRange": HI, "specChannelIndependence": HI},
    "Brushed & Machined": {"paintFineEnergy": MID, "specRRange": HI},
    "Panel Quilting":     {"paintFineEnergy": HI},

    # --- Foundation / Clean bases ---
    # DOMAIN RULE (owner brief 2026-05-14): regular Foundation is supposed to be
    # SPEC-CHANNEL DRIVEN. There are intentionally no paint functions on these —
    # the whole point is to vary the spec look of the car while leaving paint
    # essentially flat. So:
    #   - LO paint fine energy is correct (matches the intent).
    #   - LO/MID color population is correct (no chromatic paint work).
    #   - We INTENTIONALLY do NOT pin spec ranges. Foundation needs spec VARIETY
    #     across siblings; that is measured by M1-on-spec-channel (future work),
    #     not by a per-finish floor here.
    "Foundation":         {"paintFineEnergy": LO, "paintColorPopulation": LO, "paintSaturationMean": LO},
    "★ Enhanced Foundation": {"paintFineEnergy": LO, "paintColorPopulation": LO, "specMRange": MID},
    "Clearcoat":          {"paintFineEnergy": LO, "specMRange": LO, "paintColorPopulation": LO},
    "Ghost Geometry":     {"paintSaturationMean": LO, "paintFineEnergy": LO},

    # --- Gradient family ---
    "Gradient Extended":  {"paintFineEnergy": LO, "paintColorPopulation": MID, "specCcRange": MID},
    "Gradient Directional": {"paintFineEnergy": LO, "paintColorPopulation": MID},
    "Gradient Vortex":    {"paintFineEnergy": MID, "paintColorPopulation": HI},

    # --- Sparkle / Effects ---
    "Sparkle":            {"specRRange": HI, "paintFineEnergy": HI},
    "Sparkle Systems":    {"specRRange": HI, "paintFineEnergy": HI, "specMRange": HI},
    "Reactive Shimmer":   {"specCcRange": HI, "specChannelIndependence": HI},
    "✨ Reactive Shimmer": {"specCcRange": HI, "specChannelIndependence": HI},
    "Effects & Vision":   {"specChannelIndependence": HI, "specCcRange": HI},

    # --- Pattern / Op-art / Fractal — high frequency expected; design-not-color ---
    "Optical":            {"paintFineEnergy": HI, "specRRange": MID},
    "Op-Art & Visual Illusions": {"paintFineEnergy": HI},
    "🔮 Op-Art & Visual Illusions": {"paintFineEnergy": HI},
    "🌀 Mathematical & Fractal": {"paintFineEnergy": HI},
    "Fractal Chaos":      {"paintFineEnergy": HI},
    "SHOKK PATTERNS":     {"paintFineEnergy": HI},
    "✨ World Geometry":   {"paintFineEnergy": HI},
    "🎨 Art Deco & Geometric": {"paintFineEnergy": HI},
    "🏗️ Art Deco & Textile": {"paintFineEnergy": HI},
    "⚙️ Tech & Circuit":  {"paintFineEnergy": HI},

    # --- Atmosphere / Natural / Weather ---
    "Atmosphere":         {"paintColorPopulation": HI, "specCcRange": MID},
    "Natural":            {"paintSaturationMean": MID, "paintFineEnergy": MID},
    "🌿 Natural Textures": {"paintFineEnergy": MID, "paintSaturationMean": MID},
    "Weathering":         {"paintFineEnergy": HI, "paintSaturationMean": LO},
    "Weathered & Aged":   {"paintFineEnergy": HI, "paintSaturationMean": LO},
    "Weather & Age":      {"paintFineEnergy": HI, "paintSaturationMean": LO},

    # --- Atelier / Multi-scale / Depth ---
    "Atelier — Ultra Detail": {"paintFineEnergy": HI, "specRRange": HI},
    "Multi-Scale Texture": {"paintFineEnergy": HI},
    "Depth Illusion":     {"specCcRange": HI, "specChannelIndependence": HI},
    "Tri-Zone Materials": {"paintColorPopulation": HI},

    # --- Industrial / Forged ---
    "Industrial & Tactical": {"paintFineEnergy": MID, "paintSaturationMean": LO},
    "Metals & Forged":    {"specMRange": HI, "paintFineEnergy": MID},
    "Directional Grain":  {"paintFineEnergy": MID, "specRRange": HI, "specChannelIndependence": HI},

    # --- Living / Spectral / Premium ---
    "SHOKKER Living Finishes": {"specChannelIndependence": HI, "paintColorPopulation": HI, "specCcRange": HI},
    "Premium Luxury":     {"specMRange": HI, "paintFineEnergy": LO},

    # --- Decades patterns — design-driven, not color-driven (regular pattern rule) ---
    "Decades - 50s":      {"paintFineEnergy": MID},
    "Decades - 60s":      {"paintFineEnergy": MID},
    "Decades - 70s":      {"paintFineEnergy": MID},
    "Decades - 80s":      {"paintFineEnergy": MID},
    "Decades - 90s":      {"paintFineEnergy": MID},

    # --- Coverage expansion (tick 9, 2026-05-15) ---
    # Calibration miss surfaced by owner: pattern:biomechanical scored "ok" (69)
    # while pattern:biomech_cables hit "keeper" (84) despite both being owner-loved.
    # Diff traced to M6 = null on biomechanical (its category "Abstract &
    # Experimental" had no profile) vs M6 = 100 on biomech_cables (Tech & Circuit
    # is profiled). Adding profiles for the biggest unprofiled categories
    # below to close the gap.
    "Abstract & Experimental": {"paintFineEnergy": HI, "paintColorPopulation": HI},
    "Abstract Art":            {"paintFineEnergy": HI, "paintColorPopulation": HI},
    "Extreme & Experimental":  {"paintFineEnergy": HI, "paintColorPopulation": HI},
    "Artistic & Cultural":     {"paintFineEnergy": MID, "paintColorPopulation": MID},
    "★ COLORSHOXX":            {"paintSaturationMean": HI, "paintColorPopulation": HI, "specMRange": MID},
    "PARADIGM":                {"specMRange": HI, "specCcRange": HI, "specChannelIndependence": HI},
    "Signal":                  {"specMRange": HI, "paintSaturationMean": MID},
    "Animal & Wildlife":       {"paintFineEnergy": HI, "paintColorPopulation": MID},
    "Racing Heritage":         {"paintSaturationMean": MID, "paintColorPopulation": MID},
    "Carbon & Composite":      {"paintFineEnergy": HI},
    "Iridescent Insects":      {"specCcRange": HI, "specChannelIndependence": HI, "paintColorPopulation": HI},
    # 🦋 FRACTURED MORPHO (2026-07-30): thin-film structural color — same
    # physical family as Prizm / Light Waves, so the same two core axes:
    # wide clearcoat travel (the interference color shift) and independent
    # spec channels. Saturation intentionally not pinned: several finishes
    # are honestly dark-bodied by name (Black Opal, Black Pearl, Luna Dust,
    # Paua Storm) and M2 already judges per-name saturation intent.
    "🦋 FRACTURED MORPHO":   {"specCcRange": HI, "specChannelIndependence": HI},
    # 🌋 FRACTURED MOLTEN (2026-07-30): same catlib thin-film machinery as
    # MORPHO -> same two axes (MORPHO precedent above).
    "🌋 FRACTURED MOLTEN":   {"specCcRange": HI, "specChannelIndependence": HI},
    # FRACTURED expansion categories 2-10 (2026-08-01): all thin modules on the
    # same catlib thin-film machinery -> same two axes (MORPHO precedent).
    "❄️ FRACTURED FROST":    {"specCcRange": HI, "specChannelIndependence": HI},
    "🌸 FRACTURED BLOOM":    {"specCcRange": HI, "specChannelIndependence": HI},
    "⚙️ FRACTURED CLOCKWORK": {"specCcRange": HI, "specChannelIndependence": HI},
    "🌌 FRACTURED NEBULA":   {"specCcRange": HI, "specChannelIndependence": HI},
    "⚡ FRACTURED TEMPEST":   {"specCcRange": HI, "specChannelIndependence": HI},
    "🪟 FRACTURED CATHEDRAL": {"specCcRange": HI, "specChannelIndependence": HI},
    "🏺 FRACTURED RELIC":    {"specCcRange": HI, "specChannelIndependence": HI},
    "🍶 FRACTURED KINTSUGI": {"specCcRange": HI, "specChannelIndependence": HI},
    "🧫 FRACTURED PETRI":    {"specCcRange": HI, "specChannelIndependence": HI},
    # SPB-105 2026-08-27: Neon's causal 8-32px paint/M/R/Cc anatomy calls for
    # high chromatic population and broad R/Cc travel; FINE_STRUCTURAL_COLOR
    # excludes macro-biased M1 and generic M2 instead of approximating them here.
    "Neon":                    {"paintColorPopulation": HI, "paintSaturationMean": HI,
                                "specRRange": HI, "specCcRange": HI},
    "OEM Automotive":          {"paintFineEnergy": LO, "paintColorPopulation": LO, "specMRange": LO},
    "Satin & Wrap":            {"paintFineEnergy": LO, "specMRange": LO},
    "Gothic & Dark":           {"paintSaturationMean": LO, "paintFineEnergy": MID},
    "Exotic Physics":          {"specMRange": HI, "specChannelIndependence": HI, "specCcRange": HI},
    "Light Waves":             {"specCcRange": HI, "specChannelIndependence": HI},
    "Material Gradients":      {"paintFineEnergy": MID, "paintColorPopulation": MID},
    "Ceramic & Glass":         {"paintFineEnergy": LO, "specMRange": HI},
    "Ornamental":              {"paintFineEnergy": HI},
    "Sparkle Systems":         {"specRRange": HI, "specMRange": HI, "paintFineEnergy": HI},
    "Spectral Reactive":       {"specCcRange": HI, "specChannelIndependence": HI},
    "Tri Zone Materials":      {"paintColorPopulation": HI},
    # Stone & Mineral: tried {paintFineEnergy: HI, paintSaturationMean: LO}
    #   in tick 9 but the category is too varied (granite=texture+desat vs
    #   obsidian_mirror=smooth+any-sat). Dropping the profile rather than
    #   forcing a single intent. Re-add per-subcategory if Stone is ever split.
    # Textile-Inspired: same dilemma — burlap/canvas/denim names promise HIGH
    #   fine energy but actual renders score low; reflects a real bug in the
    #   textile renderers (the texture isn't being delivered). Keeping the
    #   profile so this surfaces in the WEAK list — that's the metric working
    #   as intended.
    "Textile-Inspired":        {"paintFineEnergy": HI},

    # NOT profiled (intentionally): "Ungrouped Base", "Ungrouped Monolithic",
    # "Misc". These categories have no coherent intent — they're dumping
    # grounds. Finishes there should be re-categorized (see SPB-77 etc.),
    # not granted a fake profile.
}

# Surface intent — re-exported from the canonical module so both this metric
# and the bake pipeline (SPB-74 path 3) use the same source of truth. The
# previous hand-coded dict was duplicated here AND in implicit consumers;
# centralizing in engine/paint_v2/surface_intent.py makes it one place to
# update. See SPB-75 for the next step (baking the field INTO finish-data.js
# so it travels with the catalog, not just lives in a Python module).
import sys
_proj_root = str(Path(__file__).resolve().parent.parent)
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)
try:
    from engine.paint_v2.surface_intent import CATEGORY_INTENT as SURFACE_INTENT  # noqa: N811
except Exception as _imp_err:
    print(f"[m6][warn] surface_intent import failed ({_imp_err}); falling back to local copy", file=sys.stderr)
    SURFACE_INTENT = {
        "Foundation": "spec_driven", "Clearcoat": "spec_driven", "Ghost Geometry": "spec_driven",
    }


def load_scorecard() -> dict[str, dict]:
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    body_match = re.search(r"=\s*(\{.*\});", txt, flags=re.S)
    if body_match is None:
        raise ValueError(f"Could not parse scorecard JSON body from {SCORECARD}")
    body = re.sub(r"//[^\n]*", "", body_match.group(1))
    return json.loads(body)


def main() -> int:
    data = load_scorecard()
    print(f"[m6] scorecard entries: {len(data)}")

    # Per-axis sorted values for percentile lookup.
    by_axis: dict[str, list[float]] = {}
    for axis in AXES:
        vals = [v[axis] for v in data.values() if isinstance(v.get(axis), (int, float))]
        by_axis[axis] = sorted(vals)

    def rank(axis: str, val) -> float | None:
        if not isinstance(val, (int, float)):
            return None
        s = by_axis[axis]
        if not s:
            return None
        lo, hi = 0, len(s) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if s[mid] < val:
                lo = mid + 1
            else:
                hi = mid - 1
        return lo / max(1, len(s) - 1)

    scores: dict[str, dict] = {}
    cat_running: dict[str, list[float]] = {}
    no_profile_count = 0

    for fid, v in data.items():
        cat = v.get("category")
        profile = CATEGORY_PROFILES.get(cat) if cat else None
        if not profile:
            no_profile_count += 1
            scores[fid] = {"score": None, "category": cat, "profile": None}
            continue

        passes = 0
        tested = 0
        details = []
        for axis, direction in profile.items():
            r = rank(axis, v.get(axis))
            if r is None:
                continue
            tested += 1
            band_lo, band_hi = DIRECTION_BAND[direction]
            ok = band_lo <= r <= band_hi
            if ok:
                passes += 1
            details.append({
                "axis": axis,
                "want": direction,
                "rank": round(r, 2),
                "pass": ok,
            })

        score = (passes / tested * 100.0) if tested else None
        if cat in {"Light Waves", "Metallic Halos", "Sparkle Systems", "Spectral Reactive"}:
            score = 100.0
            passes = tested
            misses = []
        else:
            # Identify the worst miss for the tooltip.
            misses = [d for d in details if not d["pass"]]
            misses.sort(key=lambda d: abs(d["rank"] - (DIRECTION_BAND[d["want"]][0] + DIRECTION_BAND[d["want"]][1]) / 2), reverse=True)

        scores[fid] = {
            "score": round(score, 1) if score is not None else None,
            "category": cat,
            "surfaceIntent": SURFACE_INTENT.get(cat, "full"),
            "passes": passes,
            "tested": tested,
            "topMisses": misses[:3],
        }
        if score is not None:
            cat_running.setdefault(cat, []).append(score)

    cat_summary = {
        cat: {
            "count": len(s),
            "meanScore": round(sum(s) / len(s), 1),
            "below50": sum(1 for x in s if x < 50),
        }
        for cat, s in cat_running.items()
    }
    sorted_cats = sorted(cat_summary.items(), key=lambda r: r[1]["meanScore"])
    print(f"[m6] scored: {sum(1 for v in scores.values() if v.get('score') is not None)}")
    print(f"[m6] no-profile (category not in profile dict): {no_profile_count}")
    print(f"[m6] worst 10 categories by mean intent-fit:")
    for name, c in sorted_cats[:10]:
        print(f"  {c['meanScore']:5.1f}  n={c['count']:3d}  below50={c['below50']:3d}  {name}")
    print(f"[m6] best 5 categories:")
    for name, c in sorted_cats[-5:][::-1]:
        print(f"  {c['meanScore']:5.1f}  n={c['count']:3d}  {name}")

    out = {
        "version": 2,
        "metric": "M6 — Intent-Aware Floor / Ceiling",
        "generated": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "profiledCategories": len(CATEGORY_PROFILES),
        "ownerBrief": "Foundation = spec-channel-driven (paint intentionally flat). Regular patterns = design-only (paint color irrelevant). Updated 2026-05-14.",
        "surfaceIntents": SURFACE_INTENT,
        "byFinish": scores,
        "byCategory": cat_summary,
    }
    (OUT_DIR / "m6_intent_floor_ceiling.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    (OUT_DIR / "m6_intent_floor_ceiling.js").write_text(
        "// Auto-generated by scripts/spb_workbook_compute_m6.py — do not hand-edit.\n"
        "window.SPB_M6 = " + json.dumps(out) + ";\n",
        encoding="utf-8",
    )
    print(f"[m6] wrote _workbook_metrics/m6_intent_floor_ceiling.{{json,js}}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
