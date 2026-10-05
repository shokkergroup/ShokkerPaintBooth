#!/usr/bin/env python
"""Fold the car layouts the APP LEARNED (taught by a buyer, confirmed from a look-alike, or measured in the iRacing 3D viewer) into the shipped car library.

  learned_cars.json (on the machine that taught them)  --merge-->  scripts/ai_atlas/car_atlas_learned.json  --build_car_atlas.py-->  js/spb-car-atlas-data.js

Where the learned file lives: %APPDATA%/ShokkerPaintBooth/ai/learned_cars.json (SPB_AI_DIR / SPB_LEARNED_CARS override it).
Rules: entries merge by iRacing folder key or by layout-fingerprint similarity >= 0.9; a part measured in the viewer or taught by hand beats one that was only
adopted from a look-alike; a newer measurement beats an older one of the same quality.  Nothing is ever deleted from the committed file.

Usage:
  python scripts/ai_atlas/merge_learned_cars.py                      # merge the default learned_cars.json, then rebuild the atlas
  python scripts/ai_atlas/merge_learned_cars.py --from path.json --no-build
  python scripts/ai_atlas/merge_learned_cars.py --report             # list what is in the committed learned file
SPB-AI 2026-10-02."""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / 'car_atlas_learned.json'
QUALITY = {'owner': 4, 'viewer': 3, 'taught': 2, 'adopted-near': 1, 'claude-suggested': 1}      # owner = labelled by the owner in _easy_claude_work/labeler (apply_owner_labels.py)


def default_source():
    for env in ('SPB_LEARNED_CARS',):
        if os.environ.get(env):
            return Path(os.environ[env])
    base = os.environ.get('SPB_AI_DIR') or os.path.join(os.environ.get('APPDATA', ''), 'ShokkerPaintBooth', 'ai')
    return Path(base) / 'learned_cars.json'


def sim(a, b):
    pop = [bin(i).count('1') for i in range(16)]
    i = u = 0
    for x, y in zip(a, b):
        x, y = int(x, 16), int(y, 16)
        i += pop[x & y]
        u += pop[x | y]
    return i / u if u else 0.0


def norm_folder(f):
    segs = [s for s in re.split(r'[\\/]', str(f or '')) if s and not re.search(r'\.[a-z0-9]{2,4}$', s, re.I)]
    return re.sub(r'[^a-z0-9]', '', (segs[-1] if segs else '').lower())


def quality(sources):
    q = 0
    for s in sources or []:
        q = max(q, QUALITY.get(str(s).split(':')[0], 1))
    return q


def load(p):
    if not Path(p).exists():
        return {'v': 1, 'cars': []}
    d = json.loads(Path(p).read_text(encoding='utf-8'))
    d.setdefault('cars', [])
    return d


def merge(dst, src):
    """Merge src car dicts into dst (list). Returns (added, updated)."""
    added = updated = 0
    for e in src:
        if not e.get('parts'):
            continue
        hit = None
        ef = [norm_folder(x) for x in e.get('folders') or []]
        for c in dst:
            cf = [norm_folder(x) for x in c.get('folders') or []]
            if any(f and f in cf for f in ef) or any(sim(s1, s2) >= 0.9 for s1 in (e.get('sigs') or []) for s2 in (c.get('sigs') or [])):
                hit = c
                break
        if hit is None:
            dst.append(json.loads(json.dumps(e)))
            added += 1
            continue
        qn, qo = quality(e.get('sources')), quality(hit.get('sources'))
        newer = str(e.get('updated') or '') >= str(hit.get('updated') or '')
        for nm, pv in e['parts'].items():
            if nm not in hit['parts'] or qn > qo or (qn == qo and newer):
                hit['parts'][nm] = pv
        for f in e.get('folders') or []:
            if norm_folder(f) not in [norm_folder(x) for x in hit.setdefault('folders', [])]:
                hit['folders'].append(f)
        for s in e.get('sigs') or []:
            if s not in hit.setdefault('sigs', []):
                hit['sigs'] = (hit['sigs'] + [s])[-4:]
        hit['sources'] = sorted(set((hit.get('sources') or []) + (e.get('sources') or [])))
        hit['n'] = int(hit.get('n') or 0) + int(e.get('n') or 0)
        hit['updated'] = max(str(hit.get('updated') or ''), str(e.get('updated') or ''))
        updated += 1
    return added, updated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--from', dest='src', default=None)
    ap.add_argument('--no-build', action='store_true')
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--min-quality', type=int, default=2, help='1 = also ship layouts only CONFIRMED from a look-alike (adopted-near); default 2 = taught by hand or measured in the viewer')
    a = ap.parse_args()
    cur = load(OUT)
    if a.report:
        for c in cur['cars']:
            print('%-34s parts=%-2d folders=%s sources=%s n=%s' % (c['id'], len(c['parts']), c.get('folders'), c.get('sources'), c.get('n')))
        print(len(cur['cars']), 'learned car(s) in', OUT)
        return 0
    src = Path(a.src) if a.src else default_source()
    if not src.exists():
        print('no learned_cars.json at', src)
        return 1
    inc = load(src)
    skipped = [c['id'] for c in inc['cars'] if quality(c.get('sources')) < a.min_quality]
    inc['cars'] = [c for c in inc['cars'] if quality(c.get('sources')) >= a.min_quality]
    if skipped:
        print('kept local (only adopted from a look-alike, not measured): %s  (--min-quality 1 ships them)' % ', '.join(skipped))
    added, updated = merge(cur['cars'], inc['cars'])
    cur['v'] = 1
    OUT.write_text(json.dumps(cur, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    print('merged %s: %d new car(s), %d updated -> %s (%d total)' % (src, added, updated, OUT.name, len(cur['cars'])))
    if not a.no_build:
        return subprocess.call([sys.executable, str(HERE / 'build_car_atlas.py')])
    return 0


if __name__ == '__main__':
    sys.exit(main())
