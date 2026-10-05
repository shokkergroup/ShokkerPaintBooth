#!/usr/bin/env python
"""Encyclopedia v2, lane C generator (2026-10-04): data/encyclopedia/car_pages.json = one page per car in the car atlas.

Facts come only from js/spb-car-atlas-data.js (window.SPB_CAR_ATLAS.cars: id, name, folders, sigs, parts{box,front,up}, members, learned, guess)
and scripts/ai_atlas/enc_inventory.json (records car.<id>, used for covers). Re-run any time:  python scripts/ai_atlas/enc_gen_C.py
Output is deterministic (sorted by library order), written atomically (temp file + os.replace). Ids: car_pages.<carid>; covers: ["car.<carid>"].
"""
import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import enc_hidden as _H   # shared hidden-feature list (Easy mode is hidden, owner rule 2026-10-04)
from enc_write_C import norm, _other_aliases, TODAY  # same alias normaliser the gate uses

ATLAS = ROOT / 'js' / 'spb-car-atlas-data.js'
INV = ROOT / 'scripts' / 'ai_atlas' / 'enc_inventory.json'
OUT = ROOT / 'data' / 'encyclopedia' / 'car_pages.json'
SRC = 'js/spb-car-atlas-data.js:2'
SHEET = 2048

PART_NOTE = {
    'hood': 'the hood panel',
    'roof': 'the roof panel',
    'trunk': 'the trunk lid',
    'left side': 'the driver-side body panel',
    'right side': 'the passenger-side body panel',
    'front bumper': 'the front fascia and bumper',
    'rear bumper': 'the rear fascia and bumper',
    'spoiler': 'the rear spoiler',
    'bed': 'the truck bed',
    'tailgate': 'the tailgate',
    'wing sideboards': 'the sprint-car wing side boards',
    'top wing': 'the top wing',
    'tank': 'the fuel tank cover',
}
ORDER = ['hood', 'roof', 'trunk', 'bed', 'tailgate', 'left side', 'right side', 'front bumper', 'rear bumper', 'spoiler', 'top wing', 'wing sideboards', 'tank']


def load_atlas():
    s = ATLAS.read_text(encoding='utf-8')
    return json.loads(s[s.index('{'):s.rindex('}') + 1])['cars']


def where(box):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    h = 'left' if cx < 0.34 else ('right' if cx > 0.66 else 'middle')
    v = 'top' if cy < 0.34 else ('bottom' if cy > 0.66 else 'middle')
    pos = ('the centre' if h == 'middle' and v == 'middle' else 'the ' + (v + ' ' + h).replace('middle ', '').replace(' middle', '')) + ' of the sheet'
    w, hh = int(round((x1 - x0) * SHEET, -1)), int(round((y1 - y0) * SHEET, -1))
    return pos, w, hh


def pretty_folder(f):
    return f.strip()


