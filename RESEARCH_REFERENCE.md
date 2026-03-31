# SPB Research Archive — Reference Material

**Historical and foundational research findings.** For active steering research, see [RESEARCH.md](RESEARCH.md).

---

## RESEARCH-030: COLORSHOXX Session 1 — How iRacing's Renderer Creates Angle-Dependent Effects

**Date: 2026-03-30 | Agent: SPB Research Agent | Mission: Design COLORSHOXX real color-shift finishes**

### Executive Summary

iRacing's PBR pipeline creates angle-dependent color through **paint channel** (static color/topology) + **spec channel** (M/R/CC variation). The renderer does physics; we control the material properties.

### Core Discoveries

**Discovery 1: The "Field" Abstraction**
- Chameleon finishes use a 0-1 normalized "field" representing surface orientation
- M (metallic) = INVERSE to field → high M at grazing angles creates flash
- CC (clearcoat) = FOLLOWS field → creates gloss variation
- R (roughness) = independent flake-based variation

**Discovery 2: Spec Map Mechanics**
- M range: 195–255 (high M = mirror-like, low M = paint dominates)
- R range: 15–22 (low R = specular peaks, high R = matte scatter)
- CC range: 16–66 (CC=16 max gloss, >16 increasingly matte)

**Discovery 3: The Paint–Spec Marriage Principle**
1. **Paint:** Creates STATIC zones/gradients/cells with consistent RGB (don't simulate angle-dependence)
2. **Spec:** Uses same spatial structure, varies M/R/CC to control how zones render at different angles
3. **Renderer:** Applies PBR: Fresnel (angle-dependent on M), GGX (angle-independent on R), clearcoat (CC depth)
4. **Result:** Single car looks like different colors/metallics at different angles

**Discovery 4: structural_color.py Failure Analysis**
- ❌ Paint tried to simulate angle-dependence itself → too complex
- ✅ Solution: Paint creates static zones, spec varies M/R/CC per zone

### COLORSHOXX Finish Categories (5 Types)

1. **Single-hue intensity shifters** (Morpho-like) — one color, M varies (color shifts brightness at angles)
2. **Dual-tone flips** (ChromaFlair-like) — two zones with inverted M (red front, blue metallic side)
3. **Gradient reveals** — smooth gradient, M inverse (rotates appearance at angles)
4. **Zone-based multi-color** — 3–4 Voronoi cells, each with independent M/R/CC
5. **Temperature shifts** — warm↔cool gradient with R variation (matte warm, glossy cool)

---

## RESEARCH-001–029 Archive Stubs

Pre-2026-03-30 research entries (iRacing specs, competitive analysis, pattern roadmap, GGX audits, etc.) referenced in RESEARCH.md Active Findings Summary. Full entries maintained in Paperclip task history.

---

## For Future Reference

When archiving research:
- Keep foundational discoveries (principles, architecture explanations)
- Move implementation-specific details to task descriptions as work progresses
- Maintain backward links from RESEARCH.md "Active Findings Summary" to this file
- Archive by research age once entries become inactive (>14 days)
