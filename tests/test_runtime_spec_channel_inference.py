"""HEENAN 5H OVERNIGHT — iter 2 behavioral proof for the
spec-pattern channel-routing fix in engine/compose.py.

Pre-fix state: `sp_channels = sp_layer.get("channels", "MR")` blanket-
defaulted every spec-pattern layer to M+R when the `channels` key was
absent. That silently routed `abstract_rothko_field` (authored intent:
B=Clearcoat) to M+R and never touched CC — its docstring-declared
clearcoat-depth effect was entirely absent under direct API calls or
during the brief window before the JS normalize timer fires.

Post-fix: when `channels` is absent or empty, compose now inspects the
pattern function's docstring for `Targets [RGB]=...` declarations and
routes accordingly:
  Targets R=Metallic   → 'M'
  Targets G=Roughness  → 'R'
  Targets B=Clearcoat  → 'C'

When the docstring has no Targets phrase, falls back to "MR" (matches
pre-fix behavior for patterns that never declared intent — strict
back-compat for non-annotated patterns).

When the layer dict has an explicit `channels` value (any truthy
string), that value is preserved unchanged — even if it disagrees
with the docstring. This protects every existing painter save.

This test exercises the actual compose pipeline, not the resolver
function in isolation.
"""

import numpy as np
import pytest


# --- Resolver-level tests (catches docstring-parsing regressions) ---

@pytest.fixture(scope="module")
def resolver():
    from engine.compose import _infer_spec_pattern_default_channels
    return _infer_spec_pattern_default_channels


@pytest.fixture(scope="module")
def spec_catalog():
    from engine.spec_patterns import PATTERN_CATALOG
    return PATTERN_CATALOG


@pytest.mark.parametrize("pattern_name,expected_channels", [
    # Original strict-form patterns (use the "Targets R=Metallic" phrasing)
    ("gold_leaf_torn", "M"),
    ("stippled_dots_fine", "M"),
    ("abstract_rothko_field", "C"),
    ("abstract_futurist_motion", "R"),
    # 2026-04-21 iter 7 — broadened-regex patterns (abbreviated form
    # like "R=Metallic." at end of docstring, no "Targets" prefix).
    # These previously fell into the MR default; now inferred correctly.
    ("guilloche_hobnail", "M"),       # "R=Metallic."
    ("guilloche_moire_eng", "M"),     # "R=Metallic."
    ("hairline_polish", "R"),         # "G=Roughness."
    ("bead_blast_uniform", "R"),      # "G=Roughness."
    ("jeweling_circles", "M"),        # "R=Metallic."
    ("knurl_diamond", "MR"),          # "G=Roughness + R=Metallic." → canonical MR
])
def test_resolver_matches_docstring_intent(
    resolver, spec_catalog, pattern_name, expected_channels
):
    fn = spec_catalog.get(pattern_name)
    assert fn is not None, f"{pattern_name} missing from PATTERN_CATALOG"
    got = resolver(fn)
    assert got == expected_channels, (
        f"{pattern_name}: docstring inference returned {got!r}, "
        f"expected {expected_channels!r}. Either the docstring's "
        f"channel-intent phrase changed or the resolver regexp regressed."
    )


def test_resolver_emits_channels_in_canonical_mrc_order():
    """A pattern whose docstring declares multiple channels in a
    different order (e.g. 'G=Roughness + R=Metallic.') must be
    reported in canonical MRC engine-channel order — matches the
    JS-side resolver's fixed-order output and keeps test assertions
    stable regardless of docstring phrasing.
    """
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        from engine.compose import _infer_spec_pattern_default_channels
        from engine.spec_patterns import PATTERN_CATALOG

    # knurl_diamond declares 'G=Roughness + R=Metallic.' — G comes
    # first in the doc, but MRC canonical order puts M before R.
    fn = PATTERN_CATALOG.get("knurl_diamond")
    assert fn is not None, "knurl_diamond missing from PATTERN_CATALOG"
    got = _infer_spec_pattern_default_channels(fn)
    # Expected "MR" (canonical M then R), NEVER "RM".
    assert got == "MR", (
        f"Expected canonical 'MR' order, got {got!r}. The resolver "
        f"is emitting channels in docstring-source order instead of "
        f"the engine-canonical MRC order — regression."
    )


