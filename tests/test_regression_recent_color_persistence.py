from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CANVAS = (ROOT / "paint-booth-3-canvas.js").read_text(encoding="utf-8")
HTML = (ROOT / "paint-booth-v2.html").read_text(encoding="utf-8")


def _function_body(name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", CANVAS)
    assert match, name
    start = match.end()
    depth = 1
    index = start
    while index < len(CANVAS) and depth:
        if CANVAS[index] == "{":
            depth += 1
        elif CANVAS[index] == "}":
            depth -= 1
        index += 1
    assert depth == 0
    return CANVAS[start : index - 1]


def test_pass_126_recent_palette_reads_the_same_key_it_writes():
    push = _function_body("pushRecentColor")
    assert "localStorage.setItem('spb_recentColors'" in push
    assert "_safeLocalStorageJSON('spb_recentColors', [])" in CANVAS
    assert "_safeLocalStorageJSON('spb_recent_colors'" not in CANVAS


def test_pass_126_recent_palette_accepts_only_unique_hex_colors():
    push = _function_body("pushRecentColor")
    assert "/^#[0-9A-F]{6}$/" in push
    assert "return false" in push
    assert ".filter(function(color, index, all)" in CANVAS
    assert "all.indexOf(color) === index" in CANVAS
    assert ".slice(0, 8)" in CANVAS
    assert "Array.isArray(restoredRecentColors)" in CANVAS


def test_pass_126_runtime_is_cache_busted():
    assert "spb93-recent-color-persistence-20260717" in HTML
    assert "spb93-effects-lock-readonly-20260717" in HTML
