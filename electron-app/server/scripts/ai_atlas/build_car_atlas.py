#!/usr/bin/env python
"""Build js/spb-car-atlas-data.js from scripts/ai_atlas/car_atlas_src.json (hand-checked panel boxes) + sigs.json (layout fingerprints computed BY THE APP:
python _easy_claude_work/pw/t115.py  ->  scripts/ai_atlas/sigs.json).  SPB-AI 2026-09-30.
A fingerprint that says 'the paintable area is almost everything / almost nothing' carries no layout information and is dropped (that car is then matched by its iRacing folder only).
Usage: python scripts/ai_atlas/build_car_atlas.py"""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[2]
src = json.loads((Path(__file__).parent / 'car_atlas_src.json').read_text(encoding='utf-8'))
sigs = json.loads((Path(__file__).parent / 'sigs.json').read_text(encoding='utf-8'))
def usable(h):
    n = sum(bin(int(c, 16)).count('1') for c in h)
    return 1024 * 0.12 < n < 1024 * 0.93
cars = []
for c in src['cars']:
    tpls = c['template'] if isinstance(c['template'], list) else [c['template']]
    ss = [] if c.get('folder_only') else [sigs[t] for t in tpls if t in sigs and usable(sigs[t])]
    parts = {}
    for nm, p in c['parts'].items():
        b = [round(v / 100.0, 4) for v in p['box']]
        parts[nm] = {'box': b}
        if p.get('front'): parts[nm]['front'] = p['front']
        if p.get('up'): parts[nm]['up'] = p['up']
    car = {'id': c['id'], 'name': c['name'], 'folders': c.get('folders', []), 'sigs': ss, 'parts': parts}
    if c.get('folder_only'): car['folder_only'] = True
    cars.append(car)
    print('%-26s sigs=%d parts=%d folders=%s' % (c['id'], len(ss), len(parts), c.get('folders')))
# layout clusters found in the owner's PSD library (scan_psds.py -> catalog_templates.py -> cluster.py -> hand labels in car_atlas_clusters.json)
cf = Path(__file__).parent / 'car_atlas_clusters.json'
cl_src = R / '_easy_claude_work' / 'atlas' / 'clusters.json'
if cf.exists() and cl_src.exists():
    clusters = {c['cluster']: c for c in json.loads(cl_src.read_text(encoding='utf-8'))}
    taken = [sg for car in cars for sg in car['sigs']]
    def sim(a, b):
        pop = [bin(i).count('1') for i in range(16)]; i = u = 0
        for x, y in zip(a, b):
            x, y = int(x, 16), int(y, 16); i += pop[x & y]; u += pop[x | y]
        return i / u if u else 0
    n_added = 0
    for e in json.loads(cf.read_text(encoding='utf-8'))['cars']:
        c = clusters.get(e['cluster'])
        if not c or not c.get('sig') or not usable(c['sig']): print('skip cluster', e['cluster'], 'no usable fingerprint'); continue
        if any(sim(c['sig'], sg) >= 0.97 for sg in taken):
            print('cluster %d (%s) duplicates a hand-checked entry: kept the earlier one' % (e['cluster'], e['id'])); continue
        parts = {}
        for nm, p in e['parts'].items():
            b = [round(v / 100.0, 4) for v in p['box']]; parts[nm] = {'box': b}
            if p.get('front'): parts[nm]['front'] = p['front']
            if p.get('up'): parts[nm]['up'] = p['up']
        cars.append({'id': e['id'], 'name': e['name'], 'folders': e.get('folders', []), 'sigs': [c['sig']], 'parts': parts, 'members': c['n']})
        taken.append(c['sig']); n_added += 1
        print('%-30s cluster %-3d sigs=1 parts=%d (covers %d library PSDs)' % (e['id'], e['cluster'], len(parts), c['n']))
    print('clusters added:', n_added)
# iRacing folder keys + the layout fingerprint MEASURED from real driver paints (docs/CAR_LEARNING.md: _easy_claude_work/corpus/s7_folder_overlay.py -> car_atlas_folders.json)
ff = Path(__file__).parent / 'car_atlas_folders.json'
if ff.exists():
    def _jac(a, b):
        pop = [bin(i).count('1') for i in range(16)]; i = u = 0
        for x, y in zip(a, b):
            x, y = int(x, 16), int(y, 16); i += pop[x & y]; u += pop[x | y]
        return i / u if u else 0
    ov = json.loads(ff.read_text(encoding='utf-8')).get('cars', {})
    for car in cars:
        e = ov.get(car['id'])
        if not e:
            continue
        for fo in e.get('folders', []):
            if fo not in car['folders']:
                car['folders'].append(fo)
        for sg in e.get('sigs', []):
            if usable(sg) and all(_jac(sg, x) < 0.97 for x in car['sigs']):
                car['sigs'].append(sg)
        print('%-26s + corpus folders=%s sigs=%d' % (car['id'], e.get('folders'), len(car['sigs'])))
# layouts the APP learned (taught by buyers / confirmed from a look-alike / measured in the iRacing viewer): merge_learned_cars.py keeps car_atlas_learned.json
lf = Path(__file__).parent / 'car_atlas_learned.json'
if lf.exists():
    n_learn = 0
    for e in json.loads(lf.read_text(encoding='utf-8')).get('cars', []):
        if not e.get('parts') or any(c['id'] == e['id'] for c in cars):
            continue
        ss = [sg for sg in e.get('sigs', []) if usable(sg)]
        parts = {}
        for nm, p in e['parts'].items():
            parts[nm] = {'box': [round(float(v), 4) for v in p['box']]}
            if p.get('front'): parts[nm]['front'] = p['front']
            if p.get('up'): parts[nm]['up'] = p['up']
        # 'learned': the client treats these boxes as plain boxes (measured on a real sheet), never snaps them to islands like the hand-checked library boxes
        cars.append(dict({'id': e['id'], 'name': e['name'], 'folders': e.get('folders', []), 'sigs': ss, 'parts': parts, 'learned': True}, **({'guess': True} if e.get('guess') else {})))
        n_learn += 1
        print('%-30s learned  sigs=%d parts=%d folders=%s' % (e['id'], len(ss), len(parts), e.get('folders')))
    print('learned cars added:', n_learn)
out = '/* GENERATED by scripts/ai_atlas/build_car_atlas.py - do not edit. Car library for the AI copilot (hand-checked panel layouts). */\nwindow.SPB_CAR_ATLAS = ' + json.dumps({'v': 1, 'cars': cars}, separators=(',', ':')) + ';\n'
(R / 'js' / 'spb-car-atlas-data.js').write_text(out, encoding='utf-8', newline='\n')
print('wrote js/spb-car-atlas-data.js', len(out), 'bytes')
