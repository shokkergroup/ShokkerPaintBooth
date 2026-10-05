# ZONE OWNERSHIP — Restrict-to-Layers Semantics (current implementation contract)

**Status:** CURRENT as of 2026-08-22 (binary rendered-footprint semantics; supersedes the
raw-alpha-only crisp-50 implementation after the Codex final-output audit found clipping,
opacity, effects, non-normal-blend, and final-priority contradictions).
**The 50% binary line is the current deterministic rule, not a recorded owner verdict on every
translucent-art case.** What changed is the alpha being measured and the engine guarantee:
ownership now measures the layer's rendered identity footprint, and the engine re-binarizes it at
every boundary. The owner's real 60%/20% grill fixture and stacked-transparency cases still require
an explicit semantic decision; read the post-mortem before changing the threshold.

**Code anchors** (line numbers as of this date; grep the bracketed tags if they drift):

| What | File / line | Tag |
|---|---|---|
| Per-layer ownership mask | `paint-booth-3-canvas.js` `getLayerVisibleContributionMask` | `[ULTRACODE 2026-08-22]` |
| The binary 50% rule itself | `paint-booth-3-canvas.js` (loop in the above) | — |
| Union across a zone's restricted set | `paint-booth-3-canvas.js` ~21482 `getZoneSourceLayersUnionMask` | `[SPB-MULTILAYER 2026-08-21]` |
| Client highlight/selection mask | `paint-booth-3-canvas.js` ~2090 `_buildZoneScopedSelectorMask` | `[SPB-PICK-STALE 2026-08-22]` |
| Engine mask decode (mandatory binary normalize) | `shokker_engine_v2.py` `_normalize_source_layer_mask` | `[SPB-93 / CODEX REVIEW 2026-08-22]` |
| Engine "Remaining" / Everything Else | `shokker_engine_v2.py` ~1810-1845 `_build_remainder_zone_mask` | — |
| Eyedropper outside-restriction warning | `paint-booth-3-canvas.js` ~21523 `_spbWarnPickOutsideRestriction` | `[SPB-PICK-STALE 2026-08-22]` |
| Hidden-source fail-closed + toast | `paint-booth-3-canvas.js` ~2105-2117, ~21552 | `[SPB-LAYER-GAUNTLET A3 2026-08-21]` |

---

## 1. The Ownership Law (current deterministic product behavior)

> A zone restricted to a layer owns the pixels where that layer's **rendered identity footprint**
> wins the binary majority test. Visibility, layer opacity, clipping, and enabled effects are
> included. Art stacks on top; art pixels belong to the art's own zone or fall to "Everything
> Else". The zone list is a priority order inside a shared ownership scope.
> "Everything Else" + "Remaining" takes **all** unclaimed pixels — it fills art interiors,
> with **no strokes and no fuzz**.

### 1a. The 50%-line rule (binary, no fractions — ever)

A pixel belongs to layer L's ownership mask **iff both**:

1. **L's rendered identity alpha ≥ 128** at that pixel (≥50% opaque after current layer opacity,
   clipping, and enabled effects), and
2. **the accumulated rendered identity alpha of art ABOVE L is < 128** there.

Masks are strictly **0 or 255**. Nothing downstream ever sees a fraction. The split sits at the
perceptual edge of anti-aliased art: the half of the fringe where art visually wins goes to the
art; the half where the base visually wins goes to the base. (`paint-booth-3-canvas.js` ~21634.)

This rule intentionally favors a clean binary material partition. It can split one authored
translucent object: a 60%/20% grill alternates between grill ownership and the layer below, while
two stacked 30% layers can leave the pixel to Everything Else. The regression matrix pins those
results so they cannot drift silently; it does **not** claim they are the owner's final preferred
semantics. A future Authored Footprint mode is a product decision, not a bug-fix threshold tweak.

### 1b. Fine print (deterministic implementation contract)

- **Own and above membership both honor layer opacity.** A fully opaque pixel on a layer at 40%
  opacity contributes alpha ~102 and does not cross the majority line; at 50% it does. The old
  asymmetric rule (source ignored opacity while art above honored it) is retired.
