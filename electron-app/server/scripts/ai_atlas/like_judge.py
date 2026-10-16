"""Judge the "like X but <modifier>" benchmark FROM THE PICTURES (relative, ~$0.03 a run).
   python scripts/ai_atlas/like_judge.py <name>      reads _easy_claude_work/like/cases_<name>.json, writes judged_<name>.json, prints mean score per modifier and per kind
   Tile 1 = the reference the painter likes; tiles 2-6 = what the tool returned.  2 = clearly similar in material / style AND clearly moved the asked way, 1 = similar but the move is weak or only partly there, 0 = not similar or the wrong direction."""
import os, sys, json, re, time, io, base64, urllib.request, collections
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from annotate_cards import thumb_path, font, ROOT
from PIL import Image, ImageDraw
D = os.path.join(ROOT, '_easy_claude_work', 'like')
BASE = os.environ.get('SPB_CARDS_SERVER', 'http://127.0.0.1:59879'); MODEL = os.environ.get('SPB_JUDGE_MODEL', 'deepseek/deepseek-v4.1-flash')
items = {i['k']: i for i in json.load(open(os.path.join(ROOT, '_atlas_cards', 'items.json'), encoding='utf-8'))}
WORDS = {'calm': 'calmer / quieter (less loud, less busy)', 'bold': 'bolder / louder', 'darker': 'darker', 'lighter': 'lighter / brighter', 'glossier': 'glossier / shinier', 'flatter': 'flatter / more matte', 'sparklier': 'with more sparkle / flake',
         'smoother': 'with less sparkle, smoother', 'metalmore': 'more metallic', 'metalless': 'less metallic', 'warmer': 'warmer in colour', 'cooler': 'cooler in colour', 'vivid': 'more vivid / colourful', 'muted': 'more muted', 'simpler': 'simpler / less busy',
         'busier': 'with more detail / busier', 'finer': 'finer in scale (smaller detail)', 'coarser': 'coarser in scale (bigger detail)', None: 'the same style (no change asked)'}
SYS = ('You are a strict judge for a car-paint tool. A painter likes ONE finish (tile 1, the reference) and asked for finishes like it but changed in one way. Tiles 2-6 are what the tool suggested. '
       'For EACH of tiles 2-6 score: 2 = clearly the same kind of material / style as the reference AND clearly moved the way asked; 1 = similar but the requested change is weak or only partly there; 0 = not similar, or changed the wrong way. '
       'Note: finishes that "take the colour you give them" are pictured in a placeholder colour: ignore that colour, judge shine, sparkle, metal, texture and scale. Be harsh. Reply ONLY with JSON: {"scores":[s2,s3,s4,s5,s6]}')


def sheet(keys):
    cell = 176; cols = 3; rows = (len(keys) + cols - 1) // cols; im = Image.new('RGB', (cols * cell, rows * cell), (20, 20, 28)); d = ImageDraw.Draw(im); f = font(24)
    for n, k in enumerate(keys):
        x, y = (n % cols) * cell, (n // cols) * cell; p = thumb_path(items[k]) if k in items else None
        if p:
            try:
                im.paste(Image.open(p).convert('RGB').resize((cell - 6, cell - 6), Image.LANCZOS), (x + 3, y + 3))
            except Exception:
                pass
        d.rectangle([x + 3, y + 3, x + 36, y + 32], fill=(0, 0, 0)); d.text((x + 10, y + 4), str(n + 1), fill=(255, 255, 255), font=f)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=84)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


def post(body):
    req = urllib.request.Request(BASE + '/api/ai/chat', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=150) as r:
        return json.loads(r.read().decode())


def judge(c):
    keys = [c['ref']] + [k for k in c['keys'] if k in items][:5]
    if len(keys) < 2:
        return dict(c, scores=[])
    names = '; '.join('%d=%s' % (i + 1, items[k]['n']) for i, k in enumerate(keys))
    user = [{'type': 'text', 'text': 'The painter likes tile 1 (%s) and asked for finishes like it, but %s.\nTiles: %s\nReply with the JSON only.' % (items[c['ref']]['n'], WORDS.get(c['mod']), names)}, {'type': 'image_url', 'image_url': {'url': sheet(keys)}}]
    for a in range(5):
        try:
            r = post({'model': MODEL, 'messages': [{'role': 'system', 'content': SYS}, {'role': 'user', 'content': user}], 'max_tokens': 200, 'temperature': 0, 'reasoning': {'enabled': False}, 'vision': True})
            if not r.get('ok'):
                time.sleep(6 + a * 4); continue
            m = re.search(r'\{[\s\S]*\}', (r.get('message') or {}).get('content') or ''); sc = json.loads(m.group(0))['scores']
            return dict(c, scores=[max(0, min(2, int(x))) for x in sc][:len(keys) - 1], cost=(r.get('usage') or {}).get('cost', 0))
        except Exception:
            time.sleep(4 + a * 3)
    return dict(c, scores=[])


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'base'
    cases = json.load(open(os.path.join(D, 'cases_' + name + '.json'), encoding='utf-8'))
    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(judge, cases))
    json.dump(res, open(os.path.join(D, 'judged_' + name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    ok = [r for r in res if r['scores']]
    def mean(rs):
        n = sum(len(r['scores']) for r in rs); return sum(sum(r['scores']) for r in rs) / max(1, n)
    print('%-10s cases %d | mean %.2f/2 | top3 %.2f | cost $%.3f' % (name, len(ok), mean(ok), sum(sum(r['scores'][:3]) for r in ok) / max(1, sum(len(r['scores'][:3]) for r in ok)), sum(r.get('cost', 0) for r in ok)))
    by = collections.defaultdict(list); bk = collections.defaultdict(list)
    for r in ok:
        by[r['mod']].append(r); bk[r['kind']].append(r)
    print('  by kind: ' + '  '.join('%s %.2f(%d)' % (k, mean(v), len(v)) for k, v in sorted(bk.items())))
    print('  by mod : ' + '  '.join('%s %.2f(%d)' % (str(k), mean(v), len(v)) for k, v in sorted(by.items(), key=lambda kv: str(kv[0]))))


main()