def build(car, covers_ok):
    cid, name = car['id'], car['name']
    parts = car.get('parts') or {}
    folders = [pretty_folder(f) for f in (car.get('folders') or [])]
    draft = bool(car.get('guess'))
    members = car.get('members')
    names = [p for p in ORDER if p in parts] + [p for p in parts if p not in ORDER]
    short = re.sub(r'\s*\(draft\)\s*$', '', name).strip()

    # ---- parts sentences
    plines = []
    tips = []
    for p in names:
        d = parts[p]
        pos, w, h = where(d['box'])
        line = '%s (%s): %s, roughly %d by %d pixels on the 2048 sheet' % (p, PART_NOTE.get(p, 'a named part'), pos, w, h)
        if d.get('front'):
            line += '; the car\'s front points to the %s edge of the sheet' % d['front']
        if d.get('up') == 'bottom':
            line += '; drawn upside down (the roof side is toward the bottom)'
        plines.append(line)
        if d.get('up') == 'bottom':
            tips.append('The %s is drawn upside down on this sheet, so a stripe that runs upward on the sheet runs downward on the car. Check the preview.' % p)
    if not tips:
        tips.append('Check the preview after aiming a zone at a side panel: stripes that rise or fall should match the real car.')
    tips.append('Say "the %s" in Chat and the zone is aimed for you.' % (names[0] if names else 'hood'))

    # ---- status
    if draft:
        status = ('This entry is a DRAFT layout learned from look-alike sheets, with only %d named parts. Shokker proposes it but asks you to confirm before using it, so the parts may be incomplete or off.' % len(parts))
    else:
        status = 'This is a checked layout from the car library, with %d named parts.' % len(parts)
    if members and not draft:
        status += ' It was built from a group of %d template files that share this same sheet layout.' % members

    if folders:
        fold = 'iRacing car folder name%s: %s.' % ('s' if len(folders) > 1 else '', '; '.join(folders))
        recog = 'Shokker recognises this car by its sheet layout and by the iRacing car folder name.'
    else:
        fold = 'No iRacing folder name is recorded for this layout.'
        recog = 'Shokker recognises this car by the shape of its paintable area on the sheet. Set the iRacing Car Folder for your actual car yourself.'

    what = '%s %s %s Parts known: %s.' % (status, fold, recog, '; '.join(plines) if plines else 'none yet')
    summary = '%s: %s %d named part%s%s.' % (short, 'draft layout,' if draft else 'checked layout,', len(parts), '' if len(parts) == 1 else 's',
                                              ('; folder ' + folders[0]) if folders else '')

    how = ['Open your car\'s own template (the PSD, XCF or ORA button next to Source Paint), or a flat paint of this car.']
    if folders:
        how.append('Set the iRacing Car Folder to the "%s" folder so renders land where iRacing reads them.' % folders[0])
    else:
        how.append('Set the iRacing Car Folder to your car\'s folder in Documents > iRacing > paint.')
    how.append('Open Chat and ask for something on a part, for example "make the %s black".' % (names[0] if names else 'hood'))
    how.append('Look at the preview. Missing a part? Teach it once and Shokker remembers it for this car.' if (draft or len(parts) < 6) else 'Look at the preview and refine with words.')

    pit = ['Do not use another car\'s template; the panels will not match.']
    if draft:
        pit.append('Draft layouts are proposals. Confirm in the preview and correct any part that is wrong.')
    if 'spoiler' not in parts and 'top wing' not in parts:
        pit.append('No spoiler is recorded for this layout; if your car has one, teach it before aiming a zone at it.')
    missing = [p for p in ('hood', 'roof', 'left side', 'right side') if p not in parts]
    if missing:
        pit.append('Not recorded yet: %s. Teach %s before using %s in Chat.' % (', '.join(missing), 'it' if len(missing) == 1 else 'them', 'it' if len(missing) == 1 else 'them'))

    aliases = []
    for a in [short, name] + folders:
        aliases.append(a)
    sources = [SRC, 'js/spb-pro-carmap.js:372-386']
    art = {
        'id': 'car_pages.' + cid, 'title': short + ': parts and folder', 'domain': 'car_pages',
        'summary': summary[:240], 'what': what,
        'when': ['You are painting this car and want Chat to aim at a named part.', 'You want to check which iRacing folder this layout belongs to.'],
        'how': how, 'controls': [], 'tips': tips[:4], 'pitfalls': pit,
        'related': ['cars.supported_cars', 'cars.reading_sheet', 'cars.teach_parts', 'cars.choose_template'],
        'actions': [], 'figures': [], 'covers': ['car.' + cid] if cid in covers_ok else [],
        'sources': sources, 'quick': False, 'lane': 'C', 'updated': TODAY, 'aliases': aliases, 'generated': True,
    }
    return art


def main():
    cars = load_atlas()
    inv = json.loads(INV.read_text(encoding='utf-8'))['records']
    covers_ok = set(r['id'][4:] for r in inv if r['id'].startswith('car.'))
    taken = _other_aliases('car_pages.')       # aliases owned by every other article (pages/ included)
    taken = {k: v for k, v in taken.items() if not str(v).startswith('car_pages.')}
    seen, arts, dropped = set(), [], 0
    for car in cars:
        a = build(car, covers_ok)
        out = []
        for al in a['aliases']:
            n = norm(al)
            if n and n in taken:
                dropped += 1
            if not n or n in seen or n in taken:
                continue
            seen.add(n)
            out.append(n)
        a['aliases'] = out
        arts.append(a)
    doc = {'domain': 'car_pages', 'version': 1, 'generated': True,
           'note': 'One page per car in js/spb-car-atlas-data.js. Generated by scripts/ai_atlas/enc_gen_C.py - do not edit by hand.',
           'articles': arts}
    if _H.mentions(json.dumps(arts, ensure_ascii=False)): raise SystemExit('enc_gen_C: a car page names a hidden feature (enc_hidden_features.json)')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix('.json.tmp')
    head = {k: v for k, v in doc.items() if k != 'articles'}
    body = ',\n'.join(json.dumps(a, ensure_ascii=False, separators=(',', ':')) for a in arts)   # one compact article per line: stays under the 100 KB cap
    tmp.write_text(json.dumps(head, ensure_ascii=False)[:-1] + ',"articles":[\n' + body + '\n]}\n', encoding='utf-8')
    os.replace(tmp, OUT)
    print('car_pages: %d pages, %d KB, %d aliases dropped (collisions), %d with covers' % (len(arts), OUT.stat().st_size // 1024, dropped, sum(1 for a in arts if a['covers'])))


if __name__ == '__main__':
    main()
