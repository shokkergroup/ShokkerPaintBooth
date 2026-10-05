# DLM Template Adapter v1 Package

This is the stable, livery-neutral execution package for the official iRacing Dirt Late Model 350/358/438 UV layout.

- Adapter schema: `shokk-forge.template-adapter/v1`
- Package version: `10`
- Canvas: 2048 x 2048
- Masks: 14 official-template-derived, mutually owned surface masks
- Ownership: `exclusive_nearest_unique_core/v1`; the v3 promotion removed 35,080 overlapping claims while preserving the complete paintable union
- Calibration source: `_forge_out/codex_universal_adapter/run_17_dlm_multisurface_calibration/`
- Promotion evidence: Mountain Dew and Miller side calibration, then Waffle/Friday/Sex Wax/Domino cross-car front and ownership controls
- Direct-top execution: hood, roof, and rear deck consume adapter-declared cyclic quads from clean isolated panel components when present; qualified sheets are detected without livery identity, presentation frames are rejected, enclosed white paint is preserved, and stored rotations are applied without reflection
- Direct-top promotion: Waffle active + Friday/Sex Wax controls + withheld Domino, 12/12 executed, 2,813,119 unique UV pixels, zero overlap/reflection/duplicate physical instances, minimum containment 1.0 and minimum owned-mask coverage 0.893309 (`app_integration/cycle_32/direct_top_audit_v8`)
- Direct outside-spoiler execution: a wide, shallow, framed panel component disjoint from the assembled rear view supplies `spoiler_outside_quad`; whole-role anchoring no longer lets the deliberately unseen inside face block this directly observed physical surface. The quad is still review-only, reflection-forbidden, hash-bound, and clipped to the exclusive official outside-spoiler mask.
- Qualified front-valance execution: a unique wide/shallow component disjoint from the assembled front view supplies only `front_valance_quad`. A livery-neutral lower-band edge establishes `valance_top_y`; the piecewise scanline projector maps that narrow physical strip into the official nose mask, excludes mandatory pixels, forbids reflection, and never consumes the assembled or isolated hood artwork. Full-nose inverse readiness remains false. Promotion proof is Waffle active + Friday/Sex Wax controls + withheld Domino: 4/4, 59,059 unique UV pixels, zero overlap/mandatory/reflection/duplicate physical instances.
- Partial-surface completeness: an executed qualified subprojector persists its authority-hashed pixels as `surface_completion=partial`, but cannot increment the complete-surface count or unlock semantics/PSD/Import. The projection plan names both the completed scope and the remaining physical scope as a correction requirement.
- Optional surface evidence: the adapter declares livery-neutral `front_corner_left`, `front_corner_right`, and `rear_inside` roles with physical scope, correction triggers, confidence thresholds, prohibited substitutes, exact capture guidance, and required user capture attestation. A slot upload begins below the 0.85 gate and only reaches 0.90 after its hash-bound capture contract is confirmed. Generic front/rear/side views cannot satisfy these roles, and byte-duplicate uploads remain rejected evidence.
- Specialized surface review: every optional role now declares a normalized TL/TR/BR/BL quadrilateral contract. The full-image quad shown by the page is only an explicit review seed (`seed_is_authority=false`); persistence requires a convex, positive-area manual confirmation bound to the exact reference hash, adapter hash, role, physical scope, and target surface. These records remain separate from projection anchors until a calibrated adapter projector consumes them.
- Capture integrity and replacement review: each specialized role declares minimum decode/resolution and reviewed-face pixel requirements. Only spatial integrity is a hard gate; contrast, edge energy, shadow, and highlight observations stay advisory so legitimate livery appearance is never rejected. The app compares selected and candidate sources side by side, rejects undersized replacements before attestation, and preserves the current authority until explicit supersession.

The package contains geometry and UV truth only. It must never contain a livery name, sponsor, color, filename rule, or per-livery placement. `mask_sha256` inside `adapter.json` is the authority for every mask used by the in-app executor.

Execution fails closed when a mask is missing, has the wrong hash/size, a required anchor is absent, a projector is not adapter-approved, or generated pixels escape their owned surface.
