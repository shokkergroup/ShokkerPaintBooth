"""Regression guardrail: newer spec patterns stay spec-only (no paint path).

The 2026-04 spec-pattern additions (gold_leaf_torn, stippled_dots_fine,
abstract_rothko_field, abstract_futurist_motion, plus the broader
newer cohort) must not grow a paint-side twin. Their signature must
take only (shape, seed, sm, **kwargs) — no paint canvas parameter.
Their output must be a single 2D float32 array in [0, 1].

If someone accidentally adds a paint_* counterpart, or changes the
signature to accept a paint canvas, this test fails.
"""

import inspect
import numpy as np
import pytest

NEWER_SPEC_PATTERNS = [
    "gold_leaf_torn",
    "stippled_dots_fine",
    "abstract_rothko_field",
    "abstract_futurist_motion",
]


@pytest.mark.parametrize("fn_name", NEWER_SPEC_PATTERNS)
def test_signature_is_spec_only(fn_name):
    """Spec functions must not accept a paint canvas parameter."""
    from engine import spec_patterns as sp
    fn = getattr(sp, fn_name, None)
    assert fn is not None, f"spec function {fn_name} not found in engine.spec_patterns"
    sig = inspect.signature(fn)
    params = list(sig.parameters.keys())
    # Must start with (shape, seed, sm, ...)
    assert params[:3] == ["shape", "seed", "sm"], (
        f"{fn_name} signature {params} does not match the spec-pattern "
        f"contract (shape, seed, sm, ...)."
    )
    # No paint/canvas/rgb parameter should appear
    forbidden = {"paint", "canvas", "rgb", "color", "colour"}
    overlap = forbidden.intersection(params)
    assert not overlap, (
        f"{fn_name} has forbidden paint-side parameters {overlap}. "
        f"Spec patterns must be spec-only."
    )


@pytest.mark.parametrize("fn_name", NEWER_SPEC_PATTERNS)
@pytest.mark.parametrize("seed", [1, 42, 99])
def test_output_is_single_channel_normalized(fn_name, seed):
    """Spec functions must return a single 2D float32 array in [0, 1].

    An RGB/RGBA output would mean the function is producing a paint
    canvas, not a spec channel.
    """
    from engine import spec_patterns as sp
    fn = getattr(sp, fn_name)
    shape = (64, 64)
    out = fn(shape, seed, 1.0)
    assert isinstance(out, np.ndarray), f"{fn_name} returned {type(out).__name__}, expected np.ndarray"
    assert out.dtype == np.float32, f"{fn_name} returned dtype={out.dtype}, expected float32"
    assert out.ndim == 2, (
        f"{fn_name} returned ndim={out.ndim} shape={out.shape}. "
        f"Spec patterns must be single-channel 2D; ndim=3 implies paint canvas."
    )
    assert out.shape == shape, f"{fn_name} returned shape {out.shape}, expected {shape}"
    assert float(out.min()) >= 0.0, f"{fn_name} min = {out.min()} (expected >=0)"
    assert float(out.max()) <= 1.0, f"{fn_name} max = {out.max()} (expected <=1)"


@pytest.mark.parametrize("fn_name", NEWER_SPEC_PATTERNS)
def test_no_paint_twin_exists(fn_name):
    """There must not be a `paint_<name>` function co-registered."""
    import importlib
    import pkgutil
    # Scan engine/ for any `paint_<name>` top-level symbol
    import engine
    forbidden_name = f"paint_{fn_name}"
    hits = []
    for _, modname, _ in pkgutil.walk_packages(engine.__path__, prefix="engine."):
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        if hasattr(mod, forbidden_name):
            hits.append(modname)
    assert not hits, (
        f"Found forbidden paint-side twin `{forbidden_name}` in "
        f"{hits}. Newer spec patterns must stay spec-only."
    )
