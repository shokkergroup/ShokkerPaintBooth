// ============================================================
// PAINT-BOOTH-0-PICKER-OWNER-RATINGS.JS
// ============================================================
// Purpose:
//   Sparse owner/auditor override layer for picker rankings.
//
// Ranking order in the picker:
//   1. Explicit owner/auditor rating here
//   2. Measured catalog scorecard metrics
//   3. Generated metadata
//   4. Text heuristics fallback
//
// Use keys as "<type>:<id>" where type is base, monolithic, pattern, or
// spec_pattern. Scores are 0..100 and mirror the owner-requested categories.
// Keep this sparse. Only add entries when there is real owner/auditor signal.
// ============================================================
const PICKER_OWNER_RATINGS = {
  "monolithic:solar_wind": {
    status: "keeper",
    source: "owner brief 2026-05-06",
    notes: "Atmosphere keeper: aurora-like ribbons plus sparse particle energy.",
    scores: {
      patternDesign: 88,
      uniqueness: 86,
      specDetail: 82,
      renderTime: 78,
      intentFit: 92,
      sponsorSafety: 72,
      overall: 87
    }
  },
  "monolithic:volcanic_glass": {
    status: "keeper",
    source: "owner brief 2026-05-06",
    notes: "Atmosphere keeper: black glass, fracture, sheen, and HSB-reactive depth.",
    scores: {
      patternDesign: 86,
      uniqueness: 86,
      specDetail: 84,
      renderTime: 78,
      intentFit: 91,
      sponsorSafety: 70,
      overall: 86
    }
  },
  "monolithic:long_exposure": {
    status: "watch",
    source: "owner brief 2026-05-06",
    notes: "One of the stronger Effects & Vision directions, but still pending owner taste review.",
    scores: {
      patternDesign: 74,
      uniqueness: 76,
      specDetail: 62,
      renderTime: 72,
      intentFit: 82,
      sponsorSafety: 58,
      overall: 72
    }
  },
  "monolithic:x_ray": {
    status: "rework_spec",
    source: "owner brief 2026-05-06",
    notes: "Promising direction, but spec is only about one-third of the way there.",
    scores: {
      patternDesign: 68,
      uniqueness: 78,
      specDetail: 36,
      renderTime: 72,
      intentFit: 84,
      sponsorSafety: 52,
      overall: 61
    }
  },
  // Ghost Geometry review — owner workbench 2026-05-16. Universal note:
  // 2048² canvas covers a whole car, so any pattern at "looks right" thumbnail
  // scale is ~8× too coarse on a real body. Default target: 20% of current
  // feature size, denser. Spec channels should use many shades (micro color
  // shifts) instead of one solid color to make finishes "pop".
  "monolithic:ghost_camo": {
    status: "keeper",
    source: "owner workbench 2026-05-16",
    notes: "Close enough."
  },
  "monolithic:ghost_circuit": {
    status: "rework_spec",
    source: "owner workbench 2026-05-16",
    notes: "VERY COOL - needs more detail and slightly smaller pattern. Heat signatures should vary across spec (hotter/cooler regions) so reds/pinks pop dynamically instead of uniform."
  },
  "monolithic:ghost_diamonds": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Diamond pattern way too large. ~20% current size with many more of them."
  },
  "monolithic:ghost_fracture": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Rework pattern + spec completely. Doesn't feel like a 'fracture' — too weak overall."
  },
  "monolithic:ghost_hex": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Hex cells way too big. Effect itself is great with multi-color spec coming through — need cells at ~20% current size, much higher density."
  },
  "monolithic:ghost_quilt": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Pattern too large. ~20% current size."
  },
  "monolithic:ghost_scales": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Don't like pattern. Also too large."
  },
  "monolithic:ghost_stripes": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Wavy lines too wide. ~75% current width, more of them across the canvas."
  },
  "monolithic:ghost_vortex": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Needs more vortex detail and a more dynamic spec map."
  },
  "monolithic:ghost_waves": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Waves too big."
  },
  // Depth Illusion review — owner workbench 2026-05-16. Universal verdict:
  // 11/11 reject. Category-level redesign needed, not per-finish tweaks.
  // Common faults: patterns way too large (SPB-99 doctrine), spec channels
  // monotone (SPB-99 principle 2), and several finishes don't actually
  // EVOKE their name (depth_ripple no water feel, depth_scale no scale feel,
  // depth_wave not ocean-like). Some look low-quality / pixelated at 2048².
  // Depth Illusion ROUND 2 review — owner workbench 2026-05-16 (tick 91→92).
  // 4 finishes moved from reject → watch (erosion, pillow, ripple, scale).
  // 7 finishes still reject; pattern is "renders look better but not enough
  // change" — triggers the SPB-105 universal 85% rule (rebuild until ≥85).
  "monolithic:depth_bubble": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Need about 3X more bubbles AND we have to be mindful of RENDER TIMES - they can't be too long. This one clocked at nearly 20 seconds. RENDERS should take about 2-3 seconds for a standard finish without all the extra bells and whistles (layer stacking, zone overlays, etc)."
  },
  "monolithic:depth_canyon": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Just does not scream Canyon at all. Really disappointing. Sparse, uninspired."
  },
  "monolithic:depth_crack": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "STILL about 75% too big with those crack patterns. Looks HUGE on the cars."
  },
  "monolithic:depth_erosion": {
    status: "watch",
    source: "owner workbench 2026-05-16",
    notes: "Moved from reject → watch tick 92."
  },
  "monolithic:depth_honeycomb": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "STILL looks pixelated? SOMETHING way off here."
  },
  "monolithic:depth_map": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "DEPTH should entail a 3D look. Like the car is physically growing OUTWARD. Depth map should have spec effects that literally make the car look like it has ridges, peaks, valleys, etc. Like the topography on a map. Need a lot more spec work or just better paint finish to accomplish."
  },
  "monolithic:depth_pillow": {
    status: "watch",
    source: "owner workbench 2026-05-16",
    notes: "Moved from reject → watch tick 92."
  },
  "monolithic:depth_ripple": {
    status: "watch",
    source: "owner workbench 2026-05-16",
    notes: "Moved from reject → watch tick 92."
  },
  "monolithic:depth_scale": {
    status: "watch",
    source: "owner workbench 2026-05-16",
    notes: "Moved from reject → watch tick 92."
  },
  "monolithic:depth_vortex": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Instead of a 4 square tiling effect it should be a bit more abstract looking."
  },
  "monolithic:depth_wave": {
    status: "reject",
    source: "owner workbench 2026-05-16",
    notes: "Just not enough going on."
  }
};

if (typeof window !== 'undefined') window.PICKER_OWNER_RATINGS = PICKER_OWNER_RATINGS;
