"""Pairwise statistical distinctness regression — Ornamental Specials (Item 2).

## Why this exists (2026-04-25 overnight Iter 8)

User Item 2 brief: "Deeply inspect every Ornamental finish that previously
looked identical: hex_mandala, lace_filigree, honeycomb_organic,
baroque_scrollwork, art_nouveau_vine, penrose_quasi, topographic_dense,
interference_rings. Find why they still fall back or share the same look.
Fix wiring first, then rebuild visuals. Each one should have a distinct
algorithm and obvious identity at 2048x2048. Add a visual/statistical
regression that proves they are not near-identical."

Codex's 2026-04-24 Ornamental Source Pass rebuilt all 8 with bespoke
generators (`_ornate_wave_ink`, `_ornate_micro_grit`, per-finish style
profiles in `_ORNAMENTAL_PAINT_STYLES`). Iter 8 visual audit at 256
confirmed they render as visually distinct (green spiral mandala vs
orange honeycomb vs blue interference rings vs purple penrose etc.)
with no near-duplicates flagged.

This file pins the distinctness STATISTICALLY — the user's exact
phrasing was "visual/statistical regression that proves they are not
near-identical." If a future regression silently rewires any pair to
the same fallback or shared generator, this test fires before the
painter sees it.

## What this proves

For all C(8,2) = 28 pairs of Ornamentals at probe shape 256×256, seed
42, mid-grey input:

  1. **Paint output divergence**: pairwise mean-absolute pixel difference
     > 0.04 on normalized RGB. Sub-0.04 means the two finishes render
     within 4% of identical pixels — "looks identical" by any practical
     measure.

  2. **Spec output divergence**: pairwise mean-absolute byte difference
     > 6.0 on uint8 spec channels. Bases that produce indistinguishable
     spec maps would shade identically under iRacing's PBR even if their
     paint differs.

  3. **No paint hash collision**: byte-identical paint output across any
     pair is the silent-no-op smoking gun.

  4. **No spec hash collision**: same for spec.

  5. **Per-finish identity floor**: each Ornamental's paint must differ
     from a flat mid-grey reference by more than the inter-pair floor —
     proves none silently flat-fills.

If this fires it means a future edit:
  * Wired multiple Ornamentals to the same fallback generator
  * Removed the per-finish style profiles in `_ORNAMENTAL_PAINT_STYLES`
  * Reverted the bespoke `texture_*` rebuilds
  * Or otherwise collapsed the visual distinctness Codex's source pass
    delivered.

The painter's "looked identical" complaint comes back if any of those
happen, which is why the assertions are tight numeric bounds, not just
"non-zero variance".
"""

from __future__ import annotations

import hashlib
import itertools

import numpy as np
import pytest


ORNAMENTAL_IDS = [
    "hex_mandala",
    "lace_filigree",
    "honeycomb_organic",
    "baroque_scrollwork",
    "art_nouveau_vine",
    "penrose_quasi",
    "topographic_dense",
    "interference_rings",
]

# Distinctness floors. These are deliberately well below the actually-
# measured Iter 8 pairwise distances so a real regression triggers, but
# slightly-different probe values won't false-positive.
PAINT_PAIRWISE_FLOOR = 0.04   # mean abs delta on [0,1] RGB
SPEC_PAIRWISE_FLOOR = 6.0     # mean abs delta on uint8 spec
PAINT_VS_GREY_FLOOR = 0.05    # each finish must diverge from mid-grey


@pytest.fixture(scope="module")
def engine():
    import shokker_engine_v2 as eng
    eng._ensure_expansions_loaded()
    return eng


@pytest.fixture(scope="module")
def probe_shape():
    return (256, 256)


@pytest.fixture(scope="module")
def rendered(engine, probe_shape):
    """Render each Ornamental once into a {paint, spec, hashes} bundle.
    Module-scoped so the C(8,2)=28 pair-tests don't re-render."""
    H, W = probe_shape
    mask = np.ones((H, W), dtype=np.float32)
    mid_grey = np.full((H, W, 3), 0.45, dtype=np.float32)
    bb = np.zeros((H, W), dtype=np.float32)
    seed = 42

    out = {}
    for fid in ORNAMENTAL_IDS:
        assert fid in engine.MONOLITHIC_REGISTRY, (
            f"{fid} missing from MONOLITHIC_REGISTRY — Ornamental source "
            f"pass regression"
        )
        spec_fn, paint_fn = engine.MONOLITHIC_REGISTRY[fid]
        # Monolithic paint signature: paint_fn(paint, shape, mask, seed, pm, bb)
        paint_out = paint_fn(mid_grey.copy(), probe_shape, mask, seed, 1.0, bb)
        paint_arr = np.asarray(paint_out, dtype=np.float32)
        # Spec signature: spec_fn(shape, mask, seed, sm)
        spec_out = spec_fn(probe_shape, mask, seed, 1.0)
        spec_arr = np.asarray(spec_out, dtype=np.float32)
        out[fid] = {
            "paint": paint_arr,
            "spec": spec_arr,
            "paint_hash": hashlib.sha256(paint_arr.tobytes()).hexdigest()[:16],
            "spec_hash": hashlib.sha256(spec_arr.tobytes()).hexdigest()[:16],
        }
    out["_mid_grey"] = mid_grey
    return out


