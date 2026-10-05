from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def test_show_toast_supports_typed_severity_strings():
    src = (REPO / 'paint-booth-2-state-zones.js').read_text(encoding='utf-8', errors='ignore')
    start = src.index("function showToast(msg, isError, details) {")
    end = src.index("\n}\n\n// ===== RENDER NOTIFICATION SYSTEM =====", start)
    body = src[start:end]
    assert "typeof isError === 'string'" in body
    assert "_toastSeverity === 'warn' ? 'warning' : _toastSeverity" in body
    assert "_toastExplicitInfo ? ' info' : ''" in body


def test_toast_css_has_info_style():
    css = (REPO / 'paint-booth-v2.css').read_text(encoding='utf-8', errors='ignore')
    assert '.toast.info {' in css
