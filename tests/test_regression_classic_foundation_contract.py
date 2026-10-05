"""Regression guardrail — classic Foundation picker finishes must stay vanilla.

Painter mandate (2026-04-22): the regular non-`f_*` entries shown in the
Foundation picker are not allowed to tint paint or add their own visible spec
texture. They should only change the flat material constants that define how
the painter's chosen color reflects light.
"""

import contextlib
import io

import numpy as np
import pytest


# 2026-09-30: gate the REAL shelf (all 20 FOUNDATION BASES cells) from the single source of
# truth. The old hand list still named ceramic/piano_black (moved to Ceramic & Glass 06-14) and
# chalky_base (moved to the textured EFX shelf 09-03), so it failed on ids that are no longer flat
# by design while the shelf itself went textured unnoticed. Owner 2026-09-30: "The REGULAR
# foundations SHOULD BE PURE."
from engine.base_registry_data import FOUNDATION_BASES_SHELF as CLASSIC_FOUNDATION_IDS

NOISE_KEYS = (
    "noise_M", "noise_R", "noise_CC",
    "noise_scales", "noise_weights",
    "perlin", "perlin_octaves", "perlin_persistence", "perlin_lacunarity",
)


@pytest.fixture(scope="module")
def runtime_engine():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import shokker_engine_v2
    return shokker_engine_v2


@pytest.fixture(scope="module")
def compose_module():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import engine.compose
    return engine.compose


def test_classic_foundation_registry_is_paint_identity_and_flat(runtime_engine):
    offenders = []
    for fid in CLASSIC_FOUNDATION_IDS:
        entry = runtime_engine.BASE_REGISTRY.get(fid)
        if not entry:
            offenders.append(f"{fid}: missing from BASE_REGISTRY")
            continue
        if entry.get("paint_fn") is not runtime_engine.paint_none:
            offenders.append(
                f"{fid}: paint_fn={getattr(entry.get('paint_fn'), '__name__', entry.get('paint_fn'))}"
            )
        # Pure three-channel constants (_spec_foundation_pure_bound) or the legacy two-channel flat.
        if getattr(entry.get("base_spec_fn"), "__name__", "") not in (
                "_spec_foundation_pure_bound", "_spec_foundation_flat"):
            offenders.append(
                f"{fid}: base_spec_fn={getattr(entry.get('base_spec_fn'), '__name__', entry.get('base_spec_fn'))}"
            )
        bad_keys = [key for key in NOISE_KEYS if key in entry]
        if bad_keys:
            offenders.append(f"{fid}: carries noise keys {bad_keys}")

    assert not offenders, (
        "Classic Foundation picker entries drifted away from the vanilla "
        "contract:\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize("fid", CLASSIC_FOUNDATION_IDS)
def test_classic_foundation_compose_finish_stays_flat(compose_module, fid):
    shape = (48, 48)
    mask = np.ones(shape, dtype=np.float32)
    spec = np.asarray(compose_module.compose_finish(fid, "none", shape, mask, 42, 1.0))

    assert spec.shape == (48, 48, 4), f"{fid}: unexpected spec shape {spec.shape}"
    for ch_idx, ch_name in enumerate(("M", "R", "CC")):
        ch = spec[:, :, ch_idx]
        spread = int(ch.max()) - int(ch.min())
        assert spread <= 1, (
            f"{fid}: {ch_name} spread={spread}. Classic Foundation entries "
            f"must be visually flat on the spec map."
        )


@pytest.mark.parametrize("fid", CLASSIC_FOUNDATION_IDS)
@pytest.mark.parametrize("paint_rgb", [
    (0.90, 0.10, 0.10),
    (0.05, 0.05, 0.30),
    (0.80, 0.70, 0.15),
])
def test_classic_foundation_compose_paint_is_identity(compose_module, fid, paint_rgb):
    shape = (32, 32)
    mask = np.ones(shape, dtype=np.float32)
    paint = np.zeros((32, 32, 3), dtype=np.float32)
    paint[:, :, 0] = paint_rgb[0]
    paint[:, :, 1] = paint_rgb[1]
    paint[:, :, 2] = paint_rgb[2]

    out = compose_module.compose_paint_mod(
        fid, "none", paint.copy(), shape, mask, 42, 1.0, 0.0
    )

    assert np.array_equal(out[:, :, :3], paint[:, :, :3]), (
        f"{fid}: compose_paint_mod changed the painter color for {paint_rgb}. "
        "Classic Foundation entries must leave RGB untouched."
    )
