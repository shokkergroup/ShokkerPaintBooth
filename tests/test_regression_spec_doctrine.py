"""Doctrine compliance regression tests for spec_driven finishes.

Built tick 40 (2026-05-15) from the audit scripts established in ticks 31, 32,
37: ``audit_spec_driven_paint_neutrality``, ``audit_spec_driven_spec_richness``,
``audit_registry_placeholders``. Those scripts existed but relied on humans
remembering to re-run them. These tests promote the checks to CI enforcement.

Three guard rails:

1. Spec_driven monolithic finishes must keep paint near-neutral
   (SPB-78 / paint-neutrality doctrine).
2. The known SPB-87 baseline of placeholder-shim orphans must NOT grow —
   any new orphan beyond the 12 stone/textile IDs is a regression.
3. Ghost Geometry paint_fn must stay quiet (the specific SPB-78 patch
   shouldn't be reverted by future renderer work).

Doctrine references:

* ``engine/paint_v2/surface_intent.py`` — doctrine source of truth
* ``shokker_engine_v2.py`` lines 12698-12715 — painter contract that
  Classic Foundation must be flat
* ``scripts/audit_spec_driven_paint_neutrality.py``
* ``scripts/audit_spec_driven_spec_richness.py``
* ``scripts/audit_registry_placeholders.py``
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest

import shokker_engine_v2 as eng
from engine.paint_v2.surface_intent import is_spec_driven, is_pattern_design


ROOT = Path(__file__).resolve().parent.parent
SCORECARD = ROOT / "paint-booth-0-catalog-scorecard.js"

# Doctrine thresholds — same values used by the audit scripts.
PAINT_NEUTRALITY_THRESHOLD = 0.05  # std on neutral-gray paint input
PATTERN_DESIGN_PAINT_RICHNESS_THRESHOLD = 0.04  # std on neutral-gray; below = no pattern structure
PLACEHOLDER_PATTERNS = ("_spb_missing_base_paint", "_spb_missing_base_spec", "_spb_missing_")

# SPB-87 known orphan baseline. Resolved 2026-05-15 tick 44 via Option A
# (reorder boot — see _spb_reapply_stone_textile_overrides in
# shokker_engine_v2.py). All 12 stone/textile finishes now use their
# dedicated renderers from engine/paint_v2/stone_textile.py. Baseline is
# now empty — any placeholder-shim orphan at all is a regression.
SPB87_KNOWN_BASE_ORPHANS: set[str] = set()


def _parse_scorecard_categories():
    txt = SCORECARD.read_text(encoding="utf-8", errors="replace")
    out = {}
    for m in re.finditer(
        r'"([a-z_]+:[a-z0-9_]+)":\s*\{[^{}]*?"category":\s*"([^"]+)"',
        txt,
        flags=re.S,
    ):
        out[m.group(1)] = m.group(2)
    return out


def _is_placeholder(fn):
    if not callable(fn):
        return False
    name = getattr(fn, "__name__", "") or ""
    return any(pat in name for pat in PLACEHOLDER_PATTERNS)


def test_spec_driven_monolithic_paint_stays_neutral():
    """SPB-78 doctrine: spec_driven monolithic paint_fns must stay near-neutral.

    Probes every spec_driven monolithic finish with a neutral 0.5 paint
    source. Any std > 0.05 means the paint is doing pattern work — a
    Ghost-style violation of the spec_driven doctrine.
    """
    categories = _parse_scorecard_categories()
    mono = eng.MONOLITHIC_REGISTRY

    neutral = np.full((128, 128, 3), 0.5, dtype=np.float32)
    mask = np.ones((128, 128), dtype=np.float32)

    suspects = []
    for fid_with_prefix, category in categories.items():
        if not is_spec_driven(category):
            continue
        surface, _, stem = fid_with_prefix.partition(":")
        if surface != "monolithic":
            continue
        entry = mono.get(stem)
        if not entry or not isinstance(entry, tuple) or len(entry) < 2:
            continue
        paint_fn = entry[1]
        if not callable(paint_fn):
            continue

        seed = hash(stem) & 0x7FFFFFFF
        try:
            out = paint_fn(neutral.copy(), (128, 128), mask, seed, 1.0, 1.0)
        except Exception:
            continue
        arr = np.asarray(out, dtype=np.float32)
        if arr.ndim != 3 or arr.shape[2] < 3:
            continue
        rgb = arr[:, :, :3]
        if rgb.max() > 1.5:
            rgb = rgb / 255.0
        std = float(rgb.std())
        if std > PAINT_NEUTRALITY_THRESHOLD:
            suspects.append((stem, category, std))

    if suspects:
        msg = "Spec_driven paint_fns adding too much variation (SPB-78 doctrine):\n"
        for stem, cat, std in suspects[:10]:
            msg += f"  {std:.4f}  {cat:32s}  {stem}\n"
        if len(suspects) > 10:
            msg += f"  ... and {len(suspects) - 10} more\n"
        pytest.fail(msg)


def test_registry_placeholder_orphans_match_spb87_baseline():
    """SPB-87 baseline: only the known 12 stone/textile IDs may use
    placeholder shims. Any new orphan beyond that is a regression — likely
    a new module hitting the same boot-order bug stone_textile.py did.

    If SPB-87 is resolved, shrink SPB87_KNOWN_BASE_ORPHANS in this file
    to the new (smaller) baseline.
    """
    found_base = set()
    for sid, e in eng.BASE_REGISTRY.items():
        if not isinstance(e, dict):
            continue
        if _is_placeholder(e.get("paint_fn")) or _is_placeholder(e.get("base_spec_fn")):
            found_base.add(sid)

    found_mono = set()
    for sid, v in eng.MONOLITHIC_REGISTRY.items():
        if not isinstance(v, tuple) or len(v) < 2:
            continue
        if _is_placeholder(v[0]) or _is_placeholder(v[1]):
            found_mono.add(sid)

    new_base = found_base - SPB87_KNOWN_BASE_ORPHANS
    stale_base = SPB87_KNOWN_BASE_ORPHANS - found_base
    if new_base:
        pytest.fail(
            f"NEW placeholder-shim orphans in BASE_REGISTRY (beyond SPB-87 baseline):\n  "
            + "\n  ".join(sorted(new_base))
            + "\nMost likely a new module hit the boot-order bug stone_textile.py did."
        )
    if found_mono:
        pytest.fail(
            f"PLACEHOLDER orphans appeared in MONOLITHIC_REGISTRY (baseline was 0):\n  "
            + "\n  ".join(sorted(found_mono))
        )
    if stale_base:
        # SPB-87 resolved — shrink the baseline in this file.
        pytest.fail(
            f"SPB-87 baseline list is now stale. These IDs are no longer orphans:\n  "
            + "\n  ".join(sorted(stale_base))
            + "\nRemove them from SPB87_KNOWN_BASE_ORPHANS in this test file."
        )


def test_spec_driven_base_paint_stays_neutral():
    """SPB-91 doctrine: spec_driven BASE_REGISTRY paint_fns must stay near-
    neutral on neutral input. Counterpart to test_spec_driven_monolithic_
    paint_stays_neutral, but walks BASE_REGISTRY (where Enhanced Foundation
    lives — the original test only covered monolithics).

    Owner critique 2026-05-15: "All of the enhancements on the paint side
    of it was just flipping around diagonal lines." That was multi_scale_
    noise grain inside _subtle_grain. Per the 2026-04-21 painter mandate
    Foundation Bases must be flat — paint belongs on the spec channel.
    This test fails if any spec_driven BASE paint_fn produces std > 0.05
    on a neutral 0.5 substrate.
    """
    categories = _parse_scorecard_categories()
    base = eng.BASE_REGISTRY

    neutral = np.full((128, 128, 3), 0.5, dtype=np.float32)
    mask = np.ones((128, 128), dtype=np.float32)

    suspects = []
    for fid_with_prefix, category in categories.items():
        if not is_spec_driven(category):
            continue
        surface, _, stem = fid_with_prefix.partition(":")
        if surface != "base":
            continue
        entry = base.get(stem)
        if not entry or not isinstance(entry, dict):
            continue
        paint_fn = entry.get("paint_fn")
        if not callable(paint_fn):
            continue
        seed = hash(stem) & 0x7FFFFFFF
        try:
            out = paint_fn(neutral.copy(), (128, 128), mask, seed, 1.0, 1.0)
        except Exception:
            continue
        arr = np.asarray(out, dtype=np.float32)
        if arr.ndim != 3 or arr.shape[2] < 3:
            continue
        rgb = arr[:, :, :3]
        if rgb.max() > 1.5:
            rgb = rgb / 255.0
        std = float(rgb.std())
        if std > PAINT_NEUTRALITY_THRESHOLD:
            suspects.append((stem, category, std))

    if suspects:
        msg = "Spec_driven BASE_REGISTRY paint_fns adding too much variation (SPB-91 doctrine):\n"
        for stem, cat, std in suspects[:10]:
            msg += f"  {std:.4f}  {cat:32s}  {stem}\n"
        if len(suspects) > 10:
            msg += f"  ... and {len(suspects) - 10} more\n"
        pytest.fail(msg)


def test_pattern_design_monolithic_paint_has_structure():
    """Pattern_design doctrine mirror (tick 41): paint_fns for finishes in
    pattern_design categories must produce paint output with substantial
    STRUCTURE when called on a neutral substrate. Owner brief 2026-05-14:
    "regular patterns are about DESIGN, not COLOR. Pattern quality lives
    in pattern STRUCTURE."

    Too-quiet paint output = pattern not delivering its job, the inverse
    violation of Ghost Geometry's tick-30 "paint too loud" problem.

    Source audit: scripts/audit_pattern_design_paint_richness.py
    """
    categories = _parse_scorecard_categories()
    mono = eng.MONOLITHIC_REGISTRY

    neutral = np.full((128, 128, 3), 0.5, dtype=np.float32)
    mask = np.ones((128, 128), dtype=np.float32)

    too_quiet = []
    for fid_with_prefix, category in categories.items():
        if not is_pattern_design(category):
            continue
        surface, _, stem = fid_with_prefix.partition(":")
        if surface != "monolithic":
            continue
        entry = mono.get(stem)
        if not entry or not isinstance(entry, tuple) or len(entry) < 2:
            continue
        paint_fn = entry[1]
        if not callable(paint_fn):
            continue
        seed = hash(stem) & 0x7FFFFFFF
        try:
            out = paint_fn(neutral.copy(), (128, 128), mask, seed, 1.0, 1.0)
        except Exception:
            continue
        arr = np.asarray(out, dtype=np.float32)
        if arr.ndim != 3 or arr.shape[2] < 3:
            continue
        rgb = arr[:, :, :3]
        if rgb.max() > 1.5:
            rgb = rgb / 255.0
        std = float(rgb.std())
        if std < PATTERN_DESIGN_PAINT_RICHNESS_THRESHOLD:
            too_quiet.append((stem, category, std))

    if too_quiet:
        msg = "Pattern_design paint_fns producing near-flat paint on neutral substrate:\n"
        for stem, cat, std in too_quiet[:10]:
            msg += f"  {std:.4f}  {cat:32s}  {stem}\n"
        if len(too_quiet) > 10:
            msg += f"  ... and {len(too_quiet) - 10} more\n"
        pytest.fail(msg)


def test_pattern_image_chroma_post_spb94():
    """SPB-94 doctrine: pattern_image finishes must actually carry color.

    This test SELF-ACTIVATES post-SPB-94. Logic:
    * If `FID_INTENT_OVERRIDE` doesn't exist in surface_intent.py (pre-SPB-94
      state), skip — the doctrine doesn't match reality yet.
    * If it does exist, every category-or-fid pattern_image finish must
      have mean RGB cosine alignment ≤ 0.97 across red/green/blue probes
      (= the finish actually brings color of its own, not just pass-through).

    Tick 66 audit found 16/17 "Artistic & Cultural" finishes at cosine
    exactly 1.0000 (pure pass-through). Only tribal_celtic_spiral at 0.66.
    After SPB-94 applies the category demotion + tribal_celtic_spiral
    override, only that one finish is classified as pattern_image and the
    test passes cleanly.
    """
    try:
        from engine.paint_v2.surface_intent import (
            FID_INTENT_OVERRIDE, get_intent, PATTERN_IMAGE,
        )
    except ImportError:
        pytest.skip("SPB-94 not yet applied (FID_INTENT_OVERRIDE absent)")
    # Sanity: must be the fid-aware version
    try:
        get_intent("Foundation", fid="base:f_chrome")
    except TypeError:
        pytest.skip("SPB-94 partial: get_intent doesn't accept fid yet")

    pat_registry = getattr(eng, "PATTERN_REGISTRY", {})
    categories = _parse_scorecard_categories()

    miscategorized = []
    for fid_with_prefix, category in categories.items():
        if get_intent(category, fid=fid_with_prefix) != PATTERN_IMAGE:
            continue
        surface, _, stem = fid_with_prefix.partition(":")
        if surface != "pattern" or stem not in pat_registry:
            continue
        entry = pat_registry[stem]
        paint_fn = entry.get("paint_fn") if isinstance(entry, dict) else None
        if not callable(paint_fn):
            continue
        # Probe red / green / blue (small size for speed)
        cosines = []
        for c in (np.array([0.8, 0.0, 0.0], dtype=np.float32),
                  np.array([0.0, 0.8, 0.0], dtype=np.float32),
                  np.array([0.0, 0.0, 0.8], dtype=np.float32)):
            paint_in = np.broadcast_to(c, (96, 96, 3)).copy()
            mask = np.ones((96, 96), dtype=np.float32)
            try:
                out = paint_fn(paint_in, (96, 96), mask,
                               hash(stem) & 0x7FFFFFFF, 1.0, 1.0)
            except Exception:
                continue
            arr = np.asarray(out, dtype=np.float32)[:, :, :3]
            if arr.max() > 1.5:
                arr = arr / 255.0
            m = arr.reshape(-1, 3).mean(axis=0)
            na = float(np.linalg.norm(c))
            nm = float(np.linalg.norm(m))
            if na > 1e-6 and nm > 1e-6:
                cosines.append(float(np.dot(c, m) / (na * nm)))
        if not cosines:
            continue
        mean_cos = float(np.mean(cosines))
        if mean_cos > 0.97:
            miscategorized.append((stem, category, mean_cos))

    if miscategorized:
        msg = "pattern_image finishes that don't actually carry color (SPB-94 doctrine):\n"
        for stem, cat, mc in miscategorized[:10]:
            msg += f"  cosine={mc:.4f}  {cat:32s}  {stem}\n"
        if len(miscategorized) > 10:
            msg += f"  ... and {len(miscategorized) - 10} more\n"
        pytest.fail(msg)


def test_ghost_geometry_paint_fn_stays_quiet():
    """SPB-78 specific: the Ghost Geometry paint_fn quietening (tick 30)
    must not be reverted. Probes a representative ghost_hex paint_fn on
    a neutral gray paint and asserts the std stays below 0.04 (the tick
    30 fix landed at ~0.017; pre-fix was ~0.10).
    """
    entry = eng.MONOLITHIC_REGISTRY.get("ghost_hex")
    assert entry is not None, "ghost_hex missing from MONOLITHIC_REGISTRY"
    paint_fn = entry[1]
    assert callable(paint_fn)

    neutral = np.full((128, 128, 3), 0.5, dtype=np.float32)
    mask = np.ones((128, 128), dtype=np.float32)
    out = paint_fn(neutral.copy(), (128, 128), mask, 12345, 1.0, 1.0)
    arr = np.asarray(out, dtype=np.float32)
    if arr.max() > 1.5:
        arr = arr / 255.0
    std = float(arr[:, :, :3].std())
    assert std < 0.04, (
        f"ghost_hex paint_fn std={std:.4f} exceeds tick-30 ceiling of 0.04. "
        "The SPB-78 quietening patch may have been reverted — check "
        "_make_ghost_geometry_fast in engine/expansions/fusions.py."
    )
