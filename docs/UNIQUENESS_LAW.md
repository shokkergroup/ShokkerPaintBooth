# THE UNIQUENESS LAW — a hard line in the sand for every finish

**This is not a suggestion buried in a doc. It is a gate with code behind it.**
Any human or AI that builds, rebuilds, or "freshens" finishes in Shokker Paint
Booth MUST clear this gate before the work is considered done. No exceptions,
no "good enough," no shipping recolors.

> Owner mandate, 2026-06-15 (after a category shipped with recolored clones and
> flat two-color spec maps): *"If the finishes are within X% similarity of another
> finish they get hard redone. PERIOD."* This file is the answer to that.

---

## The two rules

### 1. No finish may be ≥ 80% structurally similar to ANY other finish — in the WHOLE catalog
Similarity is measured **structurally and color-independently** (luma perceptual
hash + a multi-scale structural descriptor). That means **a recolor of an existing
design is a clone even if the palette is completely different.** The check is
**cross-category**: a new "Sock Hop" finish that's 84% similar to a "Marble" finish
fails. Look for genuinely unique lanes — unique *math*, unique *shapes*, unique
*motifs* — not the same pattern with the hue dial moved.

- **≥ 80% similar → FAIL → hard redo.** Period.
- The gate reports the nearest neighbor and the %, so you know exactly what you
  collided with and can go somewhere new.

### 2. The spec map must mirror the paint — unless it's *deliberately* doing something else
The spec is there to **complement the finish**, and to ignite the *same features*
the eye sees. If the paint is 2,300 tiny silver shards, the spec had better light
up those same 2,300 shards — same geometry, same seed, traced. A spec that carries
alien geometry the paint doesn't have, or a flat/dead spec, fails.

- Colors in the spec **can** differ from the paint (some looks need it), and the
  combined M/R/CC map **should** be multi-hue and alive — never two colors with
  dark spots. But the *structure* must trace the paint.
- The only way to skip the trace requirement is to **list the id in
  `scripts/uniqueness_exemptions.json`** with a real reason (e.g. a finish whose
  whole point is a spec that contradicts the paint). If it's not on that list,
  it's held to the rule.

---

## How to run the gate (do this BEFORE you call a finish done)

```bash
# 1. make sure the catalog index reflects current code (incremental, cached)
python scripts/spb_catalog_fingerprint.py

# 2. gate your new / rebuilt finishes
python scripts/spb_uniqueness_gate.py --ids my_new_finish,another_one
python scripts/spb_uniqueness_gate.py --module groovy_vibes_2026   # whole module

# anything that FAILS gets redone until it passes. Exit code is non-zero on fail.
```

To plan rebuilds of the *existing* catalog (we'll chip away at it):

```bash
python scripts/spb_uniqueness_gate.py --report          # all existing dup pairs ≥ 80%
python scripts/spb_uniqueness_gate.py --report --threshold 0.7
```

The same data powers the **Similarity** tab in the SPB Workbench
(`/SPB_WORKBENCH.html`): pick a finish, drag the slider, and see everything in the
whole catalog within that similarity — instantly. Use it to find empty lanes.

---

## What "unique" actually means here (so we stop arguing with the number)
- **Different algorithm**, not the same function with new constants. If two finishes
  share a `_field`/factory and differ only by palette args, they are clones.
- **Different shapes/motifs.** Swirl ≠ the only groovy thing; shards, cells, weave,
  rays, blobs, crackle, lattice, bands, dendrites, voronoi, flow — pick a lane no
  one else is in.
- **Alive, traced specs.** Multi-hue combined map, decorrelated channels
  (|corr| < 0.85), structure that follows the paint.

If you can't get under 80% against the whole catalog, the answer is not a smaller
tweak — it's a different idea. That's the whole point.

— Enforced by `scripts/spb_catalog_fingerprint.py` + `scripts/spb_uniqueness_gate.py`.
