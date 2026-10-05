#!/usr/bin/env python
"""Turn the owner's labels (_easy_claude_work/labeler/index.html -> Export -> spb_car_labels.json) into shipped car-library entries (source 'owner' = the best quality there is).

  spb_car_labels.json --apply--> scripts/ai_atlas/car_atlas_learned.json --build_car_atlas.py--> js/spb-car-atlas-data.js (bump its ?v= token, sync root -> electron-app/server)

Each labelled car folder becomes one learned entry: folders = [the iRacing folder], sigs = [the layout fingerprint measured from its real paints], parts = one box per part (union of its panels).
Entries merge with what is there (a part labelled by the owner always wins).  Usage:
  python scripts/ai_atlas/apply_owner_labels.py spb_car_labels.json [--finished-only] [--dry] [--no-build]
SPB-AI 2026-10-02."""
import argparse, json, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import merge_learned_cars as M          # QUALITY / merge()


def key_of(name):
    return re.sub(r'[^a-z0-9]+', '', name.lower())


def entries(labels, finished_only, include_suggested=False):
    out = []
    for folder, f in (labels.get('folders') or {}).items():
        if finished_only and not f.get('finished'):
            continue
        parts = {}
        for name, p in (f.get('parts') or {}).items():
            if p.get('suggested') and not include_suggested:
                continue            # 'Suggest: the usual stock-car layout' guesses the owner did not confirm
            box = p.get('box')
            if not box or len(box) != 4:
                continue
            e = {'box': [round(float(v), 4) for v in box]}
            if p.get('front') in ('left', 'right', 'top', 'bottom'):
                e['front'] = p['front']
            parts[re.sub(r'\s+', ' ', name.strip().lower())] = e
        if not parts:
            continue
        out.append({'id': 'owner-' + key_of(folder), 'name': folder, 'folders': [folder], 'sigs': [f['sig']] if f.get('sig') else [], 'parts': parts, 'learned': True,
                    'sources': ['owner'], 'n': 1, 'updated': time.strftime('%Y-%m-%dT%H:%M:%S')})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('labels')
    ap.add_argument('--finished-only', action='store_true')
    ap.add_argument('--include-suggested', action='store_true')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--no-build', action='store_true')
    a = ap.parse_args()
    labels = json.loads(Path(a.labels).read_text(encoding='utf-8'))
    new = entries(labels, a.finished_only, a.include_suggested)
    print('%d car(s) with labels: %s' % (len(new), ', '.join('%s (%d parts)' % (e['name'], len(e['parts'])) for e in new)))
    if a.dry or not new:
        return 0
    cur = M.load(M.OUT)
    added, updated = M.merge(cur['cars'], new)
    cur['v'] = 1
    M.OUT.write_text(json.dumps(cur, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    print('merged into %s: %d new, %d updated (%d total)' % (M.OUT.name, added, updated, len(cur['cars'])))
    if not a.no_build:
        return subprocess.call([sys.executable, str(HERE / 'build_car_atlas.py')])
    return 0


if __name__ == '__main__':
    sys.exit(main())
