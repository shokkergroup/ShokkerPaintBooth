"""Validate _atlas_deep/out/*.jsonl against the plan.  python scripts/ai_atlas/deep_validate.py [shard_001 ...] [--summary]
Prints 'OK <shard> <n> units' or 'FAIL <shard> <line> <reason>'. Last line per unit wins (duplicates are reported as WARN, not failures)."""
import os, sys, json, glob, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
D = os.path.join(ROOT, '_atlas_deep')
REQ = ['u', 'rep', 'look_close', 'look_far', 'light', 'stack', 'not', 'asks', 'avoid_asks', 'placement', 'with_numbers', 'variants_note', 'qa_fix', 'confidence']
STACK = {'base': ['patterns_over', 'patterns_avoid', 'spec_over'], 'monolithic': ['patterns_over', 'patterns_avoid', 'spec_over'],
         'pattern': ['reads_over', 'needs_contrast', 'crushed_pct', 'intensity'], 'spec': ['on_matte', 'on_metallic', 'on_chrome', 'visibility', 'crushed_pct']}


def plan_units():
    U = {}
    for p in sorted(glob.glob(os.path.join(D, 'shards', 'shard_*.json'))):
        for u in json.load(open(p, encoding='utf-8'))['units']:
            U[u['u']] = u
    return U


def wc(s):
    return len(str(s).split())


def check(o, U):
    for k in REQ:
        if k not in o:
            return 'missing key ' + k
    u = U.get(o['u'])
    if not u:
        return 'unit not in plan: %s' % o['u']
    if o['rep'] != u['rep']:
        return 'rep mismatch'
    if not isinstance(o['confidence'], int) or isinstance(o['confidence'], bool) or not 1 <= o['confidence'] <= 5:
        return 'confidence not int 1-5'
    for k in ('look_close', 'look_far', 'light', 'with_numbers'):
        if not isinstance(o[k], str) or not o[k].strip():
            return k + ' empty/not string'
    if wc(o['look_close']) > 60:
        return 'look_close %d words > 60' % wc(o['look_close'])
    if wc(o['look_far']) > 40:
        return 'look_far > 40 words'
    a = o['asks']
    if not isinstance(a, list) or not 8 <= len(a) <= 12:
        return 'asks must be 8-12 items (got %s)' % (len(a) if isinstance(a, list) else a)
    for x in a:
        if not isinstance(x, str) or not x.strip() or wc(x) > 14:
            return 'ask empty or > 14 words: %s' % str(x)[:40]
    if len(set(x.lower() for x in a)) != len(a):
        return 'duplicate asks'
    if not isinstance(o['avoid_asks'], list) or not 3 <= len(o['avoid_asks']) <= 5:
        return 'avoid_asks must be 3-5 items'
    if not isinstance(o['not'], list) or not 2 <= len(o['not']) <= 3:
        return 'not must be 2-3 items'
    if not isinstance(o['placement'], list) or not o['placement']:
        return 'placement empty'
    st = o['stack']
    if not isinstance(st, dict):
        return 'stack not object'
    for k in STACK[u['type']]:
        if k not in st:
            return 'stack missing ' + k
    if len(u['members']) > 1 and not str(o['variants_note']).strip():
        return 'family needs variants_note'
    if u.get('qa') and not str(o['qa_fix']).strip():
        return 'flagged unit needs qa_fix'
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    U = plan_units()
    files = sorted(glob.glob(os.path.join(D, 'out', '*.jsonl')))
    if args:
        files = [f for f in files if os.path.splitext(os.path.basename(f))[0] in args]
    good = {}
    bad = 0
    for f in files:
        sh = os.path.splitext(os.path.basename(f))[0]
        fails, seen = 0, set()
        for i, l in enumerate(open(f, encoding='utf-8'), 1):
            if not l.strip():
                continue
            try:
                o = json.loads(l)
            except Exception as e:
                print('FAIL %s %d bad JSON: %s' % (sh, i, str(e)[:60])); fails += 1; continue
            r = check(o, U) if isinstance(o, dict) else 'not an object'
            if r:
                print('FAIL %s %d %s' % (sh, i, r)); fails += 1; continue
            if o['u'] in seen:
                print('WARN %s %d duplicate %s (last wins)' % (sh, i, o['u']))
            seen.add(o['u']); good[o['u']] = o
        if not fails:
            print('OK %s %d units' % (sh, len(seen)))
        bad += fails
    if '--summary' in sys.argv:
        tot, done = collections.Counter(), collections.Counter()
        for u in U.values():
            tot[u['type']] += 1
            done[u['type']] += u['u'] in good
        for t in tot:
            print('%-10s %d / %d' % (t, done[t], tot[t]))
        print('TOTAL %d / %d' % (sum(done.values()), sum(tot.values())))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
