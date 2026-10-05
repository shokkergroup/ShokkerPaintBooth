"""Regression guardrail — SPEC_PATTERN channel-routing coverage.

## Context (Iter 3, ship-readiness audit, 2026-04-22)

``engine.compose._infer_spec_pattern_default_channels`` parses each
spec-pattern function's docstring for ``Targets R=Metallic``,
``Targets G=Roughness``, ``Targets B=Clearcoat`` declarations and
routes accordingly. Functions without any such tag fall back to
``"MR"``.

Audit baseline as of 2026-04-22:

  Total SPEC_PATTERN_CATALOG entries:               262
  Patterns with `Targets [RGB]=...` docstring tag:  144
  Patterns falling back to "MR" (no tag):           118

Of the 118 fallbacks, 34 have NAME hints that suggest a more
specific routing (19 metallic-family names → M; 9 weave/matte → R;
6 wet/ripple → CC). A **12-entry sample** of these 34 was behaviorally
probed (Pillman, Iter 3 of the 2026-04-22 ship-readiness audit —
samples: flake_scatter, gold_flake, holographic_flake, micro_sparkle,
sparkle_champagne, sparkle_constellation, spec_carbon_2x2_twill,
spec_carbon_3k_fine, spec_kevlar_weave, concentric_ripple, wave_ripple,
sparkle_rain). All 12 sampled entries produced valid 2D output with
reasonable variance at MR routing — they are NOT broken, just
arguably suboptimally routed by default. The remaining 22 were NOT
individually probed; the sample was chosen to cover all three
family suspicions (metallic / weave / wet-ripple) but cannot
certify every entry.

Painter-visible impact TODAY: low. The patterns still render and
produce painter-visible modulation; painters can explicitly set
``channels`` per pattern-stack-entry for the routing they want.

## What this test pins

  1. Total pattern count hasn't shrunk unexpectedly (catalog
     churn floor).
  2. Count of patterns with ``Targets`` tags hasn't dropped (we
     don't want regressions that DECLARE fewer channel intents
     than we have today).
  3. The inference function itself still prefers docstring tags,
     returns the expected channel characters, and falls back to
     ``"MR"`` as last resort. Behavioral pin against subtle
     reordering.

If this ratchet fires:
  - Shrink of total count: spec patterns got deleted — investigate
    catalog churn, possibly update the floor.
  - Drop in tagged count: a spec-pattern author stripped docstring
    tags without replacement metadata — restore the tags OR add
    them elsewhere (e.g. engine-side defaultChannels dict).
  - Inference output change: the heuristic got edited — make sure
    the change matches the JS mirror at
    ``paint-booth-2-state-zones.js:6903 _inferSpecPatternDefaultChannels``.
"""

import io
import contextlib

import pytest


@pytest.fixture(scope="module")
def spec_pattern_catalog():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.spec_patterns import PATTERN_CATALOG
    return PATTERN_CATALOG


@pytest.fixture(scope="module")
def infer_fn():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.compose import _infer_spec_pattern_default_channels, _SPEC_TARGETS_PATTERN
    return _infer_spec_pattern_default_channels, _SPEC_TARGETS_PATTERN


def test_spec_pattern_total_count_floor(spec_pattern_catalog):
    """Catalog must not shrink below 250 (Iter 3 baseline: 262).
    A sudden drop indicates catalog churn or import error — both
    worth a hard look before shipping."""
    n = len(spec_pattern_catalog)
    assert n >= 250, (
        f"SPEC_PATTERN_CATALOG has {n} entries, below the 250 "
        f"floor. Iter 3 baseline was 262 (2026-04-22). Investigate "
        f"whether this is intentional trimming or broken imports."
    )


def test_spec_pattern_tagged_coverage_floor(spec_pattern_catalog, infer_fn):
    """At least 140 patterns must carry docstring `Targets [RGB]=`
    tags. Baseline was 144 at Iter 3 pin time. If this drops,
    somebody removed channel-intent metadata and the dispatch is
    now blindly routing those to MR."""
    _, SPEC_TARGETS = infer_fn
    tagged = 0
    for pid, fn in spec_pattern_catalog.items():
        if not callable(fn): continue
        doc = (getattr(fn, "__doc__", "") or "")
        if SPEC_TARGETS.search(doc):
            tagged += 1
    assert tagged >= 140, (
        f"Only {tagged} spec patterns have `Targets [RGB]=...` "
        f"docstring tags (baseline: 144 at 2026-04-22). Someone "
        f"removed channel-intent metadata; these patterns now fall "
        f"back to 'MR' routing, potentially painting wrong channels."
    )


@pytest.mark.parametrize("docstring, expected", [
    ("Targets R=Metallic\n", "M"),
    ("Targets G=Roughness\n", "R"),
    ("Targets B=Clearcoat\n", "C"),
    ("Targets R=Metallic, G=Roughness\n", "MR"),
    ("Targets R=Metallic and B=Clearcoat\n", "MC"),
    ("Targets G=Roughness, B=Clearcoat\n", "RC"),
    ("Targets R=Metallic, G=Roughness, B=Clearcoat\n", "MRC"),
    # No targets → fallback
    ("Just a description, no targets.", "MR"),
    ("", "MR"),
    (None, "MR"),
])
def test_inference_function_channel_mapping(infer_fn, docstring, expected):
    """Pin the `Targets R/G/B=...` → `M/R/C` mapping and the
    fallback behavior. If this test breaks, the inference logic
    has been altered and JS mirror parity must be re-verified."""
    infer, _ = infer_fn

    class _StubFn:
        __doc__ = docstring
    if docstring is None:
        stub = None
    else:
        stub = _StubFn()

    result = infer(stub)
    assert result == expected, (
        f"docstring={docstring!r} → got {result!r}, expected {expected!r}. "
        f"Inference logic changed. Check parity with JS at "
        f"paint-booth-2-state-zones.js:6903 _inferSpecPatternDefaultChannels."
    )


def test_no_blanket_mr_dispatch_in_compose():
    """Structural pin: compose.py must consult the inference function
    (or an explicit channels value) before dispatching — no hardcoded
    `channels="MR"` literal at the spec-pattern dispatch. If this
    test fires, somebody regressed to the pre-HEENAN-overnight-iter-2
    bug class where authored clearcoat-depth patterns got routed to
    MR regardless of intent."""
    from pathlib import Path
    src = Path(__file__).resolve().parent.parent / "engine" / "compose.py"
    text = src.read_text(encoding="utf-8")

    # The 2 dispatch sites (spec-pattern stack, third-overlay spec stack)
    # must each reference _infer_spec_pattern_default_channels.
    hits = text.count("_infer_spec_pattern_default_channels(")
    assert hits >= 2, (
        f"engine/compose.py has only {hits} references to "
        f"_infer_spec_pattern_default_channels (expected >= 2 at both "
        f"spec-pattern dispatch sites). Someone short-circuited the "
        f"inference — the channels='MR' blanket-default bug is back."
    )


def test_inference_falls_back_to_mr_not_something_else(infer_fn):
    """Pin the exact fallback value. If someone changed the default
    to 'M' or '' the painter's existing liveries will render
    differently — such a change requires painter sign-off, not a
    silent code edit."""
    infer, _ = infer_fn

    class _EmptyFn:
        __doc__ = "some non-targeting description"

    result = infer(_EmptyFn())
    assert result == "MR", (
        f"Fallback channels are now {result!r} instead of 'MR'. "
        f"This silently changes how 118+ spec patterns render. If "
        f"intentional, painter sign-off is required — update this "
        f"test AND the JS mirror in paint-booth-2-state-zones.js."
    )
