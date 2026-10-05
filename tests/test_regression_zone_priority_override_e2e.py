"""Scoped zone refinement must be able to beat earlier zones locally.

Painter-visible failure mode from 2026-04-23 real-world testing:

* A lower-priority zone was restricted to the ``Numbers`` layer + picked yellow.
* The painter brushed/flooded only a tiny part of that selector.
* The source overlay showed the refinement, but Live Preview did not change,
  because higher-priority zones still owned those pixels at render time.

This guard proves the renderer now treats scoped painted includes as a local
ownership override instead of letting earlier zones silently erase them.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture(scope="module")
def engine_module():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import shokker_engine_v2 as eng
    return eng


def _write_flat_yellow_paint(path: Path, size: int = 16) -> None:
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    rgba[:, :, 0] = 255
    rgba[:, :, 1] = 255
    rgba[:, :, 3] = 255
    Image.fromarray(rgba, "RGBA").save(path)


def _solid_foundation_zone(name: str, rgb: tuple[float, float, float], *, spatial_mask=None, priority_override=False):
    zone = {
        "name": name,
        "base": "f_metallic",
        "pattern": "none",
        "color": {"color_rgb": [255, 255, 0], "tolerance": 5},
        "base_color_mode": "solid",
        "base_color": list(rgb),
        "base_color_strength": 1.0,
    }
    if spatial_mask is not None:
        zone["spatial_mask"] = spatial_mask
    if priority_override:
        zone["priority_override"] = True
    return zone


def _run_preview(engine_module, out_dir: Path, *, priority_override: bool) -> np.ndarray:
    out_dir.mkdir(parents=True, exist_ok=True)
    paint_path = out_dir / "paint.png"
    _write_flat_yellow_paint(paint_path)

    spatial = np.zeros((16, 16), dtype=np.uint8)
    spatial[4:8, 4:8] = 1

    zones = [
        _solid_foundation_zone("Top", (1.0, 0.0, 0.0)),
        _solid_foundation_zone(
            "Scoped",
            (0.0, 1.0, 0.0),
            spatial_mask=spatial,
            priority_override=priority_override,
        ),
    ]

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        paint_rgb, _combined_spec = engine_module.build_multi_zone(
            str(paint_path),
            str(out_dir),
            zones,
            preview_mode=True,
        )
    return np.asarray(paint_rgb)


def test_priority_override_lets_lower_scoped_zone_win_locally(engine_module, tmp_path):
    no_override = _run_preview(engine_module, tmp_path / "no_override", priority_override=False)
    with_override = _run_preview(engine_module, tmp_path / "with_override", priority_override=True)

    outside_no = no_override[0, 0].astype(int)
    inside_no = no_override[5, 5].astype(int)
    outside_yes = with_override[0, 0].astype(int)
    inside_yes = with_override[5, 5].astype(int)

    # Control: without the override, the lower-priority scoped zone loses and the
    # painted include region looks the same as the rest of the higher-priority zone.
    assert np.array_equal(inside_no, outside_no), (
        "Control failed: without priority_override the scoped lower-priority zone "
        "should still lose ownership to the earlier zone."
    )

    # Regression guard: once priority_override is armed, the painted include
    # region must visibly flip to the lower-priority zone's solid green base,
    # while pixels outside the include stay red from the earlier zone.
    assert inside_yes[1] > inside_yes[0] + 60, (
        f"Scoped override center pixel stayed red-dominant instead of green-dominant: {inside_yes.tolist()}"
    )
    assert outside_yes[0] > outside_yes[1] + 60, (
        f"Outside the scoped override the earlier red zone should still win: {outside_yes.tolist()}"
    )
    assert not np.array_equal(inside_yes, outside_yes), (
        "priority_override did not create a local ownership split. The painter "
        "would still see the source overlay change without a corresponding "
        "Live Preview change."
    )
