# SPB Finish Identity Contract

Status: mandatory ship evidence, 2026-09-01. This contract complements the
Owner's Finish Doctrine and M7; it does not replace either one.

## Per-finish contract

Every new or rebuilt finish must record these fields before promotion:

| Field | Required evidence |
|---|---|
| Name / promise | What the title says the user should perceive |
| Reference physics | The researched biological, optical, cultural, or fabrication process |
| Carrier grammar | The unique spatial construction—not its palette |
| Native anatomy | At least five purposeful 8–32px mark types and their roles |
| Material binding | Which named paint feature controls M, roughness, and clearcoat |
| Material tiers | The distinct per-feature states; not one global field |
| Nearest neighbors | Existing cards most likely to collide and the structural difference |
| Grayscale proof | Paint remains recognizable and distinct with color removed |
| Spec proof | Combined M/R/Cc and individual channels remain distinct with color removed |
| Picker proof | The actual live 96×48 card preserves the intended identity |
| Name-truth verdict | Visible features that communicate the title without relying on description copy |

## Automatic rejection conditions

- Same carrier with new colors, seed, phase, rotation, scale, or constants.
- Same low-frequency field dominating multiple cards.
- Paint is new but combined spec repeats an existing silhouette.
- Spec is colorful but unrelated to named paint anatomy.
- Description supplies the concept because the image does not.
- Isolated proof is distinct but the live standard/picker route is not.
- Color-invariant structural similarity is at least 0.68 to another category
  card without an explicit owner-approved shared-substrate exception.
- A candidate only raises category count; repeated designs do not count.

## Required comparison sequence

1. Inspect 2048² paint, combined spec, and individual M/R/Cc.
2. Inspect paint/spec at picker scale.
3. Compare grayscale, edges, and phase-insensitive spatial-frequency structure
   against every card in the category.
4. Inspect the live app assets and compare them to accepted evidence.
5. Run M7 and render-time gates.
6. Perform the hidden-title name test and record the verdict.
7. Promote only when every gate passes; then rebake both assets, sync the
   Electron runtime, refresh the backend, and update the Living Wiki.

Metrics identify collisions; they do not certify beauty. Owner-eye review is
the final authority and may reject any candidate regardless of score.

## Executable enforcement

This is not satisfied by a description in a ledger. Every new or rebuilt
renderer module must export an `IDENTITY_CONTRACT` using schema
`spb-finish-identity/1`. `scripts/spb_finish_identity.py` rejects the candidate
before M7 unless it declares all of the following:

- specific name/promise, researched mechanism and at least one source;
- unique paint carrier grammar and a separate spec grammar;
- a native range entirely inside 8–32px;
- at least five named, purposeful feature families;
- M, roughness and clearcoat each bound to two or more of those named features,
  with every feature participating in material response;
- at least six real material tiers;
- two or more nearest collision risks and the construction-level difference;
- at least three visible hidden-title proofs of the name;
- explicit construction and spec keys describing the mechanism.

The live rendered gate then tests the claim. Palette changes, M/R/Cc channel
swaps, translations, flips and rotations do not create a new design. A contract
can force the author to think, but it cannot certify the image; the actual
standard and picker assets remain the authority.

### Minimal module shape

```python
IDENTITY_CONTRACT = {
    "schema": "spb-finish-identity/1",
    "finish_id": "example_id",
    "display_name": "Example Name",
    "promise": "What must remain visible with the title hidden.",
    "reference_physics": {
        "mechanism": "The real biological or material process being modeled.",
        "sources": ["paper, museum, or primary technical source"],
    },
    "carrier_grammar": "Unique spatial construction, without mentioning color.",
    "spec_grammar": "How M/R/Cc trace that construction, not a house field.",
    "native_scale_px": [8, 32],
    "mark_types": [
        {"name": "feature_a", "role": "visible anatomical role"},
        {"name": "feature_b", "role": "visible anatomical role"},
        {"name": "feature_c", "role": "visible anatomical role"},
        {"name": "feature_d", "role": "visible anatomical role"},
        {"name": "feature_e", "role": "visible anatomical role"},
    ],
    "material_binding": {
        "M": ["feature_a", "feature_b"],
        "R": ["feature_c", "feature_d"],
        "Cc": ["feature_a", "feature_e"],
    },
    "material_tiers": ["tier_a", "tier_b", "tier_c", "tier_d", "tier_e", "tier_f"],
    "nearest_neighbors": [
        {"finish_id": "neighbor_a", "difference": "specific structural difference"},
        {"finish_id": "neighbor_b", "difference": "specific structural difference"},
    ],
    "name_truth": {
        "visible_evidence": ["proof one", "proof two", "proof three"],
        "hidden_title_verdict": "pass",
    },
    "construction_key": "mechanism-specific carrier key",
    "spec_key": "mechanism-specific material binding key",
}
```
