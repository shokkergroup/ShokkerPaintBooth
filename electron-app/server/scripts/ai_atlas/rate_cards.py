"""RATE the finishes (second pass over the cards, 2026-10-03): how good a first suggestion is each item for a race-car livery, by ROLE.  Measured need: the ranker kept proposing dull / niche
items (primer, powder coat, odd patterns) because the cards say what a finish IS, not how GOOD A CHOICE it is.  One cheap vision call per 6 siblings (contact sheet + numbers).
  python scripts/ai_atlas/rate_cards.py [--workers 3] [--cap 1.0]       -> _atlas_cards/ratings.jsonl  (resumable)   then  python scripts/ai_atlas/build_cards_js.py
Ratings 1-5:  appeal (would most painters happily pick it)  body (a large area)  accent (thin stripe / trim / numbers)  hero (a single statement panel)  risk (looks wrong / muddy / hurts readability in the sim)"""
import os, sys, json, re, time, argparse, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, os.path.dirname(__file__))
from annotate_cards import ITEMS, OUT, MODEL, BASE, sheet, describe, get_json, extract_json, thumb_path, ROOT   # noqa

RATINGS = os.path.join(OUT, 'ratings.jsonl')
SYSTEM = ("You are an experienced iRacing livery painter rating finishes for a catalogue. You see ONE contact sheet: numbered tiles are the items listed below, in order. "
          "Rate each item honestly from the PICTURE and the numbers; use the whole 1-5 range and do NOT give everything a 4. Reply with ONLY a JSON array, one object per item, in order.")
SCHEMA = ('Return for each item {"i":<number>,"appeal":<1-5>,"body":<1-5>,"accent":<1-5>,"hero":<1-5>,"risk":<1-5>} where: '
          'appeal = how many painters would happily choose this as a good-looking, usable finish on a race car (5 = almost everyone, 3 = a decent niche, 1 = ugly / odd / almost nobody); '
          'body = how well it works across a LARGE area (hood, roof, sides) without looking messy, cheap or exhausting; '
          'accent = how well it works as a THIN stripe, trim line or number outline; '
          'hero = how well it works as ONE statement panel on an otherwise calm car; '
          'risk = the chance it looks wrong in a racing sim (muddy, noisy, unreadable under sun, kills number readability, clashes with everything): 1 = safe, 5 = very risky. '
          'For a SPEC PATTERN (shine texture) or PAINT PATTERN, judge it as a layer on top of a base: body = layered over a big area, accent = layered on a thin stripe.')
LOCK = threading.Lock(); SPEND = {'cost': 0.0, 'fail': 0}


def call(bi, batch, cap):
    img, have = sheet(batch, 'r%05d' % bi)
    lines = '\n'.join(describe(n + 1, it) for n, it in enumerate(batch))
    user = SCHEMA + '\n\nITEMS:\n' + lines + '\n\nReply with ONLY the JSON array.'
    body = {'model': MODEL, 'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': [{'type': 'text', 'text': user}, {'type': 'image_url', 'image_url': {'url': img}}]}],
            'max_tokens': 900, 'temperature': 0.2, 'reasoning': {'enabled': False}, 'vision': True}
    for a in range(5):
        if SPEND['cost'] > cap:
            return None
        try:
            r = get_json(BASE + '/api/ai/chat', body, 150)
            if not r.get('ok'):
                time.sleep(6 + a * 4); continue
            with LOCK:
                SPEND['cost'] += float((r.get('usage') or {}).get('cost') or 0)
            arr = extract_json((r.get('message') or {}).get('content') or '')
            if isinstance(arr, list) and arr:
                return arr
        except Exception:
            time.sleep(4 + a * 3)
    with LOCK:
        SPEND['fail'] += 1
    return None


def clamp(v):
    try:
        return max(1, min(5, int(round(float(v)))))
    except Exception:
        return 3


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=3); ap.add_argument('--cap', type=float, default=1.0); a = ap.parse_args()
    items = json.load(open(ITEMS, encoding='utf-8'))
    done = set()
    if os.path.exists(RATINGS):
        for l in open(RATINGS, encoding='utf-8'):
            try:
                done.add(json.loads(l)['k'])
            except Exception:
                pass
    key = lambda it: (it['k'].split('::')[0], (it.get('shelves') or [''])[0], re.split(r'[ :\-—/(]', it['n'].lower())[0], it['n'])
    items.sort(key=key)
    todo = [it for it in items if it['k'] not in done]
    byt = {}
    for it in todo:
        byt.setdefault(it['k'].split('::')[0], []).append(it)
    batches = [lst[i:i + 6] for lst in byt.values() for i in range(0, len(lst), 6)]
    print('to rate %d in %d batches' % (len(todo), len(batches)), flush=True)
    t0 = time.time(); n_ok = 0
    with ThreadPoolExecutor(a.workers) as ex:
        futs = {ex.submit(call, bi, b, a.cap): (bi, b) for bi, b in enumerate(batches)}
        for n, f in enumerate(as_completed(futs)):
            bi, b = futs[f]; arr = f.result()
            if not arr:
                continue
            lines = []
            for c in arr:
                try:
                    ix = int(c.get('i')) - 1
                except Exception:
                    continue
                if 0 <= ix < len(b):
                    lines.append(json.dumps({'k': b[ix]['k'], 'appeal': clamp(c.get('appeal')), 'body': clamp(c.get('body')), 'accent': clamp(c.get('accent')), 'hero': clamp(c.get('hero')), 'risk': clamp(c.get('risk'))}))
            with LOCK:
                open(RATINGS, 'a', encoding='utf-8').write('\n'.join(lines) + ('\n' if lines else ''))
            n_ok += len(lines)
            if (n + 1) % 20 == 0 or n + 1 == len(batches):
                print('batches %d/%d rated +%d spent $%.4f fails %d %.0fs' % (n + 1, len(batches), n_ok, SPEND['cost'], SPEND['fail'], time.time() - t0), flush=True)
    print('DONE rated +%d spent $%.4f fails %d' % (n_ok, SPEND['cost'], SPEND['fail']), flush=True)


if __name__ == '__main__':
    main()