def test_resolver_falls_back_to_MR_when_no_targets_declaration(
    resolver, spec_catalog
):
    """A pattern with no `Targets X=...` phrase in its docstring must
    fall back to "MR" — matches pre-fix behavior for patterns that
    never declared their target channel.
    """
    # banded_rows is a generic pattern with no Targets phrase
    fn = spec_catalog.get("banded_rows")
    assert fn is not None
    assert resolver(fn) == "MR"


def test_resolver_handles_none_safely(resolver):
    """If the catalog lookup misses (sp_fn is None), the resolver
    must not crash — just return the safe default.
    """
    assert resolver(None) == "MR"


# --- Behavioral: actual compose-time routing on a 32×32 canvas ---

def _shape():
    return (32, 32)


def _mask():
    return np.ones(_shape(), dtype=np.float32)


def _absent_channels_layer(pattern_name, opacity=0.8, _range=120.0):
    """Build a spec_pattern_stack entry with NO `channels` key — the
    case where the inferred-default fix takes effect."""
    return {
        "pattern": pattern_name,
        "opacity": opacity,
        "blend_mode": "normal",
        "range": _range,
        # deliberately no `channels`
    }


def _explicit_channels_layer(pattern_name, channels, opacity=0.8, _range=120.0):
    """Build a spec_pattern_stack entry WITH explicit channels — the
    back-compat case where the explicit value must be preserved."""
    return {
        "pattern": pattern_name,
        "opacity": opacity,
        "blend_mode": "normal",
        "range": _range,
        "channels": channels,
    }


def _compose_with_stack(stack):
    """Run compose_finish with a small canvas and the supplied
    spec_pattern_stack, return the (M, R, CC) channel arrays."""
    from engine.compose import compose_finish
    spec = compose_finish(
        "candy", "none",
        _shape(), _mask(), 42, 1.0,
        spec_pattern_stack=stack,
    )
    spec = np.asarray(spec)
    assert spec.shape == (32, 32, 4), f"unexpected shape {spec.shape}"
    return spec[:, :, 0], spec[:, :, 1], spec[:, :, 2]  # M, R, CC


def _baseline_no_overlay():
    """Compose with no spec_pattern_stack — gives the channel values
    the base alone produces. Used as a reference to detect which
    channel got modified by an overlay."""
    return _compose_with_stack([])


@pytest.mark.parametrize("pattern_name,intended_channel", [
    ("gold_leaf_torn", "M"),
    ("stippled_dots_fine", "M"),
    ("abstract_rothko_field", "C"),
    ("abstract_futurist_motion", "R"),
])
def test_absent_channels_matches_explicit_inferred_target(
    pattern_name, intended_channel
):
    """A spec-pattern layer with no `channels` key must produce
    BIT-FOR-BIT identical output to the same layer with `channels`
    explicitly set to the docstring-inferred target. This proves the
    inferred-default fix routes correctly without depending on
    sensitivity thresholds (which can be defeated by clip/rounding
    noise elsewhere in the pipeline).
    """
    M_inferred, R_inferred, CC_inferred = _compose_with_stack([
        _absent_channels_layer(pattern_name)
    ])
    M_explicit, R_explicit, CC_explicit = _compose_with_stack([
        _explicit_channels_layer(pattern_name, intended_channel)
    ])

    assert np.array_equal(M_inferred, M_explicit), (
        f"{pattern_name}: M channel differs between absent-channels "
        f"and explicit-{intended_channel} cases. Routing mismatch — "
        f"max diff = {np.abs(M_inferred - M_explicit).max()}"
    )
    assert np.array_equal(R_inferred, R_explicit), (
        f"{pattern_name}: R channel differs between absent-channels "
        f"and explicit-{intended_channel} cases. Routing mismatch — "
        f"max diff = {np.abs(R_inferred - R_explicit).max()}"
    )
    assert np.array_equal(CC_inferred, CC_explicit), (
        f"{pattern_name}: CC channel differs between absent-channels "
        f"and explicit-{intended_channel} cases. Routing mismatch — "
        f"max diff = {np.abs(CC_inferred - CC_explicit).max()}"
    )


