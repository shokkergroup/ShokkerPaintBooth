"""Finish CARDS: one LLM annotation per catalogue item (4,799), written ONCE and shipped with the app (owner 2026-10-03: the intelligence must live in the DATA so
Claude / OpenAI / DeepSeek / no-key users all get it).  Resumable, append-only, filtered output.

  node scripts/ai_atlas/dump_items_for_cards.js                       # 1. atlas data -> _atlas_cards/items.json
  python scripts/ai_atlas/annotate_cards.py --pilot 300               # 2. stratified pilot (look at the result by eye!)
  python scripts/ai_atlas/annotate_cards.py                           # 3. everything not yet in _atlas_cards/cards.jsonl
  python scripts/ai_atlas/build_cards_js.py                           # 4. -> js/spb-ai-cards-data.js (lazy loaded by js/spb-ai-cards.js)

Each batch = 6 siblings (same shelf / name family, so the model can DIFFERENTIATE them) + ONE contact sheet of their baked thumbnails (or a /api/swatch render when no
thumbnail exists) + the measured numbers.  The model goes through the app's own /api/ai/chat route (the key never leaves the server; the daily cap applies).
"""
import os, sys, json, re, time, io, argparse, threading, urllib.request, urllib.error, base64, random
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, '_atlas_cards')
ITEMS = os.path.join(OUT, 'items.json')
CARDS = os.path.join(OUT, 'cards.jsonl')
THUMBS = os.path.join(OUT, 'thumbs')            # fetched swatches for items without a baked thumbnail
SHEETS = os.path.join(OUT, 'sheets')            # contact sheets (kept for eyeballing)
BASE = os.environ.get('SPB_CARDS_SERVER', 'http://127.0.0.1:59879')
MODEL = os.environ.get('SPB_CARDS_MODEL', 'deepseek/deepseek-v4.1-flash')
TH = os.path.join(ROOT, 'thumbnails')

MOODS = ['aggressive', 'stealth', 'luxury', 'elegant', 'retro', 'clean', 'playful', 'wild', 'rugged', 'techy', 'natural', 'spooky', 'cosmic', 'tropical', 'icy', 'fiery', 'dreamy', 'industrial', 'patriotic']
ERAS = ['50s-60s', '70s', '80s', '90s', 'modern', 'futuristic', 'timeless']
FITS = ['dirt late model', 'stock car', 'gt / sports car', 'open wheel', 'truck / off-road', 'show car']
USES = ['body', 'hood', 'roof', 'sides', 'stripes', 'numbers', 'trim', 'hero panel', 'bumpers', 'spoiler', 'under stripes']
SCALES = ['fine', 'medium', 'broad']

SYSTEM = (
    "You write the 'finish cards' for a car-paint design tool (iRacing liveries). A painter will later search and be advised using ONLY your cards, so be concrete, "
    "specific and honest. You are shown ONE contact sheet: numbered tiles (1..N) are the finishes below, in order (a tile may be missing for items marked 'no picture'). "
    "Base every card on the PICTURE and the MEASURED NUMBERS, not on the name alone; the name and description are hints. Never invent properties you cannot see or measure. "
    "Items marked 'takes the colour you give it' are drawn in a PLACEHOLDER colour (usually red or grey) only because a picture needs some colour: describe their SURFACE (shine, flake, grain, texture, pattern, depth) and NEVER name or hint the picture's colour "
    "in look / syn / analog / pair (write 'in whatever colour you give it'); a colour word is allowed only when it is part of the material or name itself (copper, rust, gold leaf). "
    "Reply with ONLY a JSON array, one object per item, in order, no markdown."
)

