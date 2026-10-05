"""TRUE FIVE-HOUR SHIFT runtime-proof harness for the apply* family.

This is NOT a structural-string-presence test. It actually EXECUTES the
applyFinishFromBrowser / applyCombo / applyChatZones / applyHarmonyColor
function bodies inside Node's V8 with stubbed dependencies, and asserts
that triggerPreviewRender() was called as part of the natural code flow,
that zone state was mutated correctly, and that toasts fired with the
right messages.

It also verifies the prior-shift W1-W4 fixes hold under real execution
— a structural ratchet would tell you the string is in the source; this
test tells you the function path actually fires preview refresh.

If Node is unavailable, the test SKIPs — it does not fail open.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HARNESS = REPO / "tests" / "_runtime_harness" / "apply_paths.mjs"


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
            "Runtime harness exited non-zero.\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Harness did not produce valid JSON: {e}\nstdout:\n{proc.stdout}")


@pytest.fixture(scope="module")
def harness():
    return _run_harness()


# ── runtime proof: applyFinishFromBrowser ─────────────────────────────────────
def test_runtime_apply_finish_from_browser(harness):
    """RUNTIME: extract applyFinishFromBrowser from paint-booth-6-ui-boot.js,
    execute it against stubbed zones + spies in Node V8, verify the natural
    flow fires triggerPreviewRender() and writes the finish onto the zone."""
    r = harness["finish_from_browser"]
    assert r["ok"], f"harness execution failed: {r.get('error')}"
    assert r["triggered_preview_render"] is True, (
        "applyFinishFromBrowser must call triggerPreviewRender() during normal "
        "execution — runtime proof that the prior-shift W1 fix shipped a "
        "live code path, not just a string in the source."
    )
    assert r["preview_call_count"] == 1
    assert r["pushed_undo"] == 1
    assert r["rendered_zones"] == 1
    # Zone state should reflect the applied base + pattern.
    z = r["zone_state_after"][0]
    assert z["base"] == "chrome"
    assert z["pattern"] == "carbon_fiber"
    assert z["finish"] is None
    # Toast should match the applied combo string.
    assert any("chrome + carbon_fiber" in t[0] for t in r["toasts"])


# ── runtime proof: applyCombo ─────────────────────────────────────────────────
def test_runtime_apply_combo(harness):
    """RUNTIME: applyCombo writes finish/base/pattern/intensity/scale and
    fires preview refresh + undo + toast."""
    r = harness["combo"]
    assert r["ok"], f"harness execution failed: {r.get('error')}"
    assert r["triggered_preview_render"] is True, (
        "applyCombo must call triggerPreviewRender() during normal execution."
    )
    assert r["preview_call_count"] == 1
    assert r["pushed_undo"] == 1
    z = r["zone_state_after"][0]
    assert z["base"] == "metallic"
    assert z["pattern"] == "carbon_fiber"
    assert z["intensity"] == "80"
    assert z["scale"] == 1.5


# ── runtime proof: applyChatZones ─────────────────────────────────────────────
def test_runtime_apply_chat_zones(harness):
    """RUNTIME: applyChatZones with a single chat-config that names a new
    zone and assigns a monolithic finish must create the zone, write the
    finish, fire preview refresh + undo."""
    r = harness["chat_zones"]
    assert r["ok"], f"harness execution failed: {r.get('error')}"
    assert r["triggered_preview_render"] is True
    assert r["pushed_undo"] == 1
    assert len(r["zone_state_after"]) == 2  # original + newly added
    new_zone = r["zone_state_after"][1]
    assert new_zone["name"] == "ChatHood"
    assert new_zone["finish"] == "piano_black"


# ── runtime proof: applyHarmonyColor ──────────────────────────────────────────
def test_runtime_apply_harmony_color(harness):
    """RUNTIME: applyHarmonyColor with one filled zone + one empty zone
    must auto-target the empty zone, parse the hex into color_rgb, set
    pickerColor + colorMode, fire preview refresh + undo + a toast that
    references the target zone number."""
    r = harness["harmony"]
    assert r["ok"], f"harness execution failed: {r.get('error')}"
    assert r["triggered_preview_render"] is True
    assert r["pushed_undo"] == 1
    target = r["zone_state_after"][1]
    assert target["pickerColor"] == "#ff8800"
    assert target["color"]["color_rgb"] == [255, 136, 0]
    assert target["colorMode"] == "picker"
    # Toast must reference Zone 2 (1-indexed) and the hex.
    assert any("Zone 2" in t[0] and "#ff8800" in t[0] for t in r["toasts"])
