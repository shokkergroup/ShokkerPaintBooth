#!/usr/bin/env python
"""Ship Claude's evidence-based DRAFT part boxes (_easy_claude_work/corpus/claude_suggestions.json) as GUESS entries of the car library: the app shows them as a confirm-first picture
('I think the parts are where the dashed boxes are - is that right?'), never as silent knowledge.  Owner labels (source 'owner') always win when they exist.
  python scripts/ai_atlas/apply_suggestions.py [--dry] [--min-tier T2]        then rebuild: python scripts/ai_atlas/build_car_atlas.py
SPB-AI 2026-10-02."""
import argparse, json, re, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import merge_learned_cars as M
SRC = HERE.parents[1] / '_easy_claude_work' / 'corpus' / 'claude_suggestions.json'


def key_of(n):
    return re.sub(r'[^a-z0-9]+', '', n.lower())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dry', action='store_true'); ap.add_argument('--no-build', action='store_true'); ap.add_argument('--min-tier', default='T2'); a = ap.parse_args()
    sug = json.loads(SRC.read_text(encoding='utf-8')); ok_tiers = {'T1'} if a.min_tier == 'T1' else {'T1', 'T2'}; new = []
    for folder, f in sug.items():
        if folder.startswith('_'):
            continue
        parts = {n: {'box': [round(float(v), 4) for v in p['box']]} for n, p in f['parts'].items() if p.get('tier') in ok_tiers}
        if not parts:
            continue
        new.append({'id': 'claude-' + key_of(folder), 'name': folder + ' (draft)', 'folders': [folder] + list(f.get('twins') or []), 'sigs': [], 'parts': parts, 'learned': True, 'guess': True,
                    'sources': ['claude-suggested'], 'n': 1, 'updated': time.strftime('%Y-%m-%dT%H:%M:%S')})
    print('%d draft car(s): %s' % (len(new), ', '.join('%s (%d parts)' % (e['name'], len(e['parts'])) for e in new)))
    if a.dry or not new:
        return 0
    cur = M.load(M.OUT)
    # an existing owner / viewer / taught entry for the same folder is kept untouched: drafts only fill gaps
    have = {M.norm_folder(f) for c in cur['cars'] if M.quality(c.get('sources')) >= 2 for f in c.get('folders', [])}
    new = [e for e in new if M.norm_folder(e['folders'][0]) not in have]
    ids = {c['id']: c for c in cur['cars']}
    for e in new:
        if e['id'] in ids:
            ids[e['id']].update(e)                  # refresh a previous draft
        else:
            cur['cars'].append(e)
    M.OUT.write_text(json.dumps(cur, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    print('written', M.OUT.name, 'total', len(cur['cars']))
    return 0 if a.no_build else subprocess.call([sys.executable, str(HERE / 'build_car_atlas.py')])


if __name__ == '__main__':
    sys.exit(main())