@pytest.mark.parametrize("pattern_name,intended_channel,wrong_channel", [
    ("gold_leaf_torn", "M", "MR"),       # was MR by default; fix routes to M
    ("abstract_rothko_field", "C", "MR"),  # was MR by default; fix routes to C
])
def test_absent_channels_diverges_from_pre_fix_blanket_MR(
    pattern_name, intended_channel, wrong_channel
):
    """Sanity check: the post-fix behavior must DIFFER from the
    pre-fix blanket-MR behavior on patterns whose authored intent
    isn't MR. If absent-channels still equals explicit-MR for these
    patterns, the fix did nothing.
    """
    M_inferred, R_inferred, CC_inferred = _compose_with_stack([
        _absent_channels_layer(pattern_name)
    ])
    M_oldway, R_oldway, CC_oldway = _compose_with_stack([
        _explicit_channels_layer(pattern_name, wrong_channel)
    ])
    # At least one channel must differ between the two — that's how we
    # know the fix changed routing for this pattern.
    diff = (
        not np.array_equal(M_inferred, M_oldway)
        or not np.array_equal(R_inferred, R_oldway)
        or not np.array_equal(CC_inferred, CC_oldway)
    )
    assert diff, (
        f"{pattern_name}: absent-channels output is IDENTICAL to "
        f"explicit-{wrong_channel} output. The inferred-default fix "
        f"didn't change routing. Either the resolver returned "
        f"{wrong_channel!r} (regression) or the fix isn't being "
        f"reached at this code path."
    )


def test_explicit_channels_MR_overrides_docstring_intent_for_rothko():
    """Strict back-compat: a saved zone with `channels="MR"` on
    abstract_rothko_field (whose docstring intent is "C") must STILL
    route to M+R, not be silently overridden by the inferred default.

    This protects every painter who has the existing behavior in their
    saved configs from a surprise-change after the fix lands.
    """
    base_M, base_R, base_CC = _baseline_no_overlay()
    over_M, over_R, over_CC = _compose_with_stack([
        _explicit_channels_layer("abstract_rothko_field", "MR")
    ])

    def changed(a, b):
        return float(np.abs(a.astype(np.float32) - b.astype(np.float32)).max()) > 0.5

    M_changed  = changed(base_M, over_M)
    R_changed  = changed(base_R, over_R)
    CC_changed = changed(base_CC, over_CC)

    assert M_changed and R_changed, (
        "Explicit channels='MR' did not route to M and R as the "
        "saved zone requested. Back-compat broken."
    )
    assert not CC_changed, (
        "Explicit channels='MR' leaked into CC. The explicit override "
        "is being silently re-inferred, breaking saved-config back-compat."
    )


def test_explicit_channels_C_routes_to_clearcoat_for_metallic_pattern():
    """Symmetric back-compat: a saved zone with `channels="C"` on
    gold_leaf_torn (whose docstring intent is "M") must route to CC,
    not silently re-inferred to M.
    """
    base_M, base_R, base_CC = _baseline_no_overlay()
    over_M, over_R, over_CC = _compose_with_stack([
        _explicit_channels_layer("gold_leaf_torn", "C")
    ])

    def changed(a, b):
        return float(np.abs(a.astype(np.float32) - b.astype(np.float32)).max()) > 0.5

    assert changed(base_CC, over_CC), (
        "Explicit channels='C' did not modify the CC channel."
    )
    assert not changed(base_M, over_M), (
        "Explicit channels='C' leaked into M. Inferred default is "
        "overriding explicit values."
    )
    assert not changed(base_R, over_R), (
        "Explicit channels='C' leaked into R."
    )
