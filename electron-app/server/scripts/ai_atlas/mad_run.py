"""MSR-RUN wrapper: score every batch of mad_asks.jsonl, publish the miss list, re-run in rounds.
   python scripts/ai_atlas/mad_run.py [--once] [--round-min 15] [--stop 17:40]
Round 1 of a batch = first time it is seen. Every --round-min minutes ALL batches seen so far are re-run as round N (+ the B1 200 as mad_round<N>).
Outputs (_easy_claude_work/eval/): mad_misses.jsonl (append-only), mad_scoreboard.json (atomic), mad_state.json (resume), mad_r*.jsonl/_score.json; report docs/handoff_reports/MSR_RUN.md.
A pass = every applicable metric == 1.0 on that path ('any' = best of offline/tool per metric, as in intricate_score)."""
import json, os, sys, subprocess, time, datetime, importlib.util
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
EV = os.environ.get('MAD_EV') or os.path.join(ROOT, '_easy_claude_work', 'eval'); ASKS = os.environ.get('MAD_ASKS') or os.path.join(HERE, 'mad_asks.jsonl')
MISS = os.path.join(EV, 'mad_misses.jsonl'); SCORE = os.path.join(EV, 'mad_scoreboard.json'); STATE = os.path.join(EV, 'mad_state.json')
REPORT = os.environ.get('MAD_REPORT') or os.path.join(ROOT, 'docs', 'handoff_reports', 'MSR_RUN.md')
def opt(n, d): return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d  # (read before argv is replaced below)
ROUND_MIN = float(opt('--round-min', 15)); STOP = opt('--stop', '17:40')
METRICS = ['base_hit', 'pattern_hit', 'spec_hit', 'stack_shape', 'scale_hit', 'parts_hit', 'must_not_ok', 'askback_ok']

ARGV = list(sys.argv); sys.argv = ['intricate_score.py', 'x']
os.makedirs(EV, exist_ok=True)
spec = importlib.util.spec_from_file_location('iscore', os.path.join(HERE, 'intricate_score.py')); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S); S.EV = EV

def atomic(path, text):
    tmp = path + '.tmp'
    open(tmp, 'w', encoding='utf-8').write(text)
    for _ in range(5):
        try: os.replace(tmp, path); return
        except OSError: time.sleep(0.5)
def log(line):
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    if not os.path.exists(REPORT): open(REPORT, 'w', encoding='utf-8').write('# MSR-RUN - mad scientist scoring log\n\nPass = every applicable metric 1.0 on that path (any = best of offline/tool per metric). Misses: `_easy_claude_work/eval/mad_misses.jsonl`; scores: `mad_scoreboard.json`.\n\n')
    open(REPORT, 'a', encoding='utf-8').write(line + '\n'); print(line, flush=True)
def load_asks():
    if not os.path.exists(ASKS): return []
    out = []
    for l in open(ASKS, encoding='utf-8').read().splitlines():
        l = l.strip()
        if l:
            try: out.append(json.loads(l))
            except Exception: pass     # half-written last line
    return out
