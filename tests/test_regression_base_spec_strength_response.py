"""Regression guardrail: base spec-strength weakens the material itself."""

from __future__ import annotations

import numpy as np

from engine.compose import compose_finish, compose_finish_stacked


def _full_mask(shape):
    return np.ones(shape, dtype=np.float32)


def test_flat_foundation_base_spec_strength_lerps_roughness_and_clearcoat():
    """Flat Foundation bases should move toward neutral, not stay full-strength."""
    shape = (8, 8)
    mask = _full_mask(shape)

    full = np.asarray(
        compose_finish("matte", None, shape, mask, 7, 1.0, base_spec_strength=1.0, dither=False)
    )
    weak = np.asarray(
        compose_finish("matte", None, shape, mask, 7, 1.0, base_spec_strength=0.1, dither=False)
    )

    assert full[0, 0].tolist() == [0, 200, 160, 255]
    assert weak[0, 0].tolist() == [0, 135, 30, 255], (
        "10% matte should read as a mostly-neutral material response, not full matte."
    )


def test_chrome_base_spec_strength_reduces_material_response_in_stacked_path():
    """Chrome at 10% should no longer read like full chrome."""
    shape = (32, 32)
    mask = _full_mask(shape)

    full = np.asarray(
        compose_finish_stacked("chrome", [], shape, mask, 11, 1.0, base_spec_strength=1.0, dither=False)
    )
    weak = np.asarray(
        compose_finish_stacked("chrome", [], shape, mask, 11, 1.0, base_spec_strength=0.1, dither=False)
    )

    full_m = float(full[:, :, 0].mean())
    weak_m = float(weak[:, :, 0].mean())
    full_r = float(full[:, :, 1].mean())
    weak_r = float(weak[:, :, 1].mean())

    assert weak_m < full_m * 0.5, (
        f"Chrome metallic barely moved with base_spec_strength=0.1 (full={full_m:.1f}, weak={weak_m:.1f})."
    )
    assert weak_r > full_r + 60.0, (
        f"Chrome roughness did not move back toward neutral at low strength "
        f"(full={full_r:.1f}, weak={weak_r:.1f})."
    )
