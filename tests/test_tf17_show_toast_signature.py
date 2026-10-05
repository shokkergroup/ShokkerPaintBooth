"""TRUE FIVE-HOUR SHIFT TF17 ratchet: showToast signature truth.

The canonical showToast signature (paint-booth-2-state-zones.js:8798) is:
    showToast(msg, isError, details)

Pre-fix two callers in paint-booth-3-canvas.js used the wrong arity:
    showToast(msg, 4000, true)
which made `4000` the isError flag (truthy) and `true` the details
string — error toasts surfaced a stray "true" subline under the real
message.

Fix: collapsed to (msg, true). This ratchet detects any future
regression that re-introduces a numeric second arg to showToast.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Pattern: showToast( <anything that doesn't open a paren>, <number> ...)
# We forbid any showToast call where the second positional arg is a literal
# integer — that's always the wrong-signature bug shape. Existing 2-arg
# (msg, isError-bool) and 3-arg (msg, isError-bool, details-str) calls pass.
WRONG_SIG = re.compile(r"showToast\s*\([^,()]+,\s*\d+")


CANONICAL_PATHS = (
    REPO,
    REPO / 'electron-app' / 'server',
    REPO / 'electron-app' / 'server' / 'pyserver' / '_internal',
)


def test_TF17_no_show_toast_with_numeric_second_arg():
    offenders = []
    for root in CANONICAL_PATHS:
        for f in sorted(root.glob('paint-booth-*.js')):
            text = f.read_text(encoding='utf-8', errors='ignore')
            for m in WRONG_SIG.finditer(text):
                line_num = text[:m.start()].count('\n') + 1
                # Skip the dead-bundle paint-booth-app.js (TF16 marked).
                if 'paint-booth-app.js' in str(f):
                    continue
                offenders.append((f.relative_to(REPO), line_num, m.group(0)[:80]))
    assert not offenders, (
        "showToast called with numeric second arg — wrong signature is "
        "(msg, isError, details). The number was being treated as isError "
        "and a trailing arg was bleeding into details. Offenders:\n"
        + '\n'.join(f'  {p}:{n}: {snippet}' for p, n, snippet in offenders)
    )
