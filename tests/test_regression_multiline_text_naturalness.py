"""SPB-93 Pass 71: multiline Text keeps layout and effects consistent."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8", errors="replace")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8", errors="replace")


def _text_tool() -> str:
    start = CANVAS.index("function onTextToolClick")
    return CANVAS[start : CANVAS.index("// SHAPE TOOL", start)]


def test_missing_canvas_cannot_leave_text_input_latched_active():
    text = _text_tool()
    assert text.index("if (!pc) return false") < text.index("_textInputActive = true")
    assert "if (_textInputActive) return false" in text
    assert "return true" in text


def test_blank_lines_survive_commit_and_every_effect_uses_line_offsets():
    text = _text_tool()
    assert "const lines = text.split('\\n')" in text
    assert ".filter(l => l.length > 0)" not in text
    assert "lines.some(line => line.length > 0)" in text
    assert text.count("textY + li * lineHeightPx") >= 4

    neon_start = text.index("textEffect === 'neon'")
    emboss_start = text.index("textEffect === 'emboss'")
    drawing_start = text.index("// Draw stroke (multiline)")
    neon = text[neon_start:emboss_start]
    emboss = text[emboss_start:drawing_start]
    assert "for (let li = 0; li < lines.length; li++)" in neon
    assert emboss.count("for (let li = 0; li < lines.length; li++)") == 2
    assert "_drawTextWithSpacing(rctx, text," not in neon + emboss


def test_pass_71_runtime_is_cache_busted_and_mirrored():
    assert "spb93-multiline-text-naturalness-20260717" in HTML
    server = ROOT / "electron-app" / "server"
    for relative in ("paint-booth-v2.html", "paint-booth-3-canvas.js"):
        assert (ROOT / relative).read_bytes() == (server / relative).read_bytes()
