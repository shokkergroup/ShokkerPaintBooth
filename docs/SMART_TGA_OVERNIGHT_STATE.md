# Smart TGA Overnight State - Cycle 740

## Honest outcome

- **A real reusable offline proposal capability improved paint-disjoint DLM number-core availability; customer/runtime output did not change.** Apply remains locked.
- Cycle739's `5/6` clean-core claim was wrong. Direct visual re-audit found its selected `270265` mask was lime body paint and its selected `275580` mask was livery. The corrected baseline is **4/6**; `275580` has a different clean palette proposal. Correction: `_smart_tga_runs/cycle740_edge_assembly_acceptance_v1/corrected_cycle739_selected_labels.json`.
- Added generic Lab edge-enclosed regions plus aligned-component groups to `scripts/smart_tga_anchor_free_instance_assembler.py`. Each proposal is immutable and preserves its mask/bbox/provenance. It has zero semantic, ownership, and output authority.

## Measured behavior

- Untouched/frozen holdout: target `358/270265`; controls `271152`, `272579`, `275580`, `277230`, `279330`.
- Corrected clean-core availability: **4/6 -> 6/6** (+33.3 points).
- `270265`: clean `97` isolated from the lime/cyan body field at raw panel rank **1** (`door_number_lower_side:E:G0:9f24bf91dc23`).
- `279330`: clean grouped `327` excludes the same-color Sponsor strip. It is raw rank 75, exact-family rank 13, and shadow learned rank **6**.
- Every emitted edge bbox was visually reviewed: **52/52** = 11 clean grouped cores + 37 Number fragments + 4 Sponsor/logo hard negatives; 48/52 (92.31%) are Number evidence. New authority accepts: **0**.
- The learned ranker moves clean-core top-12 recall **5/6 -> 6/6**, but stays shadow-only with zero rescue slots because its experimental additions included Paint/uncertain candidates. This is a measured safety blocker, not a release claim.
- Focused assembler **10/10** and focused+shared **33/33** passed; compile passed. Electron sync/live proof are not applicable because default runtime did not change.

## Architecture and safety

- Edge generation is generic: Canny evidence across Lab channels, closed/dilated barriers, enclosed non-border regions, then aligned component grouping. No filename/car/bbox exception or global OCR weakening.
- Cross-panel corroboration now computes on exact-mask families and fans evidence back to every immutable proposal, removing duplicate quadratic work without discarding provenance.
- Exact reconstruction, legacy fallback, apply lock, and instant rollback remain intact.

## Exact next engineering step

1. Train/calibrate an abstaining edge-family semantic scorer on the 52 durable labels so `279330` safely enters review top-12 while its four roof-logo Sponsor negatives abstain.
2. Add a provenance-tracked named-logo identity adapter as corroboration only: independent DLM references, D4/color-tolerant retrieval, known/unknown/true-Number gates. A logo match may strengthen Sponsor evidence but cannot create ownership.
3. Only if active learning identifies missing coverage, use next unused DLM358: `car_num_282271.tga`, `286176`, `288622`, `293480`, `296559`, `302683`.

## Evidence

- Acceptance: `_smart_tga_runs/cycle740_edge_assembly_acceptance_v1/acceptance_ledger.json`
- Edge labels: `_smart_tga_runs/cycle740_edge_assembly_acceptance_v1/reviewed_edge_proposal_labels.json`
- Selected cores: `_smart_tga_runs/cycle740_edge_assembly_acceptance_v1/selected_clean_core_labels.json`
- Shadow ranks: `_smart_tga_runs/cycle740_edge_ranker_holdout_v1/ranked_family_ledger.json`
- Target visual: `_smart_tga_runs/cycle740_edge_assembly_target_270265_v2/dirtlatemodel_358_car_num_270265_review.png`

No commit, push, reset, deletion, packaging, publication, runtime change, or unrelated edit.
