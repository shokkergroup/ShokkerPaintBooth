# -*- coding: utf-8 -*-
"""Surface intent — canonical category→intent mapping.

**This is the source of truth.** All consumers (M6 metric, thumbnail bake
pipeline per SPB-74/SPB-75, picker UI heuristics) MUST read from here.
Hand-coded duplicates of this mapping in individual scripts are bugs.

OWNER DOCTRINE (briefs 2026-05-14 and 2026-05-15):

1. **Foundation, Clearcoat, Ghost Geometry, Enhanced Foundation, Enhanced
   Foundation Exotic** are SPEC-CHANNEL-DRIVEN. There are intentionally no
   paint functions on these — the whole point is to vary the spec look of
   the car while the paint stays essentially flat.

   **CRITICAL CLARIFICATION (added 2026-05-15 tick 33, SPB-86):** "Spec-
   channel-driven" is satisfied two different ways depending on the
   category:

   * **Classic Foundation:** the spec channel is FLAT WITHIN each finish.
     Variation between finishes comes from the per-finish material
     constants (M / R / CC). This is the **painter contract** dated
     2026-04-21 (`shokker_engine_v2.py` lines 12698-12715, `_SPEC_FN_
     EXPLICIT_WIN_F1`): "Visible grain/weave/flake belongs in a Pattern
     or Spec Pattern Overlay, NOT a Foundation." Adding procedural
     spatial variation to `f_chrome` / `f_brushed` / `f_metallic` /
     `f_carbon_fiber` / `f_pearl` REVERTS the painter fix. Don't.

   * **★ Enhanced Foundation, ★ Enhanced Foundation Exotic, Ghost
     Geometry, Clearcoat:** spec varies spatially WITHIN each finish.
     This is where the owner's "boring spec = boring car" brief actually
     applies. Procedural spatial structure (multi-band noise, Voronoi
     cells, lognormal sparkle, etc.) is doctrine-required here.

   A spec-richness audit (`scripts/audit_spec_driven_spec_richness.py`)
   that flags spatial flatness should therefore SKIP Classic Foundation
   and only enforce the floor on the second group.

2. **Regular patterns** (Carbon, Geometric, Op-Art, Decades, Tech & Circuit,
   Guilloché, World Geometry, Art Deco, Panel Quilting, etc.) are about
   DESIGN, not COLOR. Pattern quality lives in pattern STRUCTURE (frequency-
   domain energy + regularity), not in color count or saturation. A handful
   of image-based patterns DO carry color but those are exceptions.

3. **Bases, Monolithics, Effects** (the bulk of the catalog) use both
   paint AND spec to deliver their character.

INTENT VALUES:

* ``spec_driven`` — paint intentionally flat; all character in spec.
* ``pattern_design`` — paint structure matters, paint color does not.
* ``pattern_image`` — image-backed patterns that DO carry color
  (small subset; owner has the canonical list).
* ``fine_structural_color`` — fine authored paint marks whose visibility and
  color exchange are driven by independent spec channels. M1's macro-biased
  image hash and M2's stationary name vocabulary are non-applicable; explicit
  feature-scale/semantic/color-travel gates carry those responsibilities.
* ``full`` — default. Both paint and spec carry character.

IMPLICATIONS for downstream consumers:

* **Thumbnail bake (SPB-74 path 3):** for ``spec_driven`` finishes, render
  the spec channel directly (paint-only thumbnail is flat gray for these,
  which produces the 587-megaclone). See ``scripts/bake_efx_spec_previews.py``
  for the reference pattern. For ``pattern_design`` finishes, paint-channel
  bake is fine but should be done over a neutral substrate so paint color
  doesn't dominate. For ``full``, current bake is correct.
* **M6 metric** (``scripts/spb_workbook_compute_m6.py``): per-category
  profiles must respect the intent — e.g. Foundation profile pins LOW
  paint variation but has NO opinion on spec (Foundation spec should vary).
* **Picker UI:** could surface a small "intent" badge so painters know
  what dimension the finish actually controls.

Related Linear:
* SPB-74 — bake-pipeline fix using this mapping (path 3)
* SPB-75 — bake this mapping INTO paint-booth-0-finish-data.js so it
  travels with the data instead of living only in one Python module
"""
from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Intent values (string literals for forward compat with simple JSON)
# ---------------------------------------------------------------------------
SPEC_DRIVEN: str    = "spec_driven"
PATTERN_DESIGN: str = "pattern_design"
PATTERN_IMAGE: str  = "pattern_image"
FINE_STRUCTURAL_COLOR: str = "fine_structural_color"
FULL: str           = "full"