- **Clipping participates.** A clipped layer can own only pixels surviving its resolved base-layer
  alpha. A hidden clipping base makes the clipped layer non-compositable.
- **Enabled effects participate.** The same before/pixel/after effect path used by the visible
  compositor builds ownership alpha, so an actual visible stroke/glow is not silently attributed
  to a lower layer.
- **Blend-neutral identity is deliberate.** While alpha identity is measured, every layer is drawn
  as `source-over`; its real blend mode is unchanged in the paint composite. This prevents
  multiply/screen/overlay layers from being skipped and prevents knockout operators from opening
  a hole through which a lower material can leak. Blend color contribution is not used as a
  fractional ownership weight.
- **Helper-layer exemption is NAME-based:** layers matching `/^\s*(mask|wire)\b/i` — the iRacing
  template's "Mask"/"Wire" aids — never occlude anything (~21609-21617). It was group-based for a
  few hours ("Turn Off Before Exporting" group skipped wholesale) — **wrong**: that group also
  holds **Car Mandatory**, which is REAL art (headlight/grill mesh with semi-transparent texture),
  and skipping it let the base zone claim and repaint the grill. Never widen this regex without
  the owner's real file open.
- **Hidden restricted layers don't gate.** A hidden layer is skipped from the union; if EVERY
  restricted layer is hidden the mask fails **closed** (all-zero) in both the render payload and
  the client selector, with a one-shot toast explaining why (A3, ~21493 / ~2105-2117).
- **Multi-layer restriction = max-union** of the individual masks (~21497-21498). Same payload
  contract as a single layer; the engine never knows the difference.
- **Client selection** ANDs the union mask first, then applies per-channel color tolerance against
  `paintImageData` (~2090-2140). Picking a color whose pixels live on a non-restricted layer warns
  at pick time, naming the owning layer (~21523).
- **Transport:** RLE `{width, height, runs:[[value,count],...]}`. The engine decodes to float,
  resizes with `INTER_AREA` when needed, then always thresholds `>=0.5` to exact float32 `0/1`,
  including same-resolution arrays. Truncated/overflow/invalid RLE fails closed to an all-zero
  restriction; it can never degrade into unrestricted whole-canvas paint. Client and engine
  independently enforce the binary law.
- **Cache:** masks cached per `revision:layerId:WxH`, bounded to 24 entries;
  `invalidateLayerVisibleContributionCache()` on any layer change (~21471-21477, ~21641-21646).

### 1c. Priority + Remaining + Everything Else

Zones apply **in list order** (top of list = first claim).

- **Restricted zone + "Remaining"** (`_build_remainder_zone_mask`, restricted branch ~1826-1845):
  remaining means *remaining within that zone's own layer scope* — the union mask minus what
  earlier **restricted** zones already claimed in the overlap. Earlier *unrestricted* zones live in
  the flattened composite and deliberately do not erase a layer-scoped remainder. The final
  effective-mask pass preserves this local result instead of subtracting the global prior mask a
  second time; `test_final_render_keeps_source_local_remainder_after_global_claim` pins that bug.
- **Restricted masks are hard by construction.** Source restriction implies hard ownership even
  when `hard_edge` is absent/false: selector blur, hardening, remainder, final effective mask,
  cache replay, paint, export-layer capture, CPU spec, and GPU spec all receive binary ownership.
- **Unrestricted "Everything Else"** (~1815-1820): `1 − claimed_hard`, Gaussian-feathered, then
  hard-zeroed wherever `claimed_hard > 0.5`. **This `> 0.5` cliff is why fractional claims are
  banned** — see post-mortem, iteration 3. With binary masks, `claimed_hard` is 0 or 1 at every
  pixel, so the remainder is the exact complement: art interiors fill, no orphan slivers, no
  default-green spec strokes.

---

## 2. Plain-language version (paste-able into user docs)

