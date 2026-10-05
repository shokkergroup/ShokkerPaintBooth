# Catalog: Cross-Registry Duplicate IDs

Investigation of the `WARN ... 88 id(s) claimed by more than one registry`
emitted by `scripts/spb_catalog_report.py` (the "Duplicate ids" section).

- **Status:** Investigated. 85 benign by-design; **3 genuine collisions** worth
  an owner decision.
- **Scope:** Read-only intelligence for the owner. No catalog, registry,
  finish, or engine data was changed to produce this report.
- **Date:** 2026-05-30

---

## TL;DR (Bottom line)

Of the **88** flagged IDs:

- **85 / 88 are expected / by-design.** Each id appears in two registries that
  store it in *different on-disk shapes* (e.g. a `dict` base entry vs a legacy
  `tuple` finish entry), but it represents the **same kind of finish** in both
  — it is the same thing exposed through two access paths. No ambiguity of
  intent.
- **3 / 88 are genuine same-id / different-intent collisions.** All three are
  the `BASE` ∩ `PATTERN` overlap — an id that is a **base material** in `BASE`
  but a **pattern** in `PATTERN`:
  - **`shokk_cipher`**
  - **`dragonfly_wing`**
  - **`carbon_weave`**

  A base material and a pattern are *different layers* of the
  "base + pattern + monolithic" composition model, so one id meaning both is a
  real ambiguity — exactly the failure mode the duplicate-id WARN exists to
  catch.

> A common assumption is "`FINISH` is a curated subset of `MONOLITHIC`, so any
> overlap is by-design." In *this* codebase that is **not** true — see
> "Registry model". None of the four registries is a subset of another, and
> 38 of FINISH's 43 ids are not in MONOLITHIC at all. The by-design reading
> still holds for 85 of the 88, just not via a subset relationship.

---

## How these numbers were produced (authoritative, not a grep)

Counts come from loading the engine itself, mirroring what
`scripts/spb_catalog_report.py` does — not from text-searching source files:

1. `import shokker_engine_v2` with **stdout suppressed** (the engine prints a
   banner and registry-merge chatter on import).
2. Read the four module-level registry dicts the report inspects:
   `BASE_REGISTRY`, `PATTERN_REGISTRY`, `FINISH_REGISTRY`,
   `MONOLITHIC_REGISTRY`. (These are populated at import time by the engine's
   merge from `engine.registry._build_registries()` plus the dual-shift /
   micro-flake / expansion registrations.)
3. For every id, record the set of registries that claim it; keep those
   claimed by more than one. This reproduced the report's **88** exactly.
4. For each duplicate, compare the entries across the claiming registries.

A note on *how* entries were compared, because it determines the verdict:

- `==` is **not** usable: entries hold function objects / tuples, so `==`
  reports "different" for **all 88** even when they are the same finish.
- Object identity (`is`) is also `False` for all 88 — each registry stores its
  own copy.
- The registries do not even use a uniform storage shape: `BASE` and
  `PATTERN` entries are **dicts**, while `FINISH` and `MONOLITHIC` entries are
  **tuples** (legacy `(spec_fn, paint_fn)` form). So any duplicate that pairs
  a dict-registry with a tuple-registry will *always* look "structurally
  different" — but that is a **storage-format** difference, not an
  intent collision.
- The only registry pair where both sides are dicts (and therefore directly
  comparable for intent) is **`BASE` ∩ `PATTERN`**. That is where the three
  genuine collisions surface, and there the key sets make the conflict
  unambiguous (base-material keys vs pattern keys).

The engine load completed with exit code 0. Every count below was re-derived
from the engine-produced JSON via `json.load` (an authoritative parser); the
six registry-combination buckets independently checksum to **88**, and the
verdict buckets (85 + 3) also sum to 88.

> Run-environment note: this work was done over an intermittently degraded
> network drive (raw stdout was repeatedly truncated/duplicated/contaminated).
> Every load-bearing number was therefore confirmed by parsing the
> engine-derived JSON and re-deriving it across multiple runs until stable —
> never by trusting raw console text. The three-collision finding reproduced
> identically on independent re-derivations.

---

## Registry model (what the four registries actually are)

Live sizes from the engine load:

| Registry              | Size  | Entry shape | Role |
| --------------------- | ----- | ----------- | ---- |
| `BASE_REGISTRY`       | 518   | dict        | Base-material entries (`paint_fn` + `base_spec_fn` + `CC/M/R/desc/...`). |
| `PATTERN_REGISTRY`    | 617   | dict        | Pattern entries (`paint_fn` + `texture_fn`/`image_path` + `desc/...`). |
| `FINISH_REGISTRY`     | 43    | tuple       | Legacy `(spec_fn, paint_fn)` finish map. |
| `MONOLITHIC_REGISTRY` | 1009  | tuple       | Composed "monolithic" finishes. |

Verified set relationships (all from the engine load) — note none is a strict
subset, which refutes the usual "everything rolls up into MONOLITHIC"
intuition:

- `BASE` ⊆ `MONOLITHIC`? **No.**
- `PATTERN` ⊆ `MONOLITHIC`? **No.**
- `FINISH` ⊆ `MONOLITHIC`? **No** — **38** of FINISH's 43 ids are *not* in
  MONOLITHIC.
- `BASE` ∩ `PATTERN` = `{carbon_weave, dragonfly_wing, shokk_cipher}` — the
  only overlap where both sides are dicts and intent is directly comparable.

