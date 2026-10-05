"""TRUE FIVE-HOUR SHIFT TF15 ratchet: no UTF-8→cp1252→UTF-8 mojibake bytes
in any canonical paint-booth-*.js file.

The mojibake byte sequence b'\\xc3\\xa2\\xe2\\x82\\xac' is the 5-byte
representation of the chars 'â€' that you get when UTF-8-encoded text
is incorrectly decoded as cp1252 then re-encoded as UTF-8.

Pre-fix: 51 mojibake instances across the canonical 3-copy build (1 in
paint-booth-2-state-zones.js, 16 in paint-booth-6-ui-boot.js, ×3 copies
including the two mirrors). Painters saw garbled chars in toasts and
button tooltips depending on the browser's font choice.

Fix: tests/_runtime_harness/fix_mojibake.py replaces three known
3-byte→1-char corruption patterns:
  em-dash (—): b'\\xc3\\xa2\\xe2\\x82\\xac\\xe2\\x80\\x9d'
  en-dash (–): b'\\xc3\\xa2\\xe2\\x82\\xac\\xe2\\x80\\x9c'
  ellipsis (…): b'\\xc3\\xa2\\xe2\\x82\\xac\\xc2\\xa6'

This ratchet runs on canonical 3-copy files only. Built/packaged
electron-app/dist artifacts are excluded — they get regenerated from
canonical via `npm run build`.
"""

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# TF15 needles + TF20 (lightning bolt — different mojibake byte sequence).
# Each tuple: (corrupt bytes, friendly name).
NEEDLES = (
    (b'\xc3\xa2\xe2\x82\xac', 'em/en/ellipsis cluster'),  # TF15 — `â€` prefix
    (b'\xc3\xa2\xc5\xa1\xc2\xa1', 'lightning bolt cluster'),  # TF20 — `âš¡` literal
)

CANONICAL_PATHS = (
    REPO,
    REPO / 'electron-app' / 'server',
    REPO / 'electron-app' / 'server' / 'pyserver' / '_internal',
)


@pytest.fixture(scope='module')
def files():
    return [
        p for root in CANONICAL_PATHS
        for p in sorted(root.glob('paint-booth-*.js'))
    ]


def test_TF15_TF20_no_mojibake_in_canonical_paint_booth_files(files):
    offenders = []
    for p in files:
        raw = p.read_bytes()
        for needle, name in NEEDLES:
            count = raw.count(needle)
            if count:
                offenders.append((p.relative_to(REPO), count, name))
    assert not offenders, (
        "Mojibake regression detected — UTF-8 text was decoded as cp1252 "
        "and re-encoded as UTF-8. Run "
        "`python tests/_runtime_harness/fix_mojibake.py` to repair.\n"
        f"Offenders: {offenders}"
    )
