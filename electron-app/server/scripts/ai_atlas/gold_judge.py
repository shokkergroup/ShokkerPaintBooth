"""Judge retrieval systems on the gold asks FROM THE PICTURES (contact sheet of the 6 results + names).  A relative measure, not truth:
python scripts/ai_atlas/gold_judge.py lexical cards [--limit N]     -> prints relevance@6, hit-rate, bad-rate, distinct items;  writes _easy_claude_work/gold/judged_<system>.json"""
import os, sys, json, re, time, io, base64, argparse, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
from annotate_cards import thumb_path, font, ROOT
from PIL import Image, ImageDraw
GOLD = os.path.join(ROOT, '_easy_claude_work', 'gold')
BASE = os.environ.get('SPB_CARDS_SERVER', 'http://127.0.0.1:59879'); MODEL = os.environ.get('SPB_JUDGE_MODEL', 'deepseek/deepseek-v4.1-flash')
items = {i['k']: i for i in json.load(open(os.path.join(ROOT, '_atlas_cards', 'items.json'), encoding='utf-8'))}
SYS = ('You are a strict judge for a car-paint tool. A painter typed a request. Below are the 6 finishes the tool suggested: numbered tiles in one picture, with names. '
       'Judge ONLY whether each finish genuinely fits what the painter asked for (look, material, mood, constraints incl. negatives). '
       'Score each: 2 = clearly a good answer to the request, 1 = partly fits / acceptable, 0 = does not fit or contradicts it. Be harsh: a finish that merely shares a word with the request is 0. '
       'Reply ONLY with JSON: {"scores":[s1,s2,s3,s4,s5,s6]}')


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


def judge(row):
    keys = [k for k in row['keys'] if k in items][:6]
    if not keys:
        return {'ask': row['ask'], 'cat': row['cat'], 'keys': [], 'scores': []}
    names = '; '.join('%d=%s' % (i + 1, items[k]['n']) for i, k in enumerate(keys))
    user = [{'type': 'text', 'text': 'Painter request: "%s"\nFinishes (names): %s\nReply with the JSON only.' % (row['ask'], names)}, {'type': 'image_url', 'image_url': {'url': sheet(keys)}}]
    for a in range(5):
        try:
            r = post({'model': MODEL, 'messages': [{'role': 'system', 'content': SYS}, {'role': 'user', 'content': user}], 'max_tokens': 200, 'temperature': 0, 'reasoning': {'enabled': False}, 'vision': True})
            if not r.get('ok'):
                time.sleep(6 + a * 4); continue
            m = re.search(r'\{[\s\S]*\}', (r.get('message') or {}).get('content') or ''); sc = json.loads(m.group(0))['scores']
            sc = [max(0, min(2, int(x))) for x in sc][:len(keys)]
            return {'ask': row['ask'], 'cat': row['cat'], 'keys': keys, 'scores': sc, 'cost': (r.get('usage') or {}).get('cost', 0)}
        except Exception:
            time.sleep(4 + a * 3)
    return {'ask': row['ask'], 'cat': row['cat'], 'keys': keys, 'scores': []}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('systems', nargs='+'); ap.add_argument('--limit', type=int, default=0); a = ap.parse_args()
    for s in a.systems:
        rows = json.load(open(os.path.join(GOLD, 'results_' + s + '.json'), encoding='utf-8'))
        if a.limit:
            rows = rows[:a.limit]
        prev = {}
        jp = os.path.join(GOLD, 'judged_' + s + '.json')
        if os.path.exists(jp):
            for r in json.load(open(jp, encoding='utf-8')):
                if r.get('scores'):
                    prev[(r['ask'], tuple(r['keys']))] = r
        todo = [r for r in rows if (r['ask'], tuple(k for k in r['keys'] if k in items)[:6]) not in prev]
        with ThreadPoolExecutor(3) as ex:
            done = list(ex.map(judge, todo))
        for r in done:
            prev[(r['ask'], tuple(r['keys']))] = r
        res = [prev.get((r['ask'], tuple(k for k in r['keys'] if k in items)[:6])) or {'ask': r['ask'], 'cat': r['cat'], 'keys': [], 'scores': []} for r in rows]
        json.dump(res, open(os.path.join(GOLD, 'judged_' + s + '.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        ok = [r for r in res if r['scores']]; n = sum(len(r['scores']) for r in ok)
        rel = sum(sum(r['scores']) for r in ok) / max(1, n); good = sum(1 for r in ok if max(r['scores']) == 2) / max(1, len(ok)); bad = sum(1 for r in ok for x in r['scores'] if x == 0) / max(1, n)
        top3 = sum(sum(r['scores'][:3]) for r in ok) / max(1, sum(len(r['scores'][:3]) for r in ok)); distinct = len({k for r in ok for k in r['keys']})
        print('%-8s asks %d | mean relevance %.2f/2 | top3 %.2f | asks with a clear hit %.0f%% | bad picks %.0f%% | distinct finishes %d | cost $%.3f' % (s, len(ok), rel, top3, good * 100, bad * 100, distinct, sum(r.get('cost', 0) for r in ok)))
        cats = {}
        for r in ok:
            cats.setdefault(r['cat'], []).append(sum(r['scores']) / len(r['scores']))
        print('         ' + '  '.join('%s %.2f' % (c[:9], sum(v) / len(v)) for c, v in sorted(cats.items())))


if __name__ == '__main__':
    main()
