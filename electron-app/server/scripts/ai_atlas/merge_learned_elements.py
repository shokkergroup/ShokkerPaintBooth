#!/usr/bin/env python
"""Fold the number places the APP LEARNED into a shipped PROPOSALS file.  (WP10, 2026-10-03)

  learned_elements.json (on the machine that learned them)  --merge-->  scripts/ai_atlas/out/learned_elements_atlas.json

Where the learned file lives: %APPDATA%/ShokkerPaintBooth/ai/learned_elements.json (SPB_AI_DIR / SPB_LEARNED_ELEMENTS override it).
Input rows (server_routes/ai_car_routes.py learn_elements):  {key: iRacing car folder, kind: 'numbers', boxes: [[x0,y0,x1,y1] 0-1], source: confirm|teach|ai|viewer, n: times told, at}

Output = PROPOSALS ONLY, never facts: numbers are NOT in the same place on every paint of one car folder (docs/ELEMENT_FINDER.md), so a client may only OFFER these
("are the numbers here?") and must ask first.  Shape:
  {v:1, proposals_only:true, cars:{ <folder key>: { <kind>: [ {box:[x0,y0,x1,y1] (2 dp), sources:{buyer:n, ai:n, viewer:n}, count:total} ] } } }

Rules: dedupe by (car folder, kind, box rounded to 2 dp); source is mapped to buyer (confirm/teach/anything else) / ai / viewer; the per-source count is the MAX seen
(not a sum) so running the merge twice - or on a file that already contains rows merged earlier - changes nothing.  The input is never modified or deleted; the output file
is only rewritten when its content would change.

CLIENT LOADER: none exists yet (js/spb-pro-elements.js only reads /api/ai/learned-elements and localStorage); this file is not consumed by the app until one is built.

Usage:
  python scripts/ai_atlas/merge_learned_elements.py                 # dry run (default): print what would merge
  python scripts/ai_atlas/merge_learned_elements.py --write
  python scripts/ai_atlas/merge_learned_elements.py --from rows.json --out atlas.json --write
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / 'out' / 'learned_elements_atlas.json'
KINDS = ('numbers',)
SRC_MAP = {'ai': 'ai', 'viewer': 'viewer'}


def default_source():
    if os.environ.get('SPB_LEARNED_ELEMENTS'):
        return Path(os.environ['SPB_LEARNED_ELEMENTS'])
    base = os.environ.get('SPB_AI_DIR') or os.path.join(os.environ.get('APPDATA', ''), 'ShokkerPaintBooth', 'ai')
    return Path(base) / 'learned_elements.json'


def norm_key(k):
    return ''.join(c for c in str(k or '').lower() if c.isalnum())[:80]


def clean_box(b):
    try:
        q = [min(1.0, max(0.0, float(v))) for v in list(b)[:4]]
    except Exception:
        return None
    if len(q) != 4 or q[2] <= q[0] or q[3] <= q[1]:
        return None
    return [round(v, 2) for v in q]


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception:
        return default


def merge(atlas, rows):
    """Merge learned rows into atlas['cars'] in place. Returns (new_boxes, bumped_counts, skipped_rows)."""
    new = bumped = skipped = 0
    cars = atlas.setdefault('cars', {})
    for r in rows or []:
        if not isinstance(r, dict):
            skipped += 1
            continue
        key, kind = norm_key(r.get('key')), str(r.get('kind') or '')
        if not key or kind not in KINDS:
            skipped += 1
            continue
        src = SRC_MAP.get(str(r.get('source') or '').lower(), 'buyer')
        try:
            n = max(1, int(r.get('n') or 1))
        except Exception:
            n = 1
        lst = cars.setdefault(key, {}).setdefault(kind, [])
        any_box = False
        for b in r.get('boxes') or []:
            box = clean_box(b)
            if box is None:
                continue
            any_box = True
            hit = next((e for e in lst if e['box'] == box), None)
            if hit is None:
                hit = {'box': box, 'sources': {}, 'count': 0}
                lst.append(hit)
                new += 1
            if n > hit['sources'].get(src, 0):
                if hit['sources'].get(src):
                    bumped += 1
                hit['sources'][src] = n
            hit['count'] = sum(hit['sources'].values())
        if not any_box:
            skipped += 1
    for key in list(cars):                       # drop empty shells, sort for a stable file
        cars[key] = {k: sorted(v, key=lambda e: e['box']) for k, v in cars[key].items() if v}
        if not cars[key]:
            del cars[key]
    atlas['cars'] = dict(sorted(cars.items()))
    return new, bumped, skipped


def run(src, out, write):
    """Returns (exit_code, message)."""
    src, out = Path(src), Path(out)
    if not src.exists():
        return 1, 'no learned_elements.json at %s' % src
    d = load_json(src, {})
    rows = d.get('rows') if isinstance(d, dict) else None
    if not isinstance(rows, list):
        return 1, 'unreadable / no rows in %s' % src
    atlas = load_json(out, {})
    if not isinstance(atlas, dict) or not isinstance(atlas.get('cars'), dict):
        atlas = {}
    atlas['v'] = 1
    atlas['proposals_only'] = True
    before = json.dumps(atlas, indent=1, ensure_ascii=False, sort_keys=True)
    new, bumped, skipped = merge(atlas, rows)
    after = json.dumps(atlas, indent=1, ensure_ascii=False, sort_keys=True)
    ncars = len(atlas['cars'])
    nbox = sum(len(v) for c in atlas['cars'].values() for v in c.values())
    msg = '%s: %d row(s) read, %d new box(es), %d count(s) raised, %d row(s) skipped -> %d car(s), %d proposal box(es) in %s' % (
        'WRITE' if write else 'DRY RUN', len(rows), new, bumped, skipped, ncars, nbox, out.name)
    if before == after and out.exists():
        return 0, msg + ' (no change)'
    if write:
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix('.tmp')
        tmp.write_text(after + '\n', encoding='utf-8', newline='\n')
        os.replace(tmp, out)
    return 0, msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='src', default=None)
    ap.add_argument('--out', default=None)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--dry-run', action='store_true', help='default')
    g.add_argument('--write', action='store_true')
    a = ap.parse_args()
    code, msg = run(a.src or default_source(), a.out or OUT, a.write)
    print(msg)
    return code


if __name__ == '__main__':
    sys.exit(main())
