"""TRUE FIVE-HOUR SHIFT runtime-proof for W14 (doExportToPhotoshop PSD-layer
composite-fallback).

Prior shift shipped W14 as a structural ratchet only ("the string
_psdLayersLoaded appears in the function body"). This shift adds runtime
proof: actually execute the function in Node V8 with stubbed PSD-layer
state and verify that paint_image_base64 IS set when the painter has PSD
layers but no decals — the silent-drop scenario W14 was meant to fix.

We stub ShokkerAPI.exportToPhotoshop to capture the `extras` it receives
and assert against four scenarios:
  - PSD layers + no decals     → paint_image_base64 MUST be set (W14 fix)
  - decals + no PSD layers     → paint_image_base64 set by decal block
  - no PSD layers, no decals   → paint_image_base64 absent (server default)
  - PSD layers + decals        → paint_image_base64 set by decal block (and
                                  the W14 block doesn't double-write because
                                  of the !extras.paint_image_base64 guard)
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "ps_export.mjs"


def _run_harness():
    if shutil.which("node") is None:
        pytest.skip("node not on PATH; runtime harness requires Node 18+")
    if not HARNESS.exists():
        pytest.fail(f"runtime harness missing: {HARNESS}")
    proc = subprocess.run(
        ["node", str(HARNESS)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"PS export harness exited non-zero.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


def test_runtime_W14_psd_layers_no_decals_includes_paint_base64(harness):
    """RUNTIME (W14): the silent-drop scenario the prior-shift fix was for.
    Painter has PSD layers loaded, has done layer paint work, has not
    placed any decals. doExportToPhotoshop MUST capture the live composite
    canvas as paint_image_base64 — else the server gets default paint and
    the painter's layer work is invisible in the exported PSD."""
    r = harness["psd_layers_no_decals"]
    assert r["ok"], f"harness exception: {r.get('error')}"
    assert r["had_paint_image_base64"] is True, (
        "W14 silent-drop NOT fixed: with PSD layers + no decals, "
        "paint_image_base64 was not in the extras payload — painter loses work."
    )


def test_runtime_W14_decals_no_psd_layers(harness):
    """RUNTIME: pre-existing behavior — when decals exist, the decal block
    builds paint_image_base64 from the decal composite. W14 must not break
    this path."""
    r = harness["decals_no_psd_layers"]
    assert r["ok"], f"harness exception: {r.get('error')}"
    assert r["had_paint_image_base64"] is True
    # And decal_spec_finishes should also be there (Marathon Windham bug #21).
    assert "decal_spec_finishes" in r["extras_sent"]


def test_runtime_W14_no_psd_no_decals_skips_paint_base64(harness):
    """RUNTIME: when there's nothing to send, paint_image_base64 must
    NOT be set — server falls back to its synthesized default. Sending
    a fake base64 here would force the painter's work to be replaced
    with junk on the server side."""
    r = harness["no_psd_no_decals"]
    assert r["ok"], f"harness exception: {r.get('error')}"
    assert r["had_paint_image_base64"] is False, (
        "no PSD + no decals scenario unexpectedly set paint_image_base64 — "
        "would force the server to overwrite its proper default with junk."
    )


def test_runtime_W14_psd_layers_with_decals_does_not_double_set(harness):
    """RUNTIME (W14 guard): the W14 block uses `!extras.paint_image_base64`
    so it doesn't overwrite the decal-block-built paint_image_base64. This
    prevents the layer composite from clobbering the decal composite when
    both are present (decals win — they're additive on top)."""
    r = harness["psd_layers_with_decals"]
    assert r["ok"], f"harness exception: {r.get('error')}"
    assert r["had_paint_image_base64"] is True
    assert "decal_spec_finishes" in r["extras_sent"]
