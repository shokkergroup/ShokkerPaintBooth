"""SPB-93 Pass 65: Clone has one visible opacity control and shortcuts target it."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def test_clone_hides_dead_generic_opacity_and_uses_its_owned_slider():
    options_start = CANVAS.index("const showCloneOpacity")
    options = CANVAS[options_start : CANVAS.index("const fillSampleSource", options_start)]
    assert "const showCloneOpacity = (mode === 'clone')" in options
    assert "&& !showCloneOpacity" in options

    clone_start = CANVAS.index("function paintCloneStroke")
    clone = CANVAS[clone_start : CANVAS.index("function drawCloneSourceIndicator", clone_start)]
    assert "getElementById('cloneOpacity')" in clone
    assert "getElementById('brushOpacity')" not in clone


def test_clone_number_keys_adjust_the_same_opacity_the_engine_reads():
    shortcut_start = CANVAS.index("// Number keys: context-sensitive")
    shortcut = CANVAS[shortcut_start : CANVAS.index("// Ctrl+D = deselect zone mask", shortcut_start)]
    assert "const isClone = canvasMode === 'clone'" in shortcut
    assert "isClone ? 'cloneOpacity'" in shortcut
    assert "isClone ? 'Clone opacity'" in shortcut
    assert 'aria-label="Clone opacity percent"' in HTML


def test_pass_65_runtime_is_cache_busted_and_mirrored():
    assert "spb93-clone-opacity-parity-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