# ---------------------------------------------------------------------------
# Category → intent map.
#
# Update this dict when adding a new category. Default for unknown
# categories is `full` (safe baseline — every metric stays valid).
# ---------------------------------------------------------------------------
CATEGORY_INTENT: dict[str, str] = {
    # --- SPEC-DRIVEN: paint stays vanilla, spec does the work ---
    "Foundation":              SPEC_DRIVEN,
    # FOUNDATION ONE (owner 2026-09-03): ★ Enhanced Foundation retired (its spec was
    # flat anyway); the EFX shelf now carries its own paint + spec, so it is FULL.
    "Foundation EFX":          FULL,
    "Clearcoat":               SPEC_DRIVEN,
    "Ghost Geometry":          SPEC_DRIVEN,

    # --- FINE STRUCTURAL COLOR: explicit micro topology + spec angle travel ---
    # SPB-WILDS 2026-08-23 tick 7. Owner doctrine requires 8-32px features and
    # rejects M7's macro-structure incentive. These four lanes retain normal
    # paint thumbnails (unlike spec_driven), retain clone penalties, and are
    # judged by current paint/spec coherence + the explicit category material
    # contract. Permanent suites separately enforce six semantic glyphs,
    # feature scale, uniqueness, eight tiers, and chromatic angle exchange.
    "👣 FRACTURED CRYPTID":    FINE_STRUCTURAL_COLOR,
    "🦋 FRACTURED MORPHO":     FINE_STRUCTURAL_COLOR,
    "🌸 FRACTURED BLOOM":      FINE_STRUCTURAL_COLOR,
    "🧫 FRACTURED PETRI":      FINE_STRUCTURAL_COLOR,
    # SPB-105 2026-08-27: Neon's authored 8-32px color features and independent
    # M/R/Cc tiers share causal masks. Macro-rewarding M1 and generic M2 are
    # inapplicable; category M6 plus permanent scale/material gates carry intent.
    "Neon":                    FINE_STRUCTURAL_COLOR,
    # SPB-105 / ASTRA A3: 8-32px authored geometry and feature-bound materials.
    # Keep normal paint thumbnails and clone penalties; the invariant rendered
    # similarity gate replaces macro-biased dHash as the identity ship gate.
    "ASTRA":                   FINE_STRUCTURAL_COLOR,

    # --- PATTERN_DESIGN: pattern structure matters, paint color irrelevant ---
    # (Owner brief 2026-05-14: "regular patterns are about DESIGN not COLOR.")
    "Carbon & Weave":          PATTERN_DESIGN,
    "Carbon & Composite":      PATTERN_DESIGN,
    "Geometric":               PATTERN_DESIGN,
    "Guilloché":               PATTERN_DESIGN,
    "Panel Quilting":          PATTERN_DESIGN,
    "Optical":                 PATTERN_DESIGN,
    "Op-Art & Visual Illusions": PATTERN_DESIGN,
    "🔮 Op-Art & Visual Illusions": PATTERN_DESIGN,
    "🌀 Mathematical & Fractal": PATTERN_DESIGN,
    "Fractal Chaos":           PATTERN_DESIGN,
    "SHOKK PATTERNS":          PATTERN_DESIGN,
    "✨ World Geometry":        PATTERN_DESIGN,
    "🎨 Art Deco & Geometric": PATTERN_DESIGN,
    "🏗️ Art Deco & Textile":  PATTERN_DESIGN,
    "⚙️ Tech & Circuit":       PATTERN_DESIGN,
    "Decades - 50s":           PATTERN_DESIGN,
    "Decades - 60s":           PATTERN_DESIGN,
    "Decades - 70s":           PATTERN_DESIGN,
    "Decades - 80s":           PATTERN_DESIGN,
    "Decades - 90s":           PATTERN_DESIGN,
    "Ornamental":              PATTERN_DESIGN,
    "Artistic & Cultural":     PATTERN_DESIGN,  # SPB-94 tick 72: was pattern_image

    # --- PATTERN_IMAGE: image-based patterns that DO carry color ---
    # SPB-94 tick 72: removed "Artistic & Cultural" — only 1 of 17 finishes
    # (tribal_celtic_spiral) actually carries its own color. The rest are
    # pattern_design pass-through. Single exception lives in FID_INTENT_OVERRIDE.
    "Cultural":                PATTERN_IMAGE,
    # Specific known image-backed sub-families that often live as patterns
    # but DO carry color information (Viva Mexico, Union Jacked, Rising Sun,
    # Mortal Shokk per VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md).

    # All other categories default to `full` via DEFAULT_INTENT.
}


# SPB-94 tick 72: per-finish overrides for cases where the category-level
# intent is wrong for a specific finish. Keyed by "<surface>:<id>". Use
# sparingly — the category mapping is the doctrine source of truth.
FID_INTENT_OVERRIDE: dict[str, str] = {
    # tribal_celtic_spiral: only "Artistic & Cultural" finish that carries
    # its own color (chroma audit tick 66: cosine 0.66 vs 1.0000 for all
    # other entries in that category). Genuinely pattern_image.
    "pattern:tribal_celtic_spiral": PATTERN_IMAGE,
}


DEFAULT_INTENT: str = FULL


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_intent(category: Optional[str], fid: Optional[str] = None) -> str:
    """Return the surface intent for a category. Falls back to ``full``.

    SPB-94 tick 72: when ``fid`` is provided, check ``FID_INTENT_OVERRIDE``
    first so per-finish exceptions trump the category mapping. Existing
    callers that pass only ``category`` continue to work unchanged.
    """
    if fid and fid in FID_INTENT_OVERRIDE:
        return FID_INTENT_OVERRIDE[fid]
    if not category:
        return DEFAULT_INTENT
    return CATEGORY_INTENT.get(category, DEFAULT_INTENT)


def is_spec_driven(category: Optional[str]) -> bool:
    """True iff the category's intent is SPEC_DRIVEN.

    Use this from the thumbnail bake pipeline (SPB-74 path 3) to decide
    whether to render the paint channel or the spec channel as the
    canonical preview.
    """
    return get_intent(category) == SPEC_DRIVEN


def is_pattern_design(category: Optional[str]) -> bool:
    """True iff the category's intent is PATTERN_DESIGN.

    Patterns of this type should be evaluated on pattern structure
    (frequency content, regularity) not on paint color or saturation.
    """
    return get_intent(category) == PATTERN_DESIGN


def is_pattern_image(category: Optional[str]) -> bool:
    """True iff the category contains image-backed patterns that carry color."""
    return get_intent(category) == PATTERN_IMAGE


__all__ = [
    "SPEC_DRIVEN", "PATTERN_DESIGN", "PATTERN_IMAGE", "FINE_STRUCTURAL_COLOR", "FULL",
    "CATEGORY_INTENT", "DEFAULT_INTENT",
    "get_intent", "is_spec_driven", "is_pattern_design", "is_pattern_image",
]
