# HOUDINI / X-LAB — LOOK-FREEZE + PERFORMANCE MANDATE (owner, 2026-08-29)

**BINDING for every agent building or touching FRACTURED HOUDINI and X-LAB finishes — Codex
first and foremost. This is an owner ruling, not a suggestion.**

Owner's exact words, 2026-08-29:

> "Is there a way to keep the quality not sacrificing the 'look' of some of these new finishes?
> Because some of them are visually stunning." … "I'm good with the way they look now unless
> they are changed." … "I want CODEX to be able to change the looks just optimize the times on
> them. Like the same look every time BUT if it's trying to IMPROVE the looks through several
> iterations it's able to do that at its own free will."

Translation into law — **the contract binds the ACTIVITY, not the artist. Two modes:**

- **OPTIMIZE mode** (goal = speed): the look is untouchable. Same pixels, faster. Speed and
  look are not in tension — this codebase has already proven it (bit-exact perf lane
  2026-08-06: 8.42s → 5.37s with byte-identical output).
- **IMPROVE mode** (goal = a better look): Codex iterates **at its own free will** — as many
  redesign passes as it wants, no pre-approval needed. The only requirements: the intent is
  DECLARED (lane doc / log line saying this card's look is changing on purpose), the new look
  passes the same gates every finish passes (§4, including the render budget), and the
  reference is RE-BAKED afterward so the improved look becomes the new baseline.

**What is forbidden is the gap between the modes: silent look drift during a perf pass.** A
card's pixels never change as an *accident* of optimization — they change only when Codex
meant them to.

---

## 1. THE LOOK-STABILITY CONTRACT (binds OPTIMIZE mode; IMPROVE mode re-bakes it)

`_finish_look_refs/2026-08-29/` holds the owner-approved reference state for **every registered
`houdini_*` and `xlab_*` monolithic** (rendered 2048², seed 51, scale 1.0, the standard
`(paint, shape, mask, seed, sm, bb)` / spec call):

- `manifest.json` — per-card **SHA-256 of the canonical float32 output bytes** (paint + spec),
  per-card render timings (the before-state), and stats.
- `<id>_paint.png` / `<id>_spec.png` — 1024px eyeball copies.

**The rule in OPTIMIZE mode:** after ANY perf work, re-render at the same seed/scale and
compare against the manifest.

- **Bit-exact match (same SHA) = done.** This is the default expectation for vectorization,
  separable filters, dtype hygiene, pass-fusion, and caching work.
- **If an optimization is legitimately non-bit-exact** (e.g. a resampling change), it is
  **owner-approve-only**: produce a before/after image pair from the refs, put it in front of
  the owner, and do not ship until the owner says the look is unchanged. Metrics
  (SSIM ≥ 0.995, maxdiff, std delta) support the case — they never replace the owner's eye.
- A card whose baked ref carries `"deterministic": false` cannot use the SHA contract —
  fix the nondeterminism first (a finish that renders differently per run is itself a bug).

**The rule in IMPROVE mode:** iterate freely. When the improved look is the one you're
keeping: declare it, pass §4, then **re-bake that card's reference** so the contract tracks
the new baseline: `python _finish_look_refs/bake_refs.py <id> [<id>...]` (passing ids forces
a re-bake; with no args the script is incremental and skips done ids). A stale reference SHA
after a declared improvement is expected — a changed SHA with NO declared improvement is the
violation.

New cards: bake their ref the moment the look is settled, then the same two-mode contract
applies.

---

## 2. THE TWO DEFECTS TO FIX NOW (wiki T66)

1. **Base Scale < 1.00 loses the colors** (owner-confirmed on Sonic Chrome). The finish math
   is NOT the problem — `MONOLITHIC_REGISTRY["xlab_sonic_chrome"]` paint_fn called directly
   returns full color at every scale and resolution (evidence: `_deepaudit/houdini_repro/`,
   method in `_deepaudit/houdini_scale_repro.py`). The loss is in the render path taken when
   `base_scale != 1.0`. Reproduce with a REAL client capture (render in-app at 1.00 vs 0.85,
   diff `output/job_*/RENDER_paint.png`) — synthetic hand-built payloads do not exercise the
   monolithic paint path correctly (documented in T66).
2. **Render budget breach.** Measured 2026-08-29 at 2048²: `houdini_chroma_pyre` **6.8s**
   (spec_fn alone 4.5s), `houdini_aurora_wolf` **6.4s** vs the CLAUDE.md hard budget of
   **2–3s**. At preview size these cards cost 1.0–1.5s vs ~100ms for classic finishes — with a
   HOUDINI zone active every slider tick queues seconds of render and the whole app feels
   choked (owner: "no longer snappy"). The baked manifest records every card's timing:
   anything with `"over_budget": true` is on the fix list.

---

## 3. APPROVED FIX DIRECTIONS (in order of preference)

1. **Bit-exact optimization** — profile the spec_fn hotspots (they carry ~2/3 of the cost),
   vectorize, make large blurs separable, fuse redundant full-canvas passes, reuse noise
   fields across octaves, keep float32 end-to-end. Verify with the SHA contract. Precedent:
   the 2026-08-06 perf lane and `project_render_perf_2026-08` memory (separable +
   zero-frac decimate rewrites were the only bit-exact ones — read it before touching
   resampling).
2. **Bake-to-asset for finished cards** — a parameterless monolithic is deterministic, so a
   shipped card may be rendered once and stored, with the engine loading + transforming the
   baked art instead of re-synthesizing (the Viva Mexico playbook). Pixel-identical by
   construction, ~100–300ms load path, and it collapses the scale-1.0 vs scale<1 code split —
   likely fixing defect #1 structurally. Wire baked assets through the two-copy rule +
   `scripts/runtime-sync-manifest.json` like every other asset.
3. **Preview resolution laddering** (app-side, shared code — coordinate before touching):
   quarter-res renders while a slider drags, full quality on release. This protects UI feel
   from ANY expensive finish, but it is a complement, not a substitute — the 3s full-render
   budget still stands.

---

## 4. GATES — NOT OPTIONAL, RUN BEFORE ANY CARD SHIPS

- The **spb-finish-gate** battery (uniqueness < 0.80, render ≤ 3s @2048, coverage, fineness)
  over the whole category — the render-time gate would have caught both T66 defects before the
  owner did.
- The look contract from §1 (SHA match or owner approval).
- A scale sweep: render at base_scale 1.0 / 0.85 / 0.5 and verify the color content survives
  (paint std / colorfulness must not collapse) — this is the regression test defect #1 earns.
- Evidence lands in the lane's own state doc (per-card before/after ms + SHA verdict), ONE
  wiki daily-log line per day — token discipline as usual.

---

*Filed by Claude 2026-08-29 after the owner's report + diagnosis session. Cross-references:
wiki trouble spot **T66**, `_deepaudit/houdini_repro/`, `_finish_look_refs/2026-08-29/`,
CHANGELOG 2026-08-29 entries.*
