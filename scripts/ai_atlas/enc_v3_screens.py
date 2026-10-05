#!/usr/bin/env python
"""Lane C v3: attach real screenshots (lane S, data/encyclopedia/screens.json) to the hand-written lane C articles.

For each lane C hand-written article:
  1. every screen whose article_ids[] names the article (lane S's own assignment) goes first;
  2. otherwise the best 1-2 screens by word overlap between the article (title, summary, aliases, domain) and the screen (title, caption, alt, kind);
  3. if nothing overlaps at all, the first ui screen (window tour) so the article always shows the real window.
Already-set screens[] that still exist in screens.json are kept (only dropped ids are replaced). Idempotent.
Run: python scripts/ai_atlas/enc_v3_screens.py [--check]
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import enc_write_C as W
import enc_reader_fix as RF          # ENC_READER_FIX 2026-10-05: a picture must show the article's topic (screen_ok)

DOMAINS = ['getting_started', 'workflows', 'playbook', 'preview_render', 'cars', 'shokk_drop', 'ai_copilot', 'settings', 'recipes', 'concepts', 'support']
STOP = set('the a an and or of to in on for with is are it its be your you how what why do does my this that from as at by not no can will when into than then'.split())


def words(s):
    return {w for w in re.findall(r'[a-z0-9]+', (s or '').lower()) if len(w) > 2 and w not in STOP}


def main():
    check = '--check' in sys.argv
    sc = json.loads((ROOT / 'data' / 'encyclopedia' / 'screens.json').read_text(encoding='utf-8'))
    screens = sc.get('screens') or []
    ids = {s['id'] for s in screens}
    if not screens:
        sys.exit('no screens yet')
    by_art = {}
    for s in screens:
        for a in s.get('article_ids', []):
            by_art.setdefault(a, []).append(s['id'])
    ui = next((s['id'] for s in screens if s.get('kind') == 'ui'), screens[0]['id'])
    sw = {s['id']: words(' '.join([s.get('title', ''), s.get('caption', ''), s.get('alt', ''), s.get('kind', '')])) for s in screens}
    short, changed = [], 0
    for dom in DOMAINS:
        fp = ROOT / 'data' / 'encyclopedia' / (dom + '.json')
        if not fp.exists():
            continue
        d = W._load(dom) if hasattr(W, '_load') else json.loads(fp.read_text(encoding='utf-8'))
        dirty = False
        for a in d['articles']:
            if a.get('generated'):
                continue
            byid = {s['id']: s for s in screens}
            cur = set(by_art.get(a['id'], []))
            keep = [x for x in a.get('screens', []) if x in ids and RF.screen_ok(a, byid[x], curated=x in cur)[0]]
            want = list(by_art.get(a['id'], []))
            if not want and not keep:          # ENC_READER_FIX: no window-tour fallback; an overlap pick must still pass screen_ok
                aw = words(' '.join([a['title'], a['summary'], ' '.join(a.get('aliases', [])), a['domain']]))
                ranked = sorted(((len(aw & sw[i]), i) for i in sw), reverse=True)
                want = [i for n, i in ranked if n >= 2 and RF.screen_ok(a, byid[i])[0]][:2]
            new = list(dict.fromkeys(keep + want))[:3]
            if new != a.get('screens'):
                a['screens'] = new; dirty = True; changed += 1
        if dirty and not check:
            W._save(dom, d)
    print('screens attached/updated on %d lane C articles (%d screens available)' % (changed, len(screens)))


if __name__ == '__main__':
    main()