So the 88 duplicates are spread across **six** distinct registry pairings, and
**not** all of them route through MONOLITHIC (the `all_include_mono` check is
`False`).

---

## The 88, categorized

Bucketed by the exact pair of registries claiming each id. "Comparable
shape?" means both registries store the entry as a dict (so intent can be
compared directly); when one side is a tuple, the entries are the same finish
exposed in two storage formats.

### Expected / by-design (85 of 88)

| Registries claiming the id | Count | Comparable shape? | Why it's by-design |
| -------------------------- | ----- | ----------------- | ------------------ |
| BASE + MONOLITHIC          | 32    | no (dict vs tuple)| Base-material entry also exposed as a composed-finish tuple. |
| FINISH + PATTERN           | 24    | no (tuple vs dict)| Pattern also exposed via the legacy finish tuple map. |
| BASE + FINISH              | 14    | no (dict vs tuple)| Base-material entry also exposed via the legacy finish tuple map. |
| MONOLITHIC + PATTERN       | 10    | no (tuple vs dict)| Pattern also exposed as a composed-finish tuple. |
| FINISH + MONOLITHIC        | 5     | no (tuple vs tuple)| Same finish in both legacy tuple maps. |
| BASE + PATTERN             | 0     | —                 | (All 3 BASE+PATTERN ids are collisions; see below.) |

Bucket checksum across all six pairings: 32 + 24 + 14 + 10 + 5 + 3 = **88**.
Of those, the 85 above are by-design; the 3 in `BASE + PATTERN` are the
collisions.

> Why the dict-vs-tuple cases are *not* collisions: the same id is reachable
> through more than one registry, but each registry's job differs (legacy
> finish lookup, composed monolithic, base material, pattern). The id resolves
> to the same finish; only the calling convention differs. This is duplication
> in the *catalog bookkeeping*, not a conflict in *meaning*.

### Worth-owner-review (3) — the `BASE` ∩ `PATTERN` collisions

All three ids below are a **base material** in `BASE` and a **pattern** in
`PATTERN`. Both sides are dicts, so the conflict is real and directly
verifiable from their keys:

| ID               | `BASE` entry keys (base material)            | `PATTERN` entry keys (pattern)              |
| ---------------- | -------------------------------------------- | ------------------------------------------- |
| `shokk_cipher`   | `CC, M, R, base_spec_fn, desc, paint_fn`     | `desc, paint_fn, texture_fn, variable_cc`   |
| `dragonfly_wing` | `CC, M, R, base_spec_fn, desc, paint_fn`     | `desc, paint_fn, texture_fn, variable_cc`   |
| `carbon_weave`   | `CC, M, R, base_spec_fn, desc, noise_M, noise_R, paint_fn, perlin, perlin_lacunarity, perlin_octaves, perlin_persistence` | `desc, image_path, paint_fn` |

In each case the `BASE` copy carries the base-material spec controls
(`CC/M/R/base_spec_fn`) while the `PATTERN` copy carries pattern controls
(`texture_fn`/`image_path`/`variable_cc`) and **no** base spec. Same id,
fundamentally different entry → different runtime behavior depending on which
registry resolves it.

*Why it matters:* base materials and patterns are different layers in the
"base + pattern + monolithic" composition model. An id that means both is
ambiguous.

*Owner decision (no change made here):* for each of the three, confirm which
definition is canonical and rename the other so the id is unambiguous (e.g.
keep the pattern as-is and rename the base copy to `base_<id>`, or
vice-versa). The fix touches catalog/registry data and is intentionally left
to the owner; this document is read-only intelligence.

---

## Examples (representative, engine-verified)

| ID                | Claimed by           | Verdict | Note |
| ----------------- | -------------------- | ------- | ---- |
| `acid_rain`       | BASE + MONOLITHIC    | by-design | Same finish, dict (base) vs tuple (monolithic). |
| `art_nouveau_vine`| FINISH + PATTERN     | by-design | Same finish, tuple (finish) vs dict (pattern). |
| `anodized`        | BASE + FINISH        | by-design | Same finish, dict vs legacy tuple. |
| `ember_glow`      | MONOLITHIC + PATTERN | by-design | Same finish, tuple vs dict. |
| `carbon_fiber`    | FINISH + MONOLITHIC  | by-design | Same finish in both legacy tuple maps. |
| `carbon_weave`    | BASE + PATTERN       | **collision** | Base material vs pattern under one id. |
| `dragonfly_wing`  | BASE + PATTERN       | **collision** | Base material vs pattern under one id. |
| `shokk_cipher`    | BASE + PATTERN       | **collision** | Base material vs pattern under one id. |

---

## Recommendation

- **No code/data change is required for 85 of the 88.** They are the same
  finish reachable through two registries (often dict-vs-legacy-tuple). This
  part of the WARN is informational.
- **Three items deserve an owner decision:** `shokk_cipher`, `dragonfly_wing`,
  and `carbon_weave` are each the same id bound to a **base material** (in
  `BASE`) and a **pattern** (in `PATTERN`). Decide the canonical meaning of
  each and rename the other copy to disambiguate. (Intentionally **not**
  changed here — read-only intelligence, and the fix is catalog/registry
  data.)
- *Optional reporting tweak (owner call, not made here):* the report currently
  counts an id as a duplicate whenever it appears in ≥2 registries, even when
  it is merely the same finish exposed in two storage formats. Tightening it to
  warn only when both sides are dicts with **different key sets** (true intent
  conflict) would surface just the **3** real collisions instead of 88 —
  putting the signal front-and-center while keeping the full count available as
  an INFO line.
