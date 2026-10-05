"""Regression guardrail — Foundation Bases selected as a DECAL specFinish
must produce FLAT spec (no texture, honoring the Foundation flat-spec
contract) AND must not raise TypeError (which was previously swallowed
silently at the DECAL dispatch site).

## Context (2026-04-22 HEENAN FAMILY overnight Iter 5)

The painter-visible UI flow:

  paint-booth-6-ui-boot.js:447-497 — decal specFinish <select> lists
  all 19 Foundation Base ids (f_metallic, f_pearl, f_chrome, ...)

  paint-booth-3-canvas.js:5821  +  paint-booth-5-api-render.js:1809/
  2041/2413/2586 — export paths pass
  `decal_spec_finishes: [{specFinish: f_*}]` to the server

  shokker_engine_v2.py:10932 — server reads the literal string and
  dispatches `DECAL_SPEC_MAP.get(spec_name, spec_gloss)((h, w),
  decal_alpha, seed + 7777, 1.0)` at the 4-arg signature.

Pre-fix state:
  - DECAL_SPEC_MAP mapped foundation ids to engine.spec_paint.*
    functions. spec_metallic / spec_pearl / spec_carbon_fiber produced
    visible per-pixel TEXTURE on the decal region (spreads of 80 / 168
    / 50 units respectively) — violated the Foundation flat-spec
    contract.
  - spec_satin_metal / spec_brushed_titanium / spec_anodized /
    spec_frozen / spec_gloss / spec_matte / spec_satin have 5-arg
    signatures requiring `base_r`. The 4-arg dispatch site raises
    TypeError, which is silently swallowed by the outer try/except —
    painter's chosen spec finish produces NO output.

Post-fix state (this iter's target):
  - Every f_* id routes through ``_mk_flat_foundation_decal_spec(fid)``
    which returns a flat 4-channel uint8 spec using the foundation's
    own M/R/CC from BASE_REGISTRY. Zero spread on all three channels.
    No TypeError.

## What this test proves

1. The module-level factory ``_mk_flat_foundation_decal_spec`` is
   importable (catches a regression that removes or renames it).
2. For all 19 Foundation Base ids shown in the UI dropdown, calling
   the factory's callable with the exact call signature used at the
   dispatch site (``(shape, mask, seed, sm)``) returns:
   - a 4-channel uint8 array of the requested shape, and
   - zero per-channel spread (truly flat, honoring the contract), and
   - does NOT raise.
3. The M/R/CC values at each pixel match the foundation's BASE_REGISTRY
   values (with the _spec_foundation_flat R-floor applied).
4. The DECAL_SPEC_MAP construction site in shokker_engine_v2.py still
   references the module-level factory for f_* keys — catches a
   future refactor that silently re-inlines a textured function.

## Why this is the closing gap

Iter 3 proved the shim flat in isolation. Iter 5 closes the end-to-end
confidence by:
  (a) proving the SHIM THE ENGINE ACTUALLY USES is the flat one, and
  (b) source-pinning the call-site reference, so any regression
      that reroutes f_* back to textured spec_metallic/etc. fires
      immediately.
"""

import io
import contextlib
from pathlib import Path

import numpy as np
import pytest


REPO = Path(__file__).resolve().parent.parent
ENGINE_SRC = REPO / "shokker_engine_v2.py"


# The f_* foundation ids offered by the UI decal-specFinish dropdown
# (paint-booth-6-ui-boot.js decal fallback list). FOUNDATION ONE 2026-09-03:
# the flat BASES shelf is 20 perceptually distinct cells; these are its f_* members.
DECAL_FOUNDATION_IDS = [
    "f_chrome", "f_satin_chrome", "f_dark_chrome", "f_metallic",
    "f_matte_metallic", "f_pearl", "f_satin_pearl", "f_candy",
    "f_brushed", "f_frozen", "f_bead_blast", "f_powder_coat",
]


