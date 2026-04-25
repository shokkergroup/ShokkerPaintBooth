"""HEENAN HARDMODE-CULL — Hennig perfection-gate quality cull.

Hennig audit (2026-04-20 ~01:00) called out 4 cx_*/ms_* finishes whose
visual identity does not justify front-shelf placement (engine kernels
shared with stronger hero finishes; only color RGB differs):

  cx_midnight_chrome  — clone of cx_chrome_void (seed_off 9018 vs 9010)
  cx_white_lightning  — warmer re-skin of cx_chrome_void (seed_off 9019)
  cx_glacier_fire     — same engine template as cx_electric_storm
  ms_ghost_vapor      — same multi_scale_noise kernel as ms_void_walker

These join HARDMODE-1's earlier 3 cx_* demotions (cx_rose_chrome,
cx_blood_mercury, cx_toxic_chrome). Default Specials picker now surfaces
4 distinct chrome flips: cx_chrome_void, cx_neon_abyss, cx_obsidian_gold,
cx_electric_storm.

Conversely, two finishes were buried while their distinctness scores
exceed several current heroes:

  shokk_spectrum    — diffraction-grating procedural; deserves hero
  hypershift_spectral — 3-layer spectral; distinctness=91, hidden behind
                        advanced gate

Promote both to hero:true, sortPriority:95.

Idempotent.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

METADATA_PATHS = [
    REPO / "paint-booth-0-finish-metadata.js",
    REPO / "electron-app" / "server" / "paint-booth-0-finish-metadata.js",
    REPO / "electron-app" / "server" / "pyserver" / "_internal" / "paint-booth-0-finish-metadata.js",
]

DEMOTE_TO_ADVANCED = [
    "cx_midnight_chrome",
    "cx_white_lightning",
    "cx_glacier_fire",
    "ms_ghost_vapor",
]

PROMOTE_TO_HERO = [
    ("shokk_spectrum",     {"hero": True, "featured": True, "advanced": False, "sortPriority": 95}),
    ("hypershift_spectral", {"hero": True, "featured": True, "advanced": False, "sortPriority": 95}),
]


def _replace_value(body, key, new_value):
    if isinstance(new_value, bool):
        v = "true" if new_value else "false"
    elif isinstance(new_value, str):
        v = json.dumps(new_value)
    else:
        v = str(new_value)
    pat = re.compile(r'"' + re.escape(key) + r'":\s*("[^"]*"|true|false|-?\d+)')
    if pat.search(body):
        replacement = f'"{key}": {v}'
        return pat.sub(lambda _m, _r=replacement: _r, body), True
    body = body.rstrip()
    if body.endswith(","):
        body = body[:-1]
    body += f',\n    "{key}": {v}\n  '
    return body, True


def _block_re(entry_id):
    return re.compile(
        r'(  "' + re.escape(entry_id) + r'":\s*\{)([^}]*)(\})',
        re.MULTILINE | re.DOTALL,
    )


def _patch_entry(text, entry_id, updates):
    rx = _block_re(entry_id)
    m = rx.search(text)
    if not m:
        return text, "missing"
    head, body, tail = m.group(1), m.group(2), m.group(3)
    new_body = body
    changed = False
    for k, v in updates.items():
        new_body2, _ = _replace_value(new_body, k, v)
        if new_body2 != new_body:
            new_body = new_body2
            changed = True
    if not changed:
        return text, "ok"
    return text[:m.start()] + head + new_body + tail + text[m.end():], "patched"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    grand_demoted = 0
    grand_promoted = 0
    grand_missing = 0
    for path in METADATA_PATHS:
        if not path.exists():
            print(f"  SKIP missing: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        demoted = []
        promoted = []
        missing = []
        for fid in DEMOTE_TO_ADVANCED:
            text, status = _patch_entry(text, fid, {"advanced": True})
            if status == "patched":
                demoted.append(fid)
            elif status == "missing":
                missing.append(fid)
        for fid, updates in PROMOTE_TO_HERO:
            text, status = _patch_entry(text, fid, updates)
            if status == "patched":
                promoted.append(fid)
            elif status == "missing":
                missing.append(fid)
        rel = path.relative_to(REPO)
        print(f"  {rel}:")
        print(f"    demoted to advanced: {len(demoted)} {demoted}")
        print(f"    promoted to hero:    {len(promoted)} {promoted}")
        if missing:
            print(f"    MISSING entries:     {missing}")
        grand_demoted += len(demoted)
        grand_promoted += len(promoted)
        grand_missing += len(missing)
        if not args.dry and (demoted or promoted):
            path.write_text(text, encoding="utf-8")

    print(f"\n[{'DRY-RUN' if args.dry else 'APPLIED'}] demoted: {grand_demoted}, promoted: {grand_promoted}, missing: {grand_missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
