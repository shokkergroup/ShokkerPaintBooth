# Tools improvement: revised working method

**Owner efficiency and space correction, 09-08:** use private headless regressions for repeatable state/layout, compact results and one scoped visual check; retain foreground interaction for performance evidence. Training Wheels is now opt-in and corner-mounted; the center-docked guide described below was rejected. [Current workflow and proposed local MCP pilot](SPB_DEVELOPER_BRIDGE_PROPOSAL_2026-09-08.md).

**Owner correction:** the earlier broad completion claim is withdrawn. Ordinary Brush and the visible cross-layer Select Object route had not passed the owner's workflow. Current changes, accepted native evidence, rejected intermediate evidence and remaining limits are in [Tools owner corrections](TOOLS_OWNER_CORRECTIONS_2026-09-08.md). Test the visible route and actual gesture before accepting a command; a callable handler alone is insufficient. Use foreground Chrome—background managed tabs throttle animation frames and invalidate latency comparisons. The owner now authorizes a visual Pick Color magnifier; its sampling logic stays unchanged.

Owner steering09-08: review HOW this goal is being pursued and change the method where useful; desktop Chrome/full-window testing authorized. The original functionality, Photoshop-style behavior, responsiveness and simplification requirements remain unchanged. Pick Color remains exactly unchanged.

## Assessment

Useful work already completed: real mutation/Undo defects repaired; named feature regressions and native pixel evidence; dedicated helpers rather than another large embedded tool; isolated output paths and root/Electron consistency. Keep these practices.

The process was inefficient: repeated small fixture rounds, oversized accessibility responses, accumulating speculative edge cases, inconsistent document/view sizes for performance comparisons, and insufficient prioritization of whole painting workflows. Passing local geometry tests was sometimes followed by another narrow test rather than closing a tool's acceptance row. The running report grew into a chronology, making the next task harder to choose. Correct this now.

## Authoritative test setup

Primary interaction workspace: Chrome tab1654209478, `http://localhost:59880/?spb-tool-audit=1`, actual desktop viewport1920×959. This isolated server serves current root code; its output isolation prevents routine tests from deploying to owner iRacing folders. Use59876 when comparing the owner's running app is necessary; no reason to restart or mutate that server merely to test current root code.

Native09-08 measurement: the Chevy starter SOURCE is458px wide in desktop Chrome. The previous in-app512px-fixture view was182px wide. This gives roughly6.3× the editing area, though these are different documents/UI states and are not a performance A/B comparison. Use fixed document, zoom, panel state and input gesture for subsequent comparisons.

Concrete usability finding: `spbGuidePanel` occupies x1574–1904,y370–899; Layers occupies x1655–1910,y119–959. Guide overlap covers249 of255 Layer-panel pixels horizontally and529px vertically. The guide hides the controls the painter needs. Prioritize this over speculative rare cases. Chrome also shows Easy with Layer/Wire active while Zone instructions ask the painter to pick body color; verify and clarify this workflow without changing Pick Color behavior.

## Work order

1. **Workspace and first useful result:** make the next action clear; keep the guide from obstructing Layers; verify import → choose intended target → select an area → apply finish → isolated render → reopen. Preserve every existing Zone/Layers/SHOKK option.
2. **Common editing loop:** on the same real Chevy PSD, select a sponsor/number, move/scale/rotate, retouch, adjust, undo/redo and save/reopen. Cover the actual visible commands in Select, Retouch, Mask, Spec Tools, Transform and Adjust; record each as accepted, failed or pending.
3. **Large-document responsiveness:** real4096px layered paint plus the controlled4096 two-layer ORA only for isolating a demonstrated issue. Measure event-to-first-frame, during-stroke gaps, release delay and post-edit preview separately. Automation call duration is not app latency.
4. **Release regression:** once changed workflows pass, run relevant existing contracts and one integrated output/persistence check. Repeat only after a material change, new failure or unresolved discrepancy.

Pixel loss, wrong-target edits, broken Undo or source/save corruption interrupt this order and are fixed immediately. Existing advertised features still require acceptance; avoid inventing additional Photoshop features or unbounded combinations as new goal requirements.

## Finite acceptance contract

For each existing command, confirm its advertised successful action in the intended context, unavailable/locked-target behavior where applicable, and the relevant Cancel/Undo/Redo result. Use one representative action per command; use shared invariant tests for common infrastructure rather than replaying every command against every image size and modifier combination. Add a specific case when evidence identifies a distinct failure.

