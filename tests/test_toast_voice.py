"""HEENAN Sting + Hennig — toast voice consistency ratchets.

The board meeting flagged toast voice as one of the painter trust-killers:
"Some are friendly, some are dev-speak, some are just function names like
'TGA decode error.' A premium tool talks like a human."

This ratchet is mechanical, not subjective. It enforces:
1. No `--` (double hyphen) inside showToast() string literals — premium
   typography uses real em-dashes (\u2014). HS5 fixed 20 instances; this
   pins the result.
2. No bare exception class names as toast text. (e.g., "TypeError" or
   "ReferenceError" passed straight to showToast.)
3. No empty / whitespace-only toast strings.
4. (Future): consistent sentence-end punctuation across toast voice.

Add new patterns here as the voice standard tightens.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

CANONICAL_PATHS = (
    REPO,
    REPO / "electron-app" / "server",
    REPO / "electron-app" / "server" / "pyserver" / "_internal",
)

# Match the FIRST string literal inside a showToast(...) call.
TOAST_STR_PAT = re.compile(
    r"showToast\s*\(\s*([\"'`])((?:[^\"'`\\]|\\.)*?)\1",
    re.DOTALL,
)


def _all_canonical_js():
    files = []
    for root in CANONICAL_PATHS:
        files.extend(sorted(root.glob("paint-booth-*.js")))
    # Skip the dead bundle — TF16 marked it !STALE-BUNDLE.
    return [p for p in files if "paint-booth-app.js" not in p.name]


def _harvest_toast_strings():
    by_file = {}
    for js in _all_canonical_js():
        text = js.read_text(encoding="utf-8", errors="ignore")
        msgs = [m.group(2) for m in TOAST_STR_PAT.finditer(text)]
        if msgs:
            by_file[js.relative_to(REPO)] = msgs
    return by_file


def test_toast_voice_no_double_hyphen():
    """HS5: showToast string literals must not contain `--` — use em-dash
    (\u2014) instead. The canonical build uses real typography."""
    offenders = []
    for f, msgs in _harvest_toast_strings().items():
        for m in msgs:
            if "--" in m:
                offenders.append((f, m[:80]))
    assert not offenders, (
        "Double-hyphen `--` found inside showToast() strings. Use em-dash "
        "(\u2014) instead. Run "
        "`python tests/_runtime_harness/fix_toast_typography.py` to repair.\n"
        + "\n".join(f"  {p}: {s!r}" for p, s in offenders[:20])
        + (f"\n  ... and {len(offenders) - 20} more" if len(offenders) > 20 else "")
    )


def test_toast_voice_no_bare_exception_class_names():
    """Sting: a premium tool does not put `TypeError` / `ReferenceError` /
    `SyntaxError` directly in painter-visible toast text. Use a friendly
    explanation + concatenate the .message if you need the technical detail."""
    BARE_TYPES = ("TypeError", "ReferenceError", "SyntaxError",
                  "RangeError", "URIError")
    offenders = []
    for f, msgs in _harvest_toast_strings().items():
        for m in msgs:
            for et in BARE_TYPES:
                # Only flag if the type name appears as a bare word, not
                # inside a longer phrase like "TypeScript" or "TypeFace".
                if re.search(rf"\b{et}\b(?!\w)", m):
                    offenders.append((f, m[:120], et))
    assert not offenders, (
        "Bare JS exception class name found in showToast() text. Wrap with "
        "a painter-friendly sentence.\n"
        + "\n".join(f"  {p}: {s!r} (matched {et})" for p, s, et in offenders[:10])
    )


def test_toast_voice_no_empty_strings():
    """Empty / whitespace-only toast strings are bugs — the painter sees a
    blink with no message. Either remove the call or pass real text."""
    offenders = []
    for f, msgs in _harvest_toast_strings().items():
        for m in msgs:
            if not m.strip():
                offenders.append((f, repr(m)))
    assert not offenders, (
        "Empty toast string found. Remove the call or pass real text.\n"
        + "\n".join(f"  {p}: {s}" for p, s in offenders)
    )


def test_toast_voice_inventory_baseline():
    """Sanity ratchet: the toast surface should not regress in size below
    a baseline. If we drop below, we've lost messages somewhere
    (refactor regression). If we balloon, we've added noise without
    discipline. Trust-but-verify the count.

    Current baseline as of 2026-04-19 (HS5 typography fix landed): the
    canonical 3-copy build holds ~445 showToast calls — 3x because of
    the mirror copies. Use a generous range so this is a smoke test, not
    a brittle exact-match.
    """
    by_file = _harvest_toast_strings()
    total = sum(len(msgs) for msgs in by_file.values())
    # Generous bounds; tightening over time is fine.
    assert 400 <= total <= 2500, (
        f"Toast call count drift detected: total={total} "
        f"(expected 400-2500 for canonical 3-copy build). "
        f"Per-file: {[(str(p), len(m)) for p, m in by_file.items()]}"
    )
