"""Scenario benchmark breakdown: mean judged relevance by FLAVOUR (the goal / class words of the scenario ask) and by PART, for the systems judged by gold_judge.py.
python scripts/ai_atlas/scen_by_flavour.py [adv_curated adv_ranked]      (run scenario_run.js + gold_judge.py first; NSCEN=360 for power)"""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')); G = os.path.join(ROOT, '_easy_claude_work', 'gold')
systems = sys.argv[1:] or ['adv_curated', 'adv_ranked']
data = {s: {x['ask']: x for x in json.load(open(os.path.join(G, 'judged_%s.json' % s), encoding='utf-8')) if x['scores']} for s in systems}
common = set.intersection(*[set(d) for d in data.values()])
FL = ['so it pops', 'to look premium', 'with a bit of shimmer', 'with deeper colour', 'for a retro look', 'for a stealth look', 'for a dirt late model', 'that looks aggressive']
def flavour(a):
    for f in FL:
        if f in a: return f
    m = re.search(r'put on [a-z ]+? (for a [a-z ]+|that [a-z ]+)$', a)
    return m.group(1) if m else 'plain'
def part(a):
    m = re.search(r'put on (the [a-z ]+?)(?: (?:to|so|with|for|that)\b|$)', a); return m.group(1) if m else '?'
for title, fn in (('FLAVOUR', flavour), ('PART', part)):
    agg = {}
    for a in common:
        k = fn(a); row = agg.setdefault(k, {'n': 0, **{s: 0.0 for s in systems}}); row['n'] += 1
        for s in systems: row[s] += sum(data[s][a]['scores']) / len(data[s][a]['scores'])
    print('\n' + title + ' (n common = %d)' % len(common))
    for k, row in sorted(agg.items(), key=lambda kv: -kv[1]['n']):
        print('  %-26s n=%3d  ' % (k, row['n']) + '  '.join('%s %.2f' % (s.replace('adv_', ''), row[s] / row['n']) for s in systems))