def run_node(tag, asks_file=None):
    env = dict(os.environ); env.pop('ASKS', None); env.pop('SINCE', None)
    if asks_file: env['ASKS'] = asks_file
    out = os.path.join(EV, 'intricate_%s.jsonl' % tag); env['MSR_EV'] = EV
    if os.path.exists(out): os.remove(out)
    r = subprocess.run(['node', os.path.join(HERE, 'intricate_run.js'), tag], cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    if r.returncode: raise RuntimeError(' | '.join(x for x in (r.stderr or r.stdout).splitlines() if x.strip() and not x.startswith('    at'))[:300])
def pass_of(m): return all(m[k] == 1.0 for k in METRICS if m.get(k) is not None)
def fails_of(m): return [k for k in METRICS if m.get(k) is not None and m[k] < 1.0]
def brief(rec, p):
    d = rec[p]; return {'keys': [i['key'] for i in d.get('items', [])][:6], 'kinds': d.get('layerKinds', []), 'reply': (d.get('text') or '')[:120]}

def score_round(rnd, batches_filter, asks_all, state, tagname):
    """run node over asks of the given batches, return per-ask results"""
    sel = [a for a in asks_all if a.get('batch') in batches_filter]
    f = os.path.join(EV, 'mad_in_%s.jsonl' % tagname)
    atomic(f, ''.join(json.dumps(a, ensure_ascii=False) + '\n' for a in sel))
    run_node(tagname, f)
    S.ASKS = f; S.SINCE = None
    sc = S.build(tagname)
    json.dump(sc, open(os.path.join(EV, 'intricate_%s_score.json' % tagname), 'w', encoding='utf-8'), ensure_ascii=False)
    rows = {}
    for l in open(os.path.join(EV, 'intricate_%s.jsonl' % tagname), encoding='utf-8'):
        if l.strip(): r = json.loads(l); rows[r['id']] = r
    amap = {a['id']: a for a in sel}; res = {}
    for p in sc['per_ask']:
        a = amap[p['id']]
        res[p['id']] = dict(batch=a.get('batch'), cls=p['cls'], ask=p['ask'], rec=rows[p['id']],
            pass_={x: pass_of(p[x]) for x in ('offline', 'tool', 'any')}, fails=fails_of(p['any']), comp={x: p[x]['composite'] for x in ('offline', 'tool', 'any')})
    return res

def summarize(res):
    def agg(items):
        n = len(items)
        if not n: return None
        o = {'n': n}
        for x in ('offline', 'tool', 'any'):
            o[x + '_pass'] = round(sum(1 for r in items if r['pass_'][x]) / n, 4)
            o[x + '_composite'] = round(sum(r['comp'][x] or 0 for r in items) / n, 4)
        return o
    vals = list(res.values())
    return dict(overall=agg(vals), by_class={c: agg([r for r in vals if r['cls'] == c]) for c in sorted(set(r['cls'] for r in vals))},
                by_batch={str(b): agg([r for r in vals if r['batch'] == b]) for b in sorted(set(r['batch'] for r in vals), key=lambda x: (x is None, x))})

def append_misses(res, rnd, prev_pass):
    n = reg = 0
    with open(MISS, 'a', encoding='utf-8') as fh:
        for i, r in res.items():
            if r['pass_']['any']: continue
            line = dict(id=i, batch=r['batch'], ask=r['ask'], **{'class': r['cls']}, failed=r['fails'],
                        got={'offline': brief(r['rec'], 'offline'), 'tool': brief(r['rec'], 'tool')}, round=rnd)
            if prev_pass and prev_pass.get(i):
                line['regression'] = True; reg += 1
            fh.write(json.dumps(line, ensure_ascii=False) + '\n'); n += 1
    return n, reg

def main():
    once = '--once' in ARGV; R1 = {}
    state = json.load(open(STATE, encoding='utf-8')) if os.path.exists(STATE) else dict(rounds={}, round_batches={}, last_round_ts=0, cur_round=1, first_seen={}, b1={})
    sb = json.load(open(SCORE, encoding='utf-8')) if os.path.exists(SCORE) else dict(rounds={}, batches={}, b1={}, flips={}, never_passed=[])
    hh, mm = map(int, STOP.split(':'))
    def stopped(): n = datetime.datetime.now(); return (n.hour, n.minute) >= (hh, mm)
    def save():
        atomic(STATE, json.dumps(state)); atomic(SCORE, json.dumps(sb, ensure_ascii=False, indent=1))
    if '1' not in sb['b1']:
        try:
            run_node('mad_round1'); S.ASKS = None; S.SINCE = None; b1 = S.build('mad_round1')
            sb['b1']['1'] = dict(composite_any=b1['overall']['composite_any'], composite_offline=b1['overall']['composite_offline'], composite_tool=b1['overall']['composite_tool'])
            log('- %s B1 200 round 1 composite: any %.3f offline %.3f tool %.3f' % (datetime.datetime.now().strftime('%H:%M'), *[b1['overall'][k] for k in ('composite_any', 'composite_offline', 'composite_tool')])); save()
        except Exception as e: log('- B1 round1 FAILED: %s' % e)
    while not stopped():
        asks = load_asks(); batches = sorted(set(a.get('batch') for a in asks if a.get('batch') is not None))
        new = [b for b in batches if str(b) not in state['first_seen']]
        # ---- round 1 of every new batch (recorded into the round that is current: cur_round; first scoring of a batch counts as its round 1)
        for b in new:
            try: res = score_round(1, {b}, asks, state, 'mad_b%s_r1' % b)
            except Exception as e: log('- batch %s FAILED to score: %s' % (b, e)); continue
            state['first_seen'][str(b)] = time.time()
            nm, _ = append_misses(res, 1, None)
            state['rounds'].setdefault('1', {}).update({i: r['pass_']['any'] for i, r in res.items()})
            state.setdefault('pass_detail', {}).setdefault('1', {}).update({i: r['pass_'] for i, r in res.items()})
            state['round_batches'].setdefault('1', [])
            if b not in state['round_batches']['1']: state['round_batches']['1'].append(b)
            sm = summarize(res); sb['batches'][str(b)] = dict(round1=sm); R1.update(res); sb['rounds']['1'] = summarize(R1)
            if not state['last_round_ts']: state['last_round_ts'] = time.time()
            log('- %s batch %s round 1: n=%d any-pass %.3f offline %.3f tool %.3f composite(any) %.3f; %d misses appended' % (datetime.datetime.now().strftime('%H:%M'), b, sm['overall']['n'], sm['overall']['any_pass'], sm['overall']['offline_pass'], sm['overall']['tool_pass'], sm['overall']['any_composite'], nm))
            save()
        # ---- a fresh full round
        due = state['rounds'] and (time.time() - state['last_round_ts'] >= ROUND_MIN * 60)
        if batches and due:
            rnd = state['cur_round'] + 1
            try:
                res = score_round(rnd, set(batches), asks, state, 'mad_r%d' % rnd)
                run_node('mad_round%d' % rnd); S.ASKS = None; S.SINCE = None; b1 = S.build('mad_round%d' % rnd)
                json.dump(b1, open(os.path.join(EV, 'intricate_mad_round%d_score.json' % rnd), 'w', encoding='utf-8'), ensure_ascii=False)
                prev = state['rounds'].get(str(rnd - 1), {}); cur = {i: r['pass_']['any'] for i, r in res.items()}
                flips_bad = [i for i in cur if prev.get(i) and not cur[i]]; flips_good = [i for i in cur if prev.get(i) is False and cur[i]]
                nm, nreg = append_misses(res, rnd, prev)
                state['rounds'][str(rnd)] = cur; state.setdefault('pass_detail', {})[str(rnd)] = {i: r['pass_'] for i, r in res.items()}
                state['round_batches'][str(rnd)] = batches
                sm = summarize(res); sm['batches_scored'] = batches
                sb['rounds'][str(rnd)] = sm
                sb['b1'][str(rnd)] = dict(composite_any=b1['overall']['composite_any'], composite_offline=b1['overall']['composite_offline'], composite_tool=b1['overall']['composite_tool'])
                sb['flips'][str(rnd)] = dict(regressed=flips_bad, fixed=len(flips_good))
                for b in batches: sb['batches'].setdefault(str(b), {}).setdefault('rounds', {})[str(rnd)] = sm['by_batch'].get(str(b))
                state['cur_round'] = rnd; state['last_round_ts'] = time.time()
                everpass = set()
                for rr in state['rounds'].values(): everpass |= {i for i, v in rr.items() if v}
                sb['never_passed'] = sorted(i for i in cur if i not in everpass)
                log('- %s ROUND %d (%d asks, %d batches): any-pass %.3f offline %.3f tool %.3f | B1 composite any %.3f (off %.3f tool %.3f) | fixed %d, REGRESSIONS %d%s' % (datetime.datetime.now().strftime('%H:%M'), rnd, sm['overall']['n'], len(batches), sm['overall']['any_pass'], sm['overall']['offline_pass'], sm['overall']['tool_pass'], b1['overall']['composite_any'], b1['overall']['composite_offline'], b1['overall']['composite_tool'], len(flips_good), len(flips_bad), (' -> ' + ', '.join(flips_bad[:30])) if flips_bad else ''))
                if flips_bad: log('  **REGRESSION** ids: ' + ', '.join(flips_bad))
                save()
            except Exception as e: log('- round %d FAILED: %s' % (rnd, e))
        if once: break
        time.sleep(30)
    sb['stopped'] = datetime.datetime.now().isoformat(timespec='seconds'); save()

if __name__ == '__main__': main()