> **What "Restrict to Layers" means**
>
> When you restrict a paint zone to a layer (say, BASE01), the zone paints exactly the pixels
> where that layer is what you actually see on the car. If a logo, number, or decal sits on top
> of BASE01, those covered pixels do **not** belong to the BASE01 zone — they belong to whichever
> zone is restricted to *that* art, or to "Everything Else" if nothing claims them. Your art keeps
> stacking on top of your paint, exactly like it does in Photoshop.
>
> The dividing line at soft (anti-aliased) edges is 50%: where the art on top is more than half
> opaque, the pixel is the art's; where it's less, the pixel still belongs to the layer below.
> Clean edges, no halos, no outlines.
>
> Opacity and clipping affect ownership the same way whether the layer is the restricted source or
> sits above it. A fully opaque pixel on a layer below 50% opacity does not cross the ownership
> line; at 50% it does. Visible layer effects such as strokes and glows participate too.
>
> The template helper layers named "Mask" and "Wire" are ignored entirely — they're guides, not
> paint. Everything else in your stack, including Car Mandatory (headlights/grill), is real art
> and owns its pixels like any other layer.
>
> Zones apply top-to-bottom in your zone list. A zone set to "Everything Else / Remaining" sweeps
> up every pixel no other zone claimed — including the insides of decals and numbers if no zone
> claims them — so nothing on the car is ever left unpainted.
>
> If you restrict a zone to a hidden layer, the zone paints nothing (and tells you why) instead of
> silently painting through the hidden art. If you eyedrop a color that only exists on a layer the
> zone is NOT restricted to, you'll get a warning naming that layer.

---

## 3. Post-mortem: the four iterations of 2026-08-21/22

All four shipped within ~24h against the owner's real dirt-late-model file (stack bottom→top:
BASE01 → White Accent → Logos → Numbers → Pitbox Colors → Contingency Decals → Tape → Car_Decal →
Color Change Logos → "Turn Off Before Exporting TGA" group [Car Mandatory / Mask / Wire]).

### Iteration 1 — FOOTPRINT (`SPB-SPEC-RINGS`, 2026-08-21) — WRONG
- **Semantics:** mask = the restricted layer's own alpha footprint, ignoring everything above.
- **Failure:** BASE01 is a full-canvas paint scheme, so its zone owned the ENTIRE car — including
  every pixel under logos, numbers, and decals — and repainted over them. Art stopped stacking.
  Broke the owner's core mental model for a day.
- **Lesson:** ownership is about what you *see*, not where the layer *has pixels*.

### Iteration 2 — STACK-CLAIM (`SPB-LAYER-STACK-CLAIM`, 2026-08-21) — WRONG
- **Semantics:** subtract art above, but with an all-or-nothing threshold: art above only occluded
  where its composited alpha ≥ 250 (essentially fully opaque).
- **Failure:** every anti-aliased fringe pixel (above-alpha 1..249) stayed with the base zone, so
  the base repainted a 1-3px band hugging every piece of art → the owner's **"stroke/ring around
  all the outlines."** Also the helper skip was **group-based** here, so Car Mandatory (real
  grill/headlight art inside the "Turn Off Before Exporting" group) never occluded → base claimed
  and repainted the grill.
- **Lesson:** a binary threshold at the *extreme* end of the alpha range just moves the artifact;
  and never classify art by what group it sits in.

### Iteration 3 — TAPER (`SPB-VISIBLE-OWNERSHIP`, 2026-08-22 morning) — WRONG
- **Semantics:** fractional weights, `min(own_alpha, 255 − above_alpha)`, quantized, with the
  engine's old binarize (`>0.01 → 1.0`) **lifted** so fractions survived to the claim math.
  Looked mathematically elegant: claim fades out exactly as art fades in.
