"""Score a retrieval SYSTEM against a HAND-LABELLED truth set (no AI judge).   2026-10-03 (the 400 asks + good / bad key lists come from the Codex L2 lane).
   python scripts/ai_atlas/truth_score.py [system ...]        systems: pipe_new rank pipe_old lexical cards  (default pipe_new rank)
   - runs scripts/ai_atlas/gold_run.js over the truth asks (ASKS env), then compares the top 6 keys with each ask's  good  and  bad  lists
   metrics: HIT = at least one good key in the top 6 | CLEAN = hit and no bad key | BAD = share of results that are on the ask's bad list | GOOD@6 = share of results that are good (good lists are NON-exhaustive: read it relatively)"""
import os, sys, json, subprocess, collections
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TRUTH = os.path.join(ROOT, '_codex_work', 'finish_intel', 'l2_truth_asks', 'truth_asks.json')
GOLD = os.path.join(ROOT, '_easy_claude_work', 'gold')
systems = sys.argv[1:] or ['pipe_new', 'rank']
truth = json.load(open(TRUTH, encoding='utf-8'))
tmp = os.path.join(GOLD, 'asks_truth.json')
json.dump([{'ask': t['ask'], 'cat': t['cat']} for t in truth], open(tmp, 'w', encoding='utf-8'), ensure_ascii=False)
env = dict(os.environ, ASKS=tmp, ASKTAG='truth')
subprocess.run(['node', os.path.join(ROOT, 'scripts', 'ai_atlas', 'gold_run.js')] + systems, env=env, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
for s in systems:
    res = json.load(open(os.path.join(GOLD, 'results_truth_%s.json' % s), encoding='utf-8'))
    by = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0])      # n, hit, clean, bad_n, good_n, total
    for t, r in zip(truth, res):
        keys = r['keys'][:6]; good = set(t.get('good') or []); bad = set(t.get('bad') or [])
        h = any(k in good for k in keys); b = sum(1 for k in keys if k in bad); g = sum(1 for k in keys if k in good)
        for tag in (t['cat'], 'ALL'):
            x = by[tag]; x[0] += 1; x[1] += h; x[2] += (h and b == 0); x[3] += b; x[4] += g; x[5] += len(keys)
    a = by['ALL']
    print('%-9s asks %d | HIT %.0f%% | CLEAN %.0f%% | BAD %.1f%% of results | GOOD@6 %.1f%%' % (s, a[0], 100 * a[1] / a[0], 100 * a[2] / a[0], 100 * a[3] / max(1, a[5]), 100 * a[4] / max(1, a[5])))
    print('   ' + '  '.join('%s hit %.0f/clean %.0f/bad %.0f' % (c[:9], 100 * v[1] / v[0], 100 * v[2] / v[0], 100 * v[3] / max(1, v[5])) for c, v in sorted(by.items()) if c != 'ALL'))
