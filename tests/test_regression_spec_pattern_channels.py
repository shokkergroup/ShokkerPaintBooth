"""Regression guardrail — spec-pattern channel-routing.

## Original finding (2026-04-20, regression loop iter 3)

`engine/compose.py` dispatched spec-pattern layers with a blanket
`channels="MR"` default. That silently routed every spec pattern
to M+R when the layer dict lacked an explicit `channels` key, even
if the pattern's docstring authored a different channel:

    gold_leaf_torn           docstring: "Targets R=Metallic"  → should be M
    stippled_dots_fine       docstring: "Targets R=Metallic"  → should be M
    abstract_rothko_field    docstring: "Targets B=Clearcoat" → should be CC
    abstract_futurist_motion docstring: "Targets G=Roughness" → should be R

(Docstrings use iRacing RGBA-channel letters: R=Metallic,
G=Roughness, B=Clearcoat. In this codebase the Python variables
are `M_arr`, `R_arr`, `CC_arr`.)

Under the pre-fix default:
- gold_leaf_torn, stippled_dots_fine → M correct, but R also shifted
  (unintended roughness coupling).
- abstract_rothko_field → CC never touched; M and R shifted instead.
  The authored "soft clearcoat depth per field" effect was entirely
  absent unless the layer explicitly set channels="C".
- abstract_futurist_motion → R correct, but M also shifted.

## UPDATE 2026-04-21 HEENAN OVERNIGHT iter 2 — FIXED

`engine/compose.py` now resolves the default via
`_infer_spec_pattern_default_channels(sp_fn)`, which parses the
pattern function's docstring for `Targets [RGB]=...` declarations
and converts them to engine channel letters. Falls back to "MR"
only when the docstring has no Targets phrase. Applied at BOTH
compose dispatch sites (compose_finish AND compose_finish_stacked).

Strict back-compat: any saved zone with an explicit `channels`
value (including `channels="MR"`) is preserved unchanged — the
resolver only runs when the key is absent or empty. No painter-save
breakage.

Behavioral proof: `tests/test_runtime_spec_channel_inference.py`
drives the actual compose pipeline on a 32×32 canvas with each of
the 4 named patterns, both absent-channels and explicit-channels,
and asserts bit-for-bit identity between absent-channels output
and explicit-inferred-channels output (proving correct routing)
AND divergence from explicit-MR output (proving the fix changed
behavior for the bug case).

## What this test still does

Asserts that the blanket `sp_layer.get("channels", "MR")` fallback
is GONE from every compose dispatch site, and that the
`_infer_spec_pattern_default_channels` resolver is present and
called from ≥2 call sites. Guards against a regression that
restores the old broken fallback.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
COMPOSE = REPO / "engine" / "compose.py"


def test_spec_pattern_dispatch_uses_inferred_default_resolver():
    """After the 2026-04-21 HEENAN overnight iter 2 fix, every spec-
    pattern dispatch site in `engine/compose.py` must use the
    docstring-inferred default channel resolver (`_infer_spec_pattern_default_channels`)
    instead of the blanket `sp_layer.get("channels", "MR")` fallback.

    The old fallback silently routed `abstract_rothko_field` (intent
    `Targets B=Clearcoat`) to M+R only — its authored clearcoat-depth
    effect was never applied for direct API calls or in the brief
    window before the JS normalize timer fires. Strict back-compat
    is preserved by only invoking the resolver when the layer's
    `channels` key is absent or empty (any explicit value is honored).

    Behavioral verification of this routing (including the explicit-
    channels back-compat case) lives in
    `tests/test_runtime_spec_channel_inference.py`.
    """
    src = COMPOSE.read_text(encoding="utf-8")
    # Old-style fallback must be GONE from every dispatch site.
    bad_pattern = re.compile(
        r'sp_channels\s*=\s*sp_layer\.get\(\s*["\']channels["\']\s*,\s*["\']MR["\']\s*\)'
    )
    bad_matches = list(bad_pattern.finditer(src))
    assert not bad_matches, (
        f"engine/compose.py still contains {len(bad_matches)} "
        f"`sp_channels = sp_layer.get(\"channels\", \"MR\")` "
        f"occurrence(s). The blanket-MR fallback was supposed to be "
        f"replaced by `_infer_spec_pattern_default_channels` — "
        f"refresh those sites to match the iter 2 fix."
    )

    # And the resolver must be present and called from every site
    # that still computes sp_channels.
    assert "def _infer_spec_pattern_default_channels" in src, (
        "engine/compose.py no longer defines "
        "`_infer_spec_pattern_default_channels`. The docstring-"
        "inferred-channels resolver was removed — the bug will "
        "silently come back if someone restores the old fallback."
    )
    resolver_calls = src.count("_infer_spec_pattern_default_channels(")
    # Expect: 1 definition + ≥2 call sites (compose_finish + compose_finish_stacked)
    assert resolver_calls >= 3, (
        f"_infer_spec_pattern_default_channels has only "
        f"{resolver_calls} reference(s) (expected ≥3: 1 def + ≥2 "
        f"call sites). One of the dispatch paths may have been "
        f"left on the old broken fallback."
    )


@pytest.mark.parametrize("pattern_name,intended_channel,docstring_phrase", [
    ("gold_leaf_torn",           "M",  "Targets R=Metallic"),
    ("stippled_dots_fine",       "M",  "Targets R=Metallic"),
    ("abstract_rothko_field",    "C",  "Targets B=Clearcoat"),
    ("abstract_futurist_motion", "R",  "Targets G=Roughness"),
])
def test_spec_pattern_docstring_declares_intent(pattern_name, intended_channel, docstring_phrase):
    """Each of the named patterns must still declare its intended
    channel in its docstring.

    This is not a behavioural test — it just ensures the authored
    intent stays documented. If somebody rewrites a pattern's
    docstring and strips the "Targets X=..." line, the pre-existing
    mismatch with the compose.py default becomes invisible. This
    test keeps it visible.
    """
    from engine import spec_patterns as sp
    fn = getattr(sp, pattern_name, None)
    assert fn is not None, f"spec pattern {pattern_name} not found"
    doc = (fn.__doc__ or "")
    assert docstring_phrase in doc, (
        f"{pattern_name} docstring no longer contains `{docstring_phrase}`. "
        f"The authored-intent declaration that this pattern targets the "
        f"{intended_channel} channel has been lost. Either restore the "
        f"docstring or update this test."
    )