FINISH_SCHEMA = (
    'For each FINISH (a paint material or a complete special look) return {"i":<number>,"look":"<=24 words: what it looks like on a race car, plain words, no hype",'
    '"analog":["<=4 real-world things/materials it resembles"],'
    '"syn":["10-16 words or short phrases a painter might TYPE to find this (colours, materials, objects, moods, places, eras); lower case; include the obvious AND the lateral ones"],'
    '"mood":[0-3 from ' + json.dumps(MOODS) + '],"era":[0-2 from ' + json.dumps(ERAS) + '],"fit":[0-3 car types it suits, from ' + json.dumps(FITS) + '],'
    '"use":[1-3 best placements, from ' + json.dumps(USES) + '],'
    '"loud":<1 whisper .. 5 shouts>,"busy":<1 clean/flat .. 5 chaotic/detailed>,'
    '"pair":["<=4 colours or finishes it pairs well with"],"avoid":["<=2 short cautions, e.g. numbers, big dark areas in the sim, next to other loud finishes; [] if none"]}.'
)
SPEC_SCHEMA = (
    'For each SPEC PATTERN (a texture that changes ONLY the shine channels, never the colour) return {"i":<number>,"look":"<=24 words: how the surface reflects/feels",'
    '"analog":["<=4 real-world things"],"syn":["10-16 search words"],"mood":[0-3 from ' + json.dumps(MOODS) + '],"scale":"' + '|'.join(SCALES) + '","use":[1-3 from ' + json.dumps(USES) + '],'
    '"loud":<1..5>,"busy":<1..5>,"pair":["<=4 base finishes it works on, e.g. matte, gloss, metallic, chrome"],"avoid":[<=2 cautions]}.'
)
PATTERN_SCHEMA = (
    'For each PAINT PATTERN (a pattern drawn in colour over a base) return {"i":<number>,"look":"<=24 words: what the pattern looks like",'
    '"analog":["<=4 real-world things"],"syn":["10-16 search words"],"mood":[0-3 from ' + json.dumps(MOODS) + '],"era":[0-2 from ' + json.dumps(ERAS) + '],"scale":"' + '|'.join(SCALES) + '",'
    '"use":[1-3 from ' + json.dumps(USES) + '],"loud":<1..5>,"busy":<1..5>,"pair":["<=4 base finishes or colours it works with"],"avoid":[<=2 cautions]}.'
)


def get_json(url, body=None, timeout=120):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def thumb_path(it):
    t, i = it['k'].split('::', 1)
    if t == 'spec':                                                     # spec patterns have no baked thumbnail: the app renders a spec-map preview on demand
        p2 = os.path.join(THUMBS, 'spec__' + i + '.png')
        if os.path.exists(p2):
            return p2
        try:
            with urllib.request.urlopen('%s/api/spec-pattern-preview/%s' % (BASE, urllib.parse.quote(i)), timeout=60) as r:
                raw = r.read()
            os.makedirs(THUMBS, exist_ok=True); open(p2, 'wb').write(raw)
            return p2
        except Exception:
            return None
    if t in ('base', 'monolithic', 'pattern'):
        p = os.path.join(TH, t, i + '.png')
        if os.path.exists(p):
            return p
        p2 = os.path.join(THUMBS, t + '__' + i + '.png')
        if os.path.exists(p2):
            return p2
        if t in ('base', 'monolithic', 'pattern'):                      # render it through the app's swatch route (takes-colour finishes get a neutral mid colour)
            try:
                col = '8a8f98'
                url = '%s/api/swatch/%s/%s?size=128&color=%s' % (BASE, t, urllib.parse.quote(i), col)
                with urllib.request.urlopen(url, timeout=60) as r:
                    raw = r.read()
                os.makedirs(THUMBS, exist_ok=True)
                open(p2, 'wb').write(raw)
                return p2
            except Exception:
                return None
    return None


