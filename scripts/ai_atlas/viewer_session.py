#!/usr/bin/env python
"""iRacing 3D-viewer calibration, step by step (SPB-AI 2026-10-02).  The point: the flat UV sheet cannot be read by vision, but a 3D car with coloured panels can.

  1. In the app (car loaded, islands found):  SpbProCar.calibrationSheet(2048, page)  -> a PNG where every big island has its own flat colour + a legend (colour -> island id, bbox).
     pw/t230_calsheet.py saves <tag>_sheet.png and <tag>_legend.json for you.
  2. prepare:  put that PNG into the car's iRacing paint folder as car_<custid>.tga (the car you own in the paint viewer).  Everything it replaces is MOVED to
     <folder>/_spb_viewer_backup/<stamp>/ with a manifest - nothing is deleted - and `restore` puts it all back.
  3. In iRacing's paint viewer: reload the paint, look at the car from several sides, and write findings.json:  {"orange": "hood", "blue": ["left side"], "lime": "roof"}
     (colour names come from the legend; one colour may be several parts, several colours may make ONE part).
  4. learn:   turns findings + legend into one box per part (the union of its islands) and POSTs it to the app's learned-car store with source 'viewer'
     (the best-quality source: merge_learned_cars.py ships those to every buyer).  Then:  restore.

  python scripts/ai_atlas/viewer_session.py prepare --folder "trucks ram2026" --png _easy_claude_work/viewer_cal/ram_sheet.png
  python scripts/ai_atlas/viewer_session.py learn   --legend ram_legend.json --findings findings.json --folder "trucks ram2026"
  python scripts/ai_atlas/viewer_session.py restore --folder "trucks ram2026"
"""
import argparse, json, os, re, shutil, sys, time, urllib.request
from pathlib import Path

PAINT = Path(os.environ.get('SPB_IRACING_PAINT') or Path.home() / 'Documents' / 'iRacing' / 'paint')


def paint_dir(folder):
    d = Path(folder)
    if not d.is_absolute():
        d = PAINT / folder
    if not d.is_dir():
        sys.exit('paint folder not found: %s' % d)
    return d


def custid(d, given):
    if given:
        return str(given)
    ids = {}
    for p in list(d.glob('car_*.tga')) + list(d.parent.glob('car_*.tga')):
        m = re.fullmatch(r'car_(\d+)\.tga', p.name, re.I)
        if m:
            ids[m.group(1)] = ids.get(m.group(1), 0) + 1
    return max(ids, key=ids.get) if ids else '23371'


def write_tga(png, out):
    from PIL import Image
    im = Image.open(png).convert('RGB')
    if im.size != (2048, 2048):
        im = im.resize((2048, 2048), Image.NEAREST)          # flat colours: nearest keeps the edges crisp
    im.save(out, format='TGA')


def prepare(a):
    d = paint_dir(a.folder)
    cid = custid(d, a.custid)
    bak = d / '_spb_viewer_backup' / time.strftime('%Y%m%d-%H%M%S')
    bak.mkdir(parents=True)
    moved = []
    # the paint, the number layer and the spec must all go, or they would be drawn over / mixed into the colour code
    for pat in ('car_%s.tga', 'car_num_%s.tga', 'car_spec_%s.mip', 'car_spec_%s.tga', 'car_decal_%s.tga'):
        f = d / (pat % cid)
        if f.exists():
            shutil.move(str(f), str(bak / f.name))
            moved.append(f.name)
    out = d / ('car_%s.tga' % cid)
    write_tga(a.png, out)
    (bak / 'manifest.json').write_text(json.dumps({'folder': str(d), 'custid': cid, 'moved': moved, 'wrote': out.name, 'stamp': bak.name}, indent=1), encoding='utf-8')
    print('prepared %s: wrote %s, moved aside %s -> %s' % (d.name, out.name, moved or 'nothing', bak))
    print('NOW: reload the paint in the iRacing viewer, look at the car, write findings.json, run `learn`, then `restore`.')


def restore(a):
    d = paint_dir(a.folder)
    root = d / '_spb_viewer_backup'
    stamps = sorted(p for p in root.glob('*') if (p / 'manifest.json').exists()) if root.exists() else []
    if not stamps:
        sys.exit('nothing to restore in %s' % root)
    bak = stamps[-1] if not a.stamp else root / a.stamp
    man = json.loads((bak / 'manifest.json').read_text(encoding='utf-8'))
    wrote = d / man['wrote']
    if wrote.exists():
        wrote.unlink()                                          # only the calibration sheet WE wrote
    for n in man['moved']:
        shutil.move(str(bak / n), str(d / n))
    (bak / 'manifest.json').rename(bak / 'manifest.restored.json')
    print('restored %s: %s' % (d.name, man['moved'] or 'only removed the calibration sheet'))


def learn(a):
    legends = [json.loads(Path(p).read_text(encoding='utf-8')) for p in a.legend]
    findings = [json.loads(Path(p).read_text(encoding='utf-8')) for p in a.findings]
    if len(legends) != len(findings):
        sys.exit('give one --findings file per --legend file (same order)')
    per = {}
    for leg, found in zip(legends, findings):
        by = {l['colour'].lower(): l for l in leg['legend']}
        for colour, names in found.items():
            l = by.get(colour.lower())
            if not l:
                print('unknown colour in findings (not in the legend):', colour)
                continue
            for nm in (names if isinstance(names, list) else [names]):
                u = per.setdefault(str(nm).strip().lower(), [1.0, 1.0, 0.0, 0.0])
                b = l['bbox']
                u[0], u[1], u[2], u[3] = min(u[0], b[0]), min(u[1], b[1]), max(u[2], b[2]), max(u[3], b[3])
    if not per:
        sys.exit('no parts to learn')
    parts = {nm: {'box': [round(max(0, u[0] - 0.004), 4), round(max(0, u[1] - 0.004), 4), round(min(1, u[2] + 0.004), 4), round(min(1, u[3] + 0.004), 4)]} for nm, u in per.items()}
    head = legends[0]
    body = {'source': 'viewer', 'car': a.name or head.get('psdName'), 'folder': a.folder or head.get('folder'), 'layoutSig': head.get('layoutSig'), 'sheet': head.get('sheet'), 'parts': parts, 'psdName': head.get('psdName')}
    if a.dry:
        print(json.dumps(body, indent=1))
        return
    req = urllib.request.Request(a.base.rstrip('/') + '/api/ai/learned-cars', data=json.dumps(body).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    print(urllib.request.urlopen(req, timeout=20).read().decode('utf-8')[:300])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--folder', required=True); p.add_argument('--png', required=True); p.add_argument('--custid'); p.set_defaults(fn=prepare)
    p = sub.add_parser('restore'); p.add_argument('--folder', required=True); p.add_argument('--stamp'); p.set_defaults(fn=restore)
    p = sub.add_parser('learn'); p.add_argument('--legend', nargs='+', required=True); p.add_argument('--findings', nargs='+', required=True)
    p.add_argument('--folder'); p.add_argument('--name'); p.add_argument('--base', default='http://127.0.0.1:59876'); p.add_argument('--dry', action='store_true'); p.set_defaults(fn=learn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