- **Failure (the subtle one — the engine interaction):** `_build_remainder_zone_mask` zeroes the
  unrestricted remainder wherever `claimed_hard > 0.5` (~1819). A fringe pixel claimed at, say,
  0.6 was (a) painted only 60% by the owning zone and (b) **excluded entirely** from Everything
  Else → a sliver of canvas owned by *nobody* → fell to the default green spec → **outline strokes
  around all art in the SPEC map** whenever the unrestricted remaining-gloss zone ("Everything
  Else", zone 5) was active. Meanwhile fractional claims over semi-transparent art (grill mesh,
  contingency-decal shadows) half-painted those pixels → the **"fuzz"** over the grill and decals
  in live preview.
- **Lesson:** fractional ownership is only sound if EVERY consumer is fractional-aware. The
  remainder pipeline's `>0.5` cliff makes partial claims structurally unsafe — a taper on the
  client is a lie the engine turns into orphaned pixels. Fixing the engine to be fully soft was
  considered and rejected: soft ownership over semi-alpha art *still* reads as half-painting.

### Iteration 4 — CRISP-50 (`[ULTRACODE 2026-08-22]`) — threshold retained, inputs superseded
- **Semantics:** section 1a. Binary at the 50% perceptual line, both tests (`own ≥ 128`,
  `above < 128`). Helper exemption narrowed to name-based `mask|wire`. Engine float pass-through
  retained (harmless — inputs are 0/1).
- **Why it works:** every pixel has exactly one owner or falls to the remainder — the `>0.5`
  remainder cliff and the binary masks agree by construction. No slivers, no green spec strokes,
  no half-painted mesh. The AA fringe splits at the same line a human perceives the edge.

### Iteration 5 — RENDERED-FOOTPRINT + ENGINE INVARIANT (`[SPB-93 / CODEX REVIEW 2026-08-22]`) — CURRENT
- **Audit finding:** iteration 4 measured raw source alpha, ignored source opacity/clipping/effects,
  skipped every non-normal layer above, and trusted the client to remain binary. Its helper-level
  remainder test also missed a later global priority subtraction that erased the correct local
  remainder before compose.
- **Semantics:** retain binary `own >=128 && above <128`, but build both alphas through the shared
  layer pixel/effect compositor with blend-neutral identity. Normalize every engine input to 0/1,
  make source restriction imply hard ownership across every render path, and preserve the
  source-local remainder through the final effective-mask pass.
- **Proof:** the new full `build_multi_zone(..., export_layers=True)` regression failed against the
  old final path (zone 2 never reached compose) and passes with the exact restricted mask. A second
  negative control proved same-size fractional masks previously bypassed engine binarization.

---

## 4. Notes for the next agent

1. **Do not reintroduce fractions.** `_normalize_source_layer_mask`, remainder output, and the final
   effective mask intentionally threshold independently. A future soft-ownership mode requires a
   separate product contract and a complete fractional rewrite, not removal of one guard.
2. **Blend-neutral identity is a policy, not Photoshop blend attribution.** It answers "which
   authored layer controls material here?" without attempting to apportion multiply/screen color
   deltas. If the owner wants perceptual blend contribution, build it as an explicit alternate
   mode with final-output fixtures; do not silently change this default.
3. **PSD group boundary:** SPB now preserves nested group chains, visibility, opacity, supported
   isolated blend modes, pass-through/isolation, and immediate-group clipping bases. Unsupported
   cases (including reduced-opacity pass-through groups, clipped group nodes, knockout/dissolve,
   and inconsistent group metadata) fail visibly to the authoritative source composite instead of
   being guessed or silently flattened. Ownership can only run when the imported topology is safe.
4. **Test with the owner's real file**, not synthetic stacks. Every failure above passed simple
   tests and died on: full-canvas BASE01, semi-transparent grill mesh (Car Mandatory), AA'd
   contingency decals, and the Mask/Wire helpers. `output/job_*/zones_payload.json` +
   `/spb-render-replay` reproduces engine-side; the spec-map strokes only show with the
   unrestricted "Everything Else" gloss zone active.
5. **Engine restart required** after `_normalize_source_layer_mask` changes; client mask changes
   need a cache-token bump (`?v=`) or they silently don't load. The integration owner must bump the
   canvas token when syncing this change into the packaged runtime.
