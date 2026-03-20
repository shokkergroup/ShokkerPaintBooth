# Roadmap #3 - Smart Pattern System (Car-Aware Mapping)

**Created:** 2026-03-13 23:26:25 (local)  
**Status:** Planning-ready reference  
**Owner intent:** Pattern math should adapt to car mask/body layout automatically instead of forcing one-size-fits-all mapping.

## Goal
Build a car-aware pattern mapping system that understands model-specific UV/body semantics (hood, roof, sides, front, rear) and adjusts pattern scale/orientation/gradient direction to produce consistent results across different iRacing templates.

## Core Concept
Introduce a `car_profile` layer that maps paint-space pixels to semantic parts, then drive pattern transforms by those semantics before final compositing.

## Product Requirements
- Support profile-aware pattern placement for at least one launch family (NASCAR trucks).
- Preserve current manual controls while offering an automatic mode.
- Let users override auto behavior per zone when needed.
- Make gradients and directional effects align to logical car flow (front->back, roof->hood, etc.).

## Data Model (Draft)
- `car_profile_id`: e.g., `nascar_truck_chevy`.
- `semantic_map`: per-pixel part IDs or vector fields:
  - `hood`, `roof`, `left_side`, `right_side`, `front`, `rear`, etc.
- Optional transform hints:
  - default orientation, anisotropy, mirroring rules.

## Engine Design Direction
- Add optional `car_profile` input to render pipeline.
- During pattern sampling:
  - Read semantic region at pixel.
  - Apply per-region transform policy (scale/rotation/offset flow).
  - Blend boundaries with soft transitions to avoid seams.
- Keep fallback to current global UV behavior when no profile is active.

## Frontend Design Direction
- New section in zone controls:
  - `Pattern Mapping Mode`: `Classic` / `Smart`.
  - `Car Profile`: dropdown when smart mode enabled.
  - Optional per-zone override toggles.
- Visual preview overlay for semantic regions (debug mode).

## Phase Plan
- **Phase A (MVP):** profile schema + one truck profile + smart gradients only.
- **Phase B:** smart mapping for procedural + image patterns.
- **Phase C:** profile pack system and community-shared profiles.

## Risks / Guardrails
- Profile authoring complexity -> start with one highly validated profile.
- Seam artifacts across UV islands -> blend margins and directional continuity checks.
- Runtime overhead -> precompute profile transforms and cache.

## Acceptance Criteria
- Same pattern preset gives visually coherent placement on supported truck templates.
- Smart mode can be toggled off to recover current behavior instantly.
- No major performance regression on standard renders.