@pytest.fixture(scope="module")
def engine_module():
    """Import shokker_engine_v2 with init output suppressed."""
    import sys
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import shokker_engine_v2
    return shokker_engine_v2


def test_flat_foundation_decal_factory_is_module_level(engine_module):
    """The factory ``_mk_flat_foundation_decal_spec`` must be a public
    module-level symbol. Pre-Iter-5 it was a local closure inside
    build_multi_zone — impossible to test directly.

    If this test fails, someone re-inlined the factory into the
    dispatch site. Re-hoist it, OR update this test to reflect the
    new structure with equivalent behavioral coverage.
    """
    assert hasattr(engine_module, "_mk_flat_foundation_decal_spec"), (
        "shokker_engine_v2._mk_flat_foundation_decal_spec is missing. "
        "It was hoisted to module level in Iter 5 of the 2026-04-22 "
        "HEENAN FAMILY overnight so this test (and any future "
        "behavioral probe of the decal foundation-spec path) can import "
        "it directly."
    )
    assert callable(engine_module._mk_flat_foundation_decal_spec)


@pytest.mark.parametrize("fid", DECAL_FOUNDATION_IDS)
def test_decal_foundation_spec_is_truly_flat(engine_module, fid):
    """For every foundation id offered by the UI's decal-specFinish
    dropdown, calling the factory's closure at the exact call
    signature used by the dispatch site (line 10932) must:

      (a) return a 4-channel uint8 array of the requested shape,
      (b) have ZERO per-channel spread on M, R, CC (flat contract), and
      (c) not raise anything.

    Failure modes this catches:
      - Anybody re-wires f_* to a textured spec_* function
        (re-introduces pre-fix pattern).
      - Anybody changes the factory to call multi_scale_noise or
        add jitter.
      - The return shape/dtype drifts from (h, w, 4) uint8 and breaks
        the combined_spec blend at line 10937.
    """
    fn = engine_module._mk_flat_foundation_decal_spec(fid)
    mask = np.ones((48, 48), dtype=np.float32)

    spec = fn((48, 48), mask, 42, 1.0)

    assert isinstance(spec, np.ndarray), (
        f"{fid}: decal-spec callable returned {type(spec).__name__}, "
        f"expected np.ndarray"
    )
    assert spec.shape == (48, 48, 4), (
        f"{fid}: decal-spec shape {spec.shape}, expected (48, 48, 4)"
    )
    assert spec.dtype == np.uint8, (
        f"{fid}: decal-spec dtype {spec.dtype}, expected uint8"
    )

    for ch_idx, ch_name in enumerate(("M", "R", "CC")):
        ch = spec[:, :, ch_idx]
        spread = int(ch.max()) - int(ch.min())
        assert spread == 0, (
            f"{fid}: {ch_name} channel has spread={spread} on the decal "
            f"spec output. Foundation Bases must be FLAT. Someone "
            f"probably re-wired f_* through a textured spec_* function "
            f"or added jitter inside the factory."
        )


@pytest.mark.parametrize("fid", DECAL_FOUNDATION_IDS)
def test_decal_foundation_spec_honors_base_registry_values(
    engine_module, fid
):
    """Every f_* decal-spec output must carry the foundation's OWN
    M/R/CC values from BASE_REGISTRY (with the non-chrome R >= 15
    floor applied). Painter picked 'f_metallic as my decal spec
    finish' → decal region reads M=200, not M=0 or M=128 defaults.

    This test catches a regression where the factory starts returning
    a generic (flat) output that ignores the selected foundation — the
    flat-spec contract would be technically honored but the painter
    would lose the foundation's intended material look.
    """
    base = engine_module.BASE_REGISTRY.get(fid)
    assert base is not None, (
        f"{fid}: expected in BASE_REGISTRY (it's in the decal-specFinish "
        f"UI dropdown)"
    )
    expected_m = int(base.get("M", 0))
    expected_r_raw = int(base.get("R", 50))
    expected_cc = int(base.get("CC", 16))
    expected_r = expected_r_raw if expected_m >= 240 else max(expected_r_raw, 15)

    fn = engine_module._mk_flat_foundation_decal_spec(fid)
    spec = fn((8, 8), np.ones((8, 8), dtype=np.float32), 42, 1.0)

    assert int(spec[0, 0, 0]) == expected_m, (
        f"{fid}: M={int(spec[0, 0, 0])}, expected {expected_m} "
        f"(from BASE_REGISTRY[{fid!r}]['M'])"
    )
    assert int(spec[0, 0, 1]) == expected_r, (
        f"{fid}: R={int(spec[0, 0, 1])}, expected {expected_r} "
        f"(from BASE_REGISTRY R={expected_r_raw} with "
        f"{'chrome-no-floor' if expected_m >= 240 else 'R>=15 floor'})"
    )
    assert int(spec[0, 0, 2]) == expected_cc, (
        f"{fid}: CC={int(spec[0, 0, 2])}, expected {expected_cc} "
        f"(from BASE_REGISTRY[{fid!r}]['CC'])"
    )


