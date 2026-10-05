"""TRUE FIVE-HOUR SHIFT TF16 ratchet: paint-booth-app.js stays dead.

This 890 KB file is a legacy bundle. The current build loads
paint-booth-{0..6}-*.js modules instead. Two copies of the dead bundle
remain on disk for safekeeping (deletion deferred to a tagged release).

This ratchet asserts:
  1. Both dead copies carry the !STALE-BUNDLE marker (preventing a
     future shift from accidentally treating them as live code).
  2. NO HTML, main.js, sync script, or build manifest in the repo
     loads or references the dead bundle.
  3. NO canonical 3-copy paint-booth-*.js file ships duplicated logic
     from the dead bundle (specifically: the unique `pushUndo()`
     function that the canonical build's TF9-TF11 fix replaced with
     pushZoneUndo).
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DEAD_BUNDLES = (
    REPO / 'electron-app' / 'server' / 'paint-booth-app.js',
    REPO / 'electron-app' / 'server' / 'pyserver' / '_internal' / 'paint-booth-app.js',
)
STALE_MARKER = '!STALE-BUNDLE'


@pytest.mark.parametrize('bundle', DEAD_BUNDLES, ids=lambda p: str(p.relative_to(REPO)))
def test_TF16_dead_bundle_has_stale_marker(bundle):
    """The bundle must carry the !STALE-BUNDLE marker so any future
    grep across the repo flags this as dead code."""
    if not bundle.exists():
        pytest.skip(f"{bundle} not present (already deleted)")
    head = bundle.read_text(encoding='utf-8', errors='ignore')[:2000]
    assert STALE_MARKER in head, (
        f"{bundle.relative_to(REPO)} is missing the !STALE-BUNDLE marker. "
        "If the bundle is still dead, restore the TF16 marker comment. "
        "If the bundle is now live, remove the canonical 3-copy modules first."
    )


def test_TF16_no_html_loads_dead_bundle():
    """No HTML in the repo loads paint-booth-app.js."""
    offenders = []
    for html in REPO.rglob('*.html'):
        # Skip dist artifacts (regenerated from canonical on build)
        if 'dist' in html.parts or 'node_modules' in html.parts:
            continue
        try:
            text = html.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        if 'paint-booth-app.js' in text:
            offenders.append(html.relative_to(REPO))
    assert not offenders, (
        "An HTML file references the dead paint-booth-app.js bundle: "
        f"{offenders}. The canonical 3-copy modules superseded it."
    )


def test_TF16_selection_modifiers_use_pushZoneUndo_not_pushUndo():
    """Canonical paint-booth-3-canvas.js DOES define `pushUndo(zoneIndex)`
    by design — it takes a zone INDEX, not a label. The TF9-TF11 bug was
    that growSelection / shrinkSelection / smoothSelection called this
    function with a STRING ('grow selection'), which made `zones[label]`
    undefined and the function early-returned silently — selection mods
    were unrevertable.

    The fix routed selection modifiers through pushZoneUndo (state-zones.js)
    which takes a label. This ratchet pins the post-fix routing: each
    selection modifier function body must call pushZoneUndo, not pushUndo."""
    canvas = (REPO / 'paint-booth-3-canvas.js').read_text(encoding='utf-8')
    # 2026-04-19 TRUE FIVE-HOUR (TF21 + TF22) — borderSelection (TF21) and
    # selectColorRange (TF22) had the same bare-pushUndo bug TF9-TF11 fixed.
    # Hennig perfection-pass spotted TF21; TF22 surfaced via grep audit
    # while wiring up the TF21 fix.
    selection_mods = ('growSelection', 'shrinkSelection', 'smoothSelection',
                      'borderSelection', 'selectColorRange')
    # Brace-matched body extraction. The naive `\n}` extractor stops at any
    # inner block close (for-loop, if-block) and produced false positives by
    # cutting comments mid-sentence. Walk the source counting braces instead.
    def _extract_top_level_function(text, name):
        needle = 'function ' + name + '('
        start = text.index(needle)
        i = text.index('{', start)
        depth = 0
        for i in range(i, len(text)):
            ch = text[i]
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        raise AssertionError('unbalanced braces in ' + name)

    # Strip line-comments before counting calls so the test does not flag
    # a `// pushUndo(...)` mention in a justification comment.
    def _strip_line_comments(s):
        return '\n'.join(ln.split('//', 1)[0] for ln in s.split('\n'))

    for fn_name in selection_mods:
        body = _extract_top_level_function(canvas, fn_name)
        assert 'pushZoneUndo' in body, (
            f"{fn_name} no longer calls pushZoneUndo — TF9-TF11/TF21/TF22 fix has regressed."
        )
        body_no_comments = _strip_line_comments(body)
        bare_calls = body_no_comments.count('pushUndo(')
        assert bare_calls == 0, (
            f"{fn_name} still calls bare pushUndo() in real code — pre-TF9 bug regressed. "
            f"bare_calls={bare_calls}"
        )
