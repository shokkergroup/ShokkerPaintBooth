"""HEENAN Raven — catalog cull mechanism.

Mass-tag finish-metadata entries with `advanced: true` based on score
threshold. The browser already gates `advanced=true` entries behind the
"Advanced" tab (paint-booth-2-state-zones.js:8120) — flagging weak
finishes pushes them off the front shelf without removing them.

Usage:
    python tests/_runtime_harness/catalog_cull.py --threshold 70 --apply
    python tests/_runtime_harness/catalog_cull.py --threshold 75    # dry-run

Conservative defaults:
- Threshold 70: ~61 entries flagged. Safe initial cull.
- Threshold 75: ~300 entries flagged. Moderate.
- Threshold 78: ~700 entries flagged. The board meeting target — should
  only be applied alongside curated "Start Here" shelf to avoid leaving
  painters with too few visible options.

The script preserves existing `advanced: true` flags (idempotent).
3-copy sync handled here so the canonical and mirror metadata files
stay aligned.
"""

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

CANONICAL_PATHS = [
    REPO / "paint-booth-0-finish-metadata.js",
    REPO / "electron-app" / "server" / "paint-booth-0-finish-metadata.js",
    REPO / "electron-app" / "server" / "pyserver" / "_internal" / "paint-booth-0-finish-metadata.js",
]


def _flip_advanced_for_entries(text, ids_to_flag):
    """Rewrite `\"advanced\": false` → `\"advanced\": true` for entries whose
    id is in `ids_to_flag`. Operates on the per-entry block so we don't
    accidentally flip an unrelated `advanced: false` outside the entry."""
    out = []
    pos = 0
    flipped = 0
    # Match each entry: "id": { ... },
    pat = re.compile(r'"([a-zA-Z0-9_]+)":\s*\{', re.DOTALL)
    for m in pat.finditer(text):
        out.append(text[pos:m.start()])
        fid = m.group(1)
        if fid not in ids_to_flag:
            out.append(text[m.start():m.end()])
            pos = m.end()
            continue
        # Find matching `}` for this entry.
        depth = 0
        i = m.end() - 1   # at the `{`
        end = i
        while end < len(text):
            ch = text[end]
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end += 1
                    break
            end += 1
        block = text[m.start():end]
        # Flip `"advanced": false` → `"advanced": true` exactly once.
        new_block, n = re.subn(r'("advanced":\s*)false', r'\1true', block, count=1)
        if n > 0:
            flipped += 1
        out.append(new_block)
        pos = end
    out.append(text[pos:])
    return ''.join(out), flipped


def _harvest_low_score_ids(text, threshold):
    pat = re.compile(
        r'"([a-zA-Z0-9_]+)":\s*\{[^}]*"advanced":\s*(true|false)[^}]*"score":\s*(\d+)',
        re.DOTALL,
    )
    targets = set()
    for m in pat.finditer(text):
        fid, adv, score = m.group(1), m.group(2), int(m.group(3))
        if score < threshold and adv == 'false':
            targets.add(fid)
    return targets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--threshold', type=int, default=70,
                    help='score below this is flagged advanced=true (default 70)')
    ap.add_argument('--apply', action='store_true',
                    help='write changes; without this flag, dry-run only')
    args = ap.parse_args()

    canonical = CANONICAL_PATHS[0]
    text = canonical.read_text(encoding='utf-8')
    targets = _harvest_low_score_ids(text, args.threshold)

    print(f'Target ids (score<{args.threshold}, currently not advanced): {len(targets)}')
    if not targets:
        print('Nothing to cull. Exiting.')
        return 0

    if not args.apply:
        sample = sorted(targets)[:20]
        print(f'\nDry-run sample (first 20):\n  ' + '\n  '.join(sample))
        print(f'\nRe-run with --apply to flag these as advanced=true.')
        return 0

    # Apply to all 3 mirror copies for sync hygiene.
    for path in CANONICAL_PATHS:
        if not path.exists():
            print(f'  SKIP {path.relative_to(REPO)} (missing)')
            continue
        original = path.read_text(encoding='utf-8')
        new_text, flipped = _flip_advanced_for_entries(original, targets)
        if flipped == 0:
            print(f'  {path.relative_to(REPO)}: no changes (already flagged)')
            continue
        path.write_text(new_text, encoding='utf-8')
        print(f'  {path.relative_to(REPO)}: flipped {flipped} entries')

    print(f'\nCull complete. {len(targets)} ids now advanced=true (front shelf reduced).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