# ---------------------------------------------------------------------------
# Pair-wise distinctness — the user's exact "not near-identical" requirement
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("pair", list(itertools.combinations(ORNAMENTAL_IDS, 2)))
def test_pairwise_paint_diverges(rendered, pair):
    """Every pair of Ornamentals must differ by >4% mean abs pixel delta
    on normalized RGB. Two finishes within 4% are visually identical
    to a painter — that's the user-reported regression class."""
    a_id, b_id = pair
    a = rendered[a_id]["paint"]
    b = rendered[b_id]["paint"]
    delta = float(np.abs(a - b).mean())
    assert delta > PAINT_PAIRWISE_FLOOR, (
        f"Ornamental pair {a_id} <-> {b_id} renders near-identically "
        f"(mean abs paint delta = {delta:.4f} <= {PAINT_PAIRWISE_FLOOR}). "
        f"Painter would call these the same finish. The Ornamental source "
        f"pass distinctness has regressed — check `_ORNAMENTAL_PAINT_STYLES` "
        f"and the per-finish `texture_*` generators in shokker_engine_v2.py."
    )


@pytest.mark.parametrize("pair", list(itertools.combinations(ORNAMENTAL_IDS, 2)))
def test_pairwise_spec_diverges(rendered, pair):
    """Every pair must differ by >6 mean abs byte delta on uint8 spec
    output. Identical spec maps mean iRacing's PBR shading reads the
    finishes the same way even if paint diverges visually."""
    a_id, b_id = pair
    a = rendered[a_id]["spec"]
    b = rendered[b_id]["spec"]
    delta = float(np.abs(a - b).mean())
    assert delta > SPEC_PAIRWISE_FLOOR, (
        f"Ornamental pair {a_id} <-> {b_id} produces near-identical spec "
        f"output (mean abs spec delta = {delta:.4f} <= {SPEC_PAIRWISE_FLOOR}). "
        f"PBR will shade these identically — same surface character on "
        f"the car despite paint differences. Check spec_fn wiring in "
        f"`_ORNAMENTAL_PAINT_STYLES` / `MONOLITHIC_REGISTRY` entries."
    )


def test_no_paint_hash_collisions_across_ornamentals(rendered):
    """Byte-identical paint output across any pair is the loudest possible
    silent-no-op signal — they're literally the same bytes coming out of
    the renderer."""
    by_hash = {}
    for fid in ORNAMENTAL_IDS:
        by_hash.setdefault(rendered[fid]["paint_hash"], []).append(fid)
    collisions = {h: ids for h, ids in by_hash.items() if len(ids) > 1}
    assert collisions == {}, (
        f"Ornamental finishes producing byte-identical paint output: "
        f"{collisions}. Either wired to a shared fallback generator or "
        f"the bespoke source generators were collapsed."
    )


def test_no_spec_hash_collisions_across_ornamentals(rendered):
    """Byte-identical spec output across any pair = same shading."""
    by_hash = {}
    for fid in ORNAMENTAL_IDS:
        by_hash.setdefault(rendered[fid]["spec_hash"], []).append(fid)
    collisions = {h: ids for h, ids in by_hash.items() if len(ids) > 1}
    assert collisions == {}, (
        f"Ornamental finishes producing byte-identical spec output: "
        f"{collisions}. Catches shared spec_fn wiring across multiple "
        f"named Ornamentals."
    )


@pytest.mark.parametrize("fid", ORNAMENTAL_IDS)
def test_ornamental_diverges_from_flat_grey(rendered, fid):
    """Each Ornamental must visibly modify a mid-grey input. A finish
    that produces output ~= mid_grey is silently doing nothing."""
    paint = rendered[fid]["paint"]
    delta = float(np.abs(paint - rendered["_mid_grey"]).mean())
    assert delta > PAINT_VS_GREY_FLOOR, (
        f"{fid} paint output stays within {PAINT_VS_GREY_FLOOR} of mid-grey "
        f"(measured {delta:.4f}). Finish silently does nothing."
    )


def test_ornamental_pairwise_distance_floor_summary(rendered):
    """Sentinel — the MIN pairwise paint delta across all C(8,2) pairs
    must stay above the floor. If a single pair drops below, the
    parametrized test above also fires; this test additionally surfaces
    the actual measured min so worklog/CHANGELOG can record it
    historically."""
    deltas = []
    for a_id, b_id in itertools.combinations(ORNAMENTAL_IDS, 2):
        d = float(np.abs(rendered[a_id]["paint"] - rendered[b_id]["paint"]).mean())
        deltas.append((a_id, b_id, d))
    deltas.sort(key=lambda t: t[2])
    min_pair = deltas[0]
    assert min_pair[2] > PAINT_PAIRWISE_FLOOR, (
        f"Closest Ornamental pair: {min_pair[0]} <-> {min_pair[1]} "
        f"(delta {min_pair[2]:.4f} <= floor {PAINT_PAIRWISE_FLOOR}). "
        f"Tightest pair has lost distinctness."
    )