def test_decal_spec_map_references_module_level_factory():
    """Structural pin: the DECAL_SPEC_MAP construction site inside
    ``build_multi_zone`` must reference the module-level
    ``_mk_flat_foundation_decal_spec`` for its f_* entries. Catches a
    regression where someone re-inlines a textured function for any
    f_* key.

    We check by source-text search: every line in the DECAL_SPEC_MAP
    literal whose key starts with "f_" must reference
    `_mk_flat_foundation_decal_spec`.
    """
    import re
    src = ENGINE_SRC.read_text(encoding="utf-8")

    # Locate the DECAL_SPEC_MAP block.
    m = re.search(r"DECAL_SPEC_MAP\s*=\s*\{", src)
    assert m, "DECAL_SPEC_MAP literal not found in shokker_engine_v2.py"
    # Walk to the matching close brace.
    depth = 1
    pos = m.end()
    while pos < len(src) and depth > 0:
        c = src[pos]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        pos += 1
    block = src[m.end():pos - 1]

    # For every f_* line, verify the RHS references the factory.
    offenders = []
    for line in block.splitlines():
        stripped = line.strip()
        lm = re.match(r'"(f_[a-z0-9_]+)"\s*:\s*(.+?),?\s*(?:#.*)?$', stripped)
        if not lm:
            continue
        fid = lm.group(1)
        rhs = lm.group(2).strip().rstrip(",")
        if "_mk_flat_foundation_decal_spec" not in rhs:
            offenders.append(f"{fid}: RHS is {rhs!r} (expected factory call)")

    assert not offenders, (
        "DECAL_SPEC_MAP has f_* entries NOT using the flat-foundation "
        "factory. These re-introduce the pre-fix bug (textured "
        "spec_metallic/spec_pearl/etc. or silent-TypeError 5-arg "
        "crashes):\n  " + "\n  ".join(offenders)
    )


def test_decal_foundation_spec_ignores_mask_seed_sm(engine_module):
    """The factory closure's contract is that mask/seed/sm are
    ignored — the output depends ONLY on the foundation's M/R/CC.
    Calling with wildly-different args must produce identical output.

    This pins the Foundation flat-spec contract at the behavioral
    level: foundations are variance-free.
    """
    fn = engine_module._mk_flat_foundation_decal_spec("f_metallic")

    spec1 = fn((32, 32), np.zeros((32, 32), dtype=np.float32), 0, 0.0)
    spec2 = fn((32, 32), np.ones((32, 32), dtype=np.float32), 99999, 2.5)
    spec3 = fn((32, 32), np.full((32, 32), 0.37, dtype=np.float32), 42, 1.0)

    assert np.array_equal(spec1, spec2), (
        "Foundation decal-spec output changed when seed/sm varied. "
        "The Foundation contract demands variance-free output."
    )
    assert np.array_equal(spec1, spec3), (
        "Foundation decal-spec output changed when mask varied. "
        "The Foundation contract demands variance-free output."
    )