- Select/Mask: correct selected pixels; correct additive/subtractive behavior on representative shared paths; image unchanged; mask history correct.
- Retouch: correct editable target and affected pixels; visible in-stroke feedback; no unintended alpha/mask changes; exact Undo.
- Spec Tools: actual rendered M/R/Cc changes agree with controls; intended source paint preserved; Cancel/Undo restore configuration and output.
- Transform: matching live and applied position/size/rotation, expected handle anchoring and modifiers, linked behavior that the app exposes, exact cancellation/history. Numeric fields agree with the live artwork.
- Adjust: control values, live preview and Apply agree; selection respected; Cancel/Undo exact; unavailable targets explain the next action.
- Simplification: a fresh-session path reaches a correct saved/rendered result without hidden targets, blocked controls, overlapping essential panels or unexplained mode changes. Existing advanced functions remain reachable.

Completion requires all existing command rows plus the integrated workflows, preserved Pick Color, output correctness and resolved demonstrated latency defects. Passing counts alone are never the release claim. The existing tools report retains evidence; this method document sets how to finish the goal without endlessly widening the test matrix.

## Measurement and context discipline

Reproduce visibly, state expected behavior, identify the smallest shared cause, patch a dedicated owner module, verify the original failure and adjacent invariant, then move on. Keep one current acceptance ledger, one evidence entry per repair and the consolidated Wiki log. Do not rewrite history or rerun successful suites without a reason.

Use a native gesture for human interaction evidence, contracts for deterministic math/races and saved outputs for render/export evidence. UI internal export-composite checks are valuable but must not be described as downloaded-file proof. If a performance change is proposed, use the same workload before/after and a small repeated sample (e.g.3 runs), recording document, brush/selection, zoom, panel state and preview workload. Investigate visible stalls and instrument only the responsible path. Do not claim a gain from a single different-fixture timing.

Retain browser handles across turns; use scoped DOM/AX slices after the initial snapshot. Do not reset healthy sessions or recreate tabs on every pass. Keep inactive views from running competing previews during a performance benchmark. Revalidate a timed-out handle before considering it dead.

## Completion status

The finite acceptance contract is satisfied for the existing tool set. All40 named toolbar actions and10 Zone instance commands have representative evidence in `_tools_simplification_work/tool-command-acceptance-20260908.json`. Earlier repair notes in the chronological report are superseded by this status and the ledger.

Completed Zone material Tint/Replace/Hue/Saturation/Vibrance and positive Sync/Re-apply. Color actions operate on owned paint and preserve raw spec/coverage/placement, with one batched native/preview capture pair per group and one atomic Undo. Chrome4096 Chevy: Hue58,965/Tint58,932/Saturation57,476/Vibrance13,487 preview paint pixels change only inside the copy; spec exact. Replace/Sync/Re-apply restore baseline exactly; Hue Undo/Redo and project reopen exact;11 Layers and stored regionMask unchanged. Actual4096 TGA paint/spec match all251,001 native snapshot pixels; Sync changes240,480 paint pixels inside the copy only; whole-file Undo exact. 47 material tests,6 Pick Color regressions and appearance/master/command/model/transform contracts pass;61 runtime pairs verified.

The integrated real4096 workflow now covers import, edit, persistence, native file export and exact file-level Undo. Reuse accepted Layer/Mask/Spec/Adjust evidence and the real11-layer Burn benchmark: median commit248→122ms, exact composite parity and Undo. Avoid restarting another verification cycle without a new failure, code change or owner request. The smaller guide, target-aware instructions and reachable existing advanced controls preserve Zone popout/Layers/SHOKK functionality. Pick Color unchanged.

Review workspace: Chrome browser2/tab1654209478 on isolated59880. Server PID68940, run_project_audit.py, project-audit-appearance.*.log; owner59876 untouched. Current runtime61 pairs verified. Saved project Tools Zone appearance 20260908 contains the colored copy and11 original Layer records. Saved TGA evidence is in `_tools_simplification_work/zone-appearance-output/`. Projects remain confined to `_release_evidence/isolated_output/tool_project_audit`. No installer build, commit, deployment or production restart is included.

Limits: representative coverage does not promise every conceivable Photoshop feature or exact proprietary color algorithms. The post-export spec-only preview uses a server PNG URL; invalid61-byte data-URL capture attempts are excluded and the unchanged URL/history plus deterministic pixel contracts are recorded honestly. External Linear posting remains unavailable due expired connector authentication; local mirror is current.