def font(sz):
    for f in ('arialbd.ttf', 'arial.ttf', 'segoeuib.ttf'):
        try:
            return ImageFont.truetype(f, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def sheet(batch, tag):
    cell = 192; cols = 3; rows = (len(batch) + cols - 1) // cols
    im = Image.new('RGB', (cols * cell, rows * cell), (20, 20, 28)); d = ImageDraw.Draw(im); f = font(26)
    have = 0
    for n, it in enumerate(batch):
        x, y = (n % cols) * cell, (n // cols) * cell
        p = thumb_path(it)
        if p:
            try:
                t = Image.open(p).convert('RGB').resize((cell - 8, cell - 8), Image.LANCZOS); im.paste(t, (x + 4, y + 4)); have += 1
            except Exception:
                p = None
        d.rectangle([x + 4, y + 4, x + 40, y + 36], fill=(0, 0, 0)); d.text((x + 12, y + 6), str(n + 1), fill=(255, 255, 255), font=f)
        if not p:
            d.text((x + 50, y + cell // 2 - 10), 'no picture', fill=(160, 160, 170), font=font(20))
    os.makedirs(SHEETS, exist_ok=True)
    path = os.path.join(SHEETS, tag + '.jpg'); im.save(path, quality=88)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=86)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii'), have


HINTS = {}
_hp = os.path.join(OUT, 'qa_hints.json')       # {key: "QA note"} written by the QA step; appended to that item's line so a redo fixes the specific fault
if os.path.exists(_hp):
    try:
        HINTS = json.load(open(_hp, encoding='utf-8'))
    except Exception:
        HINTS = {}


def describe(n, it):
    line = _describe(n, it)
    return line + (' | QA NOTE (fix this in the new card): ' + HINTS[it['k']] if it['k'] in HINTS else '')


def _describe(n, it):
    t = it['k'].split('::')[0]; sh = ', '.join(it.get('shelves') or [])
    if t == 'spec':
        return '%d. SPEC PATTERN "%s" [%s] group=%s | channels=%s | coverage=%s%% contrast=%s texture=%s anisotropy=%s | defaults=%s | note: %s | tags: %s' % (
            n, it['n'], it['k'], it.get('g'), it.get('ch'), it.get('cov'), it.get('con'), it.get('fb'), it.get('an'), json.dumps(it.get('df')), (it.get('d') or '')[:170], ', '.join(it.get('t') or []))
    if t == 'pattern':
        return '%d. PAINT PATTERN "%s" [%s] group=%s | coverage=%s%% contrast=%s texture=%s anisotropy=%s | palette=%s (%s) | note: %s | tags: %s' % (
            n, it['n'], it['k'], it.get('g'), it.get('cov'), it.get('con'), it.get('fb'), it.get('an'), ' '.join(it.get('c') or []), it.get('cn'), (it.get('d') or '')[:170], ', '.join(it.get('t') or []))
    kind = 'BASE MATERIAL' if t == 'base' else 'COMPLETE SPECIAL LOOK'
    m = it.get('M') or [0, 0]; r = it.get('R') or [0, 0]; c = it.get('C') or [0, 0]
    if it.get('o') != 1:
        # 2026-10-03 (second review #13): a takes-colour finish is only PICTURED in a placeholder colour (red / grey): the colour is not part of the finish, so the model is not shown it
        return ('%d. %s "%s" [%s] shelf: %s | takes the colour you give it (shine only; the picture uses a PLACEHOLDER colour, ignore it) | texture=%s shine=%s metal=%s sparkle=%s/100 | spec means metal=%s rough=%s clearcoat=%s | note: %s | tags: %s' % (
            n, kind, it['n'], it['k'], sh, it.get('fb'), it.get('shine'), it.get('metal'), it.get('sp'), m[0], r[0], c[0], (it.get('d') or '')[:170], ', '.join(it.get('t') or [])))
    return ('%d. %s "%s" [%s] shelf: %s | %s | palette=%s (%s), lightness=%s/100 saturation=%s contrast=%s hue-spread=%s (%s hue families) | texture=%s shine=%s metal=%s sparkle=%s/100 | spec means metal=%s rough=%s clearcoat=%s | note: %s | tags: %s' % (
        n, kind, it['n'], it['k'], sh, 'BRINGS ITS OWN COLOURS', ' '.join(it.get('c') or []), it.get('cn'), it.get('L'), it.get('S'), it.get('V'),
        it.get('hs'), it.get('hc'), it.get('fb'), it.get('shine'), it.get('metal'), it.get('sp'), m[0], r[0], c[0], (it.get('d') or '')[:170], ', '.join(it.get('t') or [])))


def clean_list(v, vocab=None, mx=16):
    if not isinstance(v, list):
        return []
    out = []
    for x in v:
        x = re.sub(r'\s+', ' ', str(x)).strip().lower()
        if not x or x in out:
            continue
        if vocab is not None and x not in vocab:
            continue
        out.append(x)
        if len(out) >= mx:
            break
    return out


def normalise(card, it):
    t = it['k'].split('::')[0]
    o = {'k': it['k'], 'look': re.sub(r'\s+', ' ', str(card.get('look') or '')).strip()[:200],
         'analog': clean_list(card.get('analog'), None, 4), 'syn': clean_list(card.get('syn'), None, 16), 'mood': clean_list(card.get('mood'), MOODS, 3),
         'use': clean_list(card.get('use'), USES, 3), 'pair': clean_list(card.get('pair'), None, 4), 'avoid': clean_list(card.get('avoid'), None, 2)}
    for k in ('loud', 'busy'):
        try:
            o[k] = max(1, min(5, int(round(float(card.get(k, 3))))))
        except Exception:
            o[k] = 3
    if t != 'spec':
        o['era'] = clean_list(card.get('era'), ERAS, 2)
    if t == 'monolithic' or t == 'base':
        o['fit'] = clean_list(card.get('fit'), FITS, 3)
    if t in ('spec', 'pattern'):
        s = str(card.get('scale') or '').lower().strip()
        o['scale'] = s if s in SCALES else ''
    return o


def extract_json(text):
    m = re.search(r'\[[\s\S]*\]', text or '')
    if not m:
        return None
    s = m.group(0)
    try:
        return json.loads(s)
    except Exception:
        s2 = re.sub(r',\s*([\]}])', r'\1', s)
        try:
            return json.loads(s2)
        except Exception:
            return None


LOCK = threading.Lock()
SPEND = {'cost': 0.0, 'calls': 0, 'fail': 0}


def call_batch(bi, batch, cap):
    t = batch[0]['k'].split('::')[0]
    schema = SPEC_SCHEMA if t == 'spec' else (PATTERN_SCHEMA if t == 'pattern' else FINISH_SCHEMA)
    img, have = sheet(batch, 'b%05d' % bi)
    lines = '\n'.join(describe(n + 1, it) for n, it in enumerate(batch))
    user = (schema + '\n\nITEMS (the numbers match the tiles of the contact sheet):\n' + lines +
            '\n\nWrite the cards. Make siblings DIFFERENT from each other (what would make a painter pick this one over its neighbour?). Remember: reply with ONLY the JSON array.')
    content = [{'type': 'text', 'text': user}]
    if img:
        content.append({'type': 'image_url', 'image_url': {'url': img}})
    body = {'model': MODEL, 'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': content if img else user}], 'max_tokens': 3600, 'temperature': 0.3, 'reasoning': {'enabled': False}, 'vision': bool(img)}
    last = None
    for attempt in range(3):
        if SPEND['cost'] > cap:
            return None
        try:
            r = get_json(BASE + '/api/ai/chat', body, 150)
            if not r.get('ok'):
                last = r.get('message') or r.get('error'); time.sleep(2 + attempt * 3); continue
            u = r.get('usage') or {}
            with LOCK:
                SPEND['cost'] += float(u.get('cost') or 0); SPEND['calls'] += 1
            arr = extract_json((r.get('message') or {}).get('content') or '')
            if isinstance(arr, list) and len(arr) >= 1:
                return arr, have
            last = 'unparseable'
        except urllib.error.HTTPError as e:
            last = 'http %s' % e.code
            if e.code in (402, 429):
                time.sleep(15)
        except Exception as e:
            last = str(e)[:80]; time.sleep(3)
    with LOCK:
        SPEND['fail'] += 1
    print('batch %d failed: %s' % (bi, last), flush=True)
    return None


def main():
    import urllib.parse  # noqa  (used lazily above)
    ap = argparse.ArgumentParser()
    ap.add_argument('--pilot', type=int, default=0, help='annotate a stratified sample of N items instead of everything')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--cap', type=float, default=4.0, help='stop when this run has spent this many dollars')
    ap.add_argument('--batch', type=int, default=6)
    ap.add_argument('--types', default='base,monolithic,pattern,spec')
    args = ap.parse_args()
    items = json.load(open(ITEMS, encoding='utf-8'))
    want = set(args.types.split(','))
    items = [it for it in items if it['k'].split('::')[0] in want]
    done = set()
    if os.path.exists(CARDS):
        for l in open(CARDS, encoding='utf-8'):
            try:
                done.add(json.loads(l)['k'])
            except Exception:
                pass
    def fam(it):
        nm = re.split(r'[ :\-—/(]', it['n'].lower())[0]
        return (it['k'].split('::')[0], (it.get('shelves') or [''])[0], nm, it['n'])
    items.sort(key=fam)
    if args.pilot:
        step = max(1, len(items) // args.pilot)
        items = items[::step][:args.pilot]
    todo = [it for it in items if it['k'] not in done]
    print('items %d, already done %d, to do %d' % (len(items), len(done), len(todo)), flush=True)
    byt = {}
    for it in todo:
        byt.setdefault(it['k'].split('::')[0], []).append(it)
    batches = []
    for t, lst in byt.items():
        for i in range(0, len(lst), args.batch):
            batches.append(lst[i:i + args.batch])
    random.Random(7).shuffle(batches) if args.pilot else None
    t0 = time.time(); ok_items = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(call_batch, bi, b, args.cap): (bi, b) for bi, b in enumerate(batches)}
        for n, f in enumerate(as_completed(futs)):
            bi, b = futs[f]
            res = f.result()
            if not res:
                continue
            arr, have = res
            lines = []
            for card in arr:
                try:
                    idx = int(card.get('i')) - 1
                except Exception:
                    continue
                if 0 <= idx < len(b):
                    o = normalise(card, b[idx]); o['vis'] = bool(have and thumb_path(b[idx])); o['m'] = MODEL; lines.append(json.dumps(o, ensure_ascii=False))
            with LOCK:
                with open(CARDS, 'a', encoding='utf-8') as fh:
                    fh.write('\n'.join(lines) + ('\n' if lines else ''))
            ok_items += len(lines)
            if (n + 1) % 10 == 0 or n + 1 == len(batches):
                print('batches %d/%d  cards +%d  spent $%.4f  fails %d  %.0fs' % (n + 1, len(batches), ok_items, SPEND['cost'], SPEND['fail'], time.time() - t0), flush=True)
    print('DONE cards +%d, spent $%.4f, fails %d' % (ok_items, SPEND['cost'], SPEND['fail']), flush=True)


if __name__ == '__main__':
    import urllib.parse
    main()
