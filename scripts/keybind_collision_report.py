# -*- coding: utf-8 -*-
"""Keyboard-shortcut COLLISION DETECTOR (read-only, 2026-06-20).

Scans the booth's keydown handlers and flags any physical key+modifier combo that is
handled by TWO OR MORE separate keydown listeners — the class of bug behind the old
"M = Elliptical Marquee vs zone-mute" conflict. It changes NOTHING; it just writes a
report so a human can confirm whether each overlap is coordinated (one handler bails on
`e.defaultPrevented`) or a real conflict.

Heuristic + advisory: it parses `e.key === 'X'` / `e.key.toLowerCase() === 'X'` / `key === 'X'`
plus the modifier guards on the SAME line (ctrl/meta/shift/alt, required vs !forbidden, and
uppercase-letter ⇒ shift). Two bindings "potentially collide" when they share a key and their
modifier requirements are mutually compatible (could both match one keypress) AND they live in
DIFFERENT keydown listeners (same-listener if/else-if chains can never both fire).

Output: _reworks_2026/keybind_report.txt  +  a console summary.
Run: python scripts/keybind_collision_report.py
"""
import os
import re

ROOT = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
SRV = os.path.join(ROOT, "electron-app", "server")
FILES = ["paint-booth-3-canvas.js", "paint-booth-2-state-zones.js"]
OUT = os.path.join(ROOT, "_reworks_2026", "keybind_report.txt")

KEY_RE = re.compile(r"(?:e\.)?key(?:\.toLowerCase\(\))?\s*===\s*'([^']+)'")
HANDLER_RE = re.compile(r"addEventListener\(\s*['\"]keydown['\"]")


def mod_state(line, *pats):
    """'req' if a positive `e.<mod>` is present, 'no' if only negated `!e.<mod>`, else 'dc'."""
    neg = any(re.search(r"!\s*e\." + p, line) for p in pats)
    pos = any(re.search(r"(?<![!])\be\." + p, line) for p in pats)
    if pos:
        return "req"
    if neg:
        return "no"
    return "dc"


def parse_file(path, fname):
    binds = []
    handler_lines = []
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()
    for i, ln in enumerate(lines, 1):
        if HANDLER_RE.search(ln):
            handler_lines.append(i)
    for i, ln in enumerate(lines, 1):
        keys = KEY_RE.findall(ln)
        if not keys:
            continue
        ctrl = mod_state(ln, "ctrlKey", "metaKey")
        shift = mod_state(ln, "shiftKey")
        alt = mod_state(ln, "altKey")
        uses_lower = ".toLowerCase()" in ln
        # nearest preceding keydown listener = the handler this binding belongs to
        handler = max([h for h in handler_lines if h <= i], default=0)
        for raw in keys:
            k = raw
            sh = shift
            if len(raw) == 1 and raw.isalpha():
                k = raw.lower()
                if raw.isupper() and not uses_lower and sh == "dc":
                    sh = "req"  # uppercase letter literal ⇒ Shift was held
            binds.append({
                "file": fname, "line": i, "key": k,
                "ctrl": ctrl, "shift": sh, "alt": alt,
                "handler": handler, "snippet": ln.strip()[:120],
            })
    return binds


def compatible(a, b):
    """True if both bindings could fire for one physical keypress (no req-vs-no clash)."""
    for dim in ("ctrl", "shift", "alt"):
        x, y = a[dim], b[dim]
        if (x == "req" and y == "no") or (x == "no" and y == "req"):
            return False
    return True


def sig(b):
    return "key '%s' [ctrl:%s shift:%s alt:%s]" % (b["key"], b["ctrl"], b["shift"], b["alt"])


def main():
    all_binds = []
    for f in FILES:
        p = os.path.join(SRV, f)
        if os.path.exists(p):
            all_binds.extend(parse_file(p, f))
    # group by key
    by_key = {}
    for b in all_binds:
        by_key.setdefault(b["key"], []).append(b)

    # The genuine conflict class is UNMODIFIED single letter/digit TOOL shortcuts (the old
    # "M = Elliptical Marquee vs zone-mute" bug). Named keys (Escape/Enter/Arrow*/Delete/Tab/
    # Backspace) are LEGITIMATELY handled in many listeners — each guards on its own state
    # (canvasMode, a modal's open flag, _selectedLayerId, …) so they never truly clash. We
    # exclude those from the collision list (they'd be pure noise) but still scan/count them.
    def is_shortcut_key(k):
        return len(k) == 1 and (k.isalpha() or k.isdigit())

    collisions = []
    for key, group in by_key.items():
        if not is_shortcut_key(key):
            continue
        n = len(group)
        for i in range(n):
            for j in range(i + 1, n):
                a, c = group[i], group[j]
                # different keydown listeners only (same listener = if/else-if, can't both fire)
                if (a["file"], a["handler"]) == (c["file"], c["handler"]):
                    continue
                if compatible(a, c):
                    collisions.append((a, c))

    lines = []
    lines.append("SPB KEYBIND COLLISION REPORT (advisory, read-only)")
    lines.append("=" * 64)
    lines.append("Scanned %d key bindings across %d files." % (len(all_binds), len(FILES)))
    lines.append("A 'collision' = same key, compatible modifiers, in DIFFERENT keydown listeners.")
    lines.append("Many are intentionally coordinated via `if (e.defaultPrevented) return;` —")
    lines.append("verify each before changing anything. This script changes NOTHING.")
    lines.append("")
    if not collisions:
        lines.append("No cross-listener collisions found. ✓")
    else:
        lines.append("POTENTIAL CROSS-LISTENER COLLISIONS: %d" % len(collisions))
        lines.append("")
        for a, c in collisions:
            lines.append("• %s" % sig(a))
            lines.append("    A: %s:%d (listener@%d)  %s" % (a["file"], a["line"], a["handler"], a["snippet"]))
            lines.append("    B: %s:%d (listener@%d)  %s" % (c["file"], c["line"], c["handler"], c["snippet"]))
            lines.append("")

    report = "\n".join(lines)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(report)
    print(report)
    print("\nWROTE", OUT)


if __name__ == "__main__":
    main()
