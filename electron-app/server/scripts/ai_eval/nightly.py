"""HELPER V3 stage S9 (local half), 2026-10-06: the NIGHTLY runner (tier 1, Node, no app, no network).

    python scripts/ai_eval/nightly.py                 # run, compare with the last run, write the report, print ONE summary line
    python scripts/ai_eval/nightly.py --dry           # run + print, but do not write the report / state (no baseline change)
    python scripts/ai_eval/nightly.py --tag NAME      # grade_offline output tag (default "nightly": _runs/nightly_train.jsonl ...)

What it runs (from _easy_claude_work/eval/bank/, exactly the commands in bank/README.md):
    node grade_offline.js --split train,dev --tag nightly        (the tier-1 grader on train + dev)
    python run_regression.py                                      (the regression bank, tier 1)
It NEVER runs the sealed split: it never passes --orchestrator and refuses to start if a sealed flag ever appears in its own command line.

Output:
    stdout                                  ONE line:  NIGHTLY <date> OK|RED | train x/y | dev x/y | harm n (was m) | regression x/y (was x/y) | <verdict>
    _easy_claude_work/eval/nightly/<date>.md  the summary line + a markdown diff vs the previous run (totals, checks, per-class moves >= 3 points)
    _easy_claude_work/eval/nightly/runs.jsonl one machine record per run (append-only; the "last run" is the last line)
EXIT CODE: 0 ok / baseline; 1 = harm went up (train + dev harm flags + HARMFUL regression items) OR the regression pass count / rate dropped;
           2 = a runner failed (node / python error). A class drop of >= 3 points is listed in the report and flagged in the summary line but,
           per the architecture doc 3.5, only "harm up" and "regression down" turn the exit code red.

SCHEDULING (not scheduled here; owner decides). Examples:
  Windows Task Scheduler:  schtasks /Create /SC DAILY /ST 03:30 /TN "SPB helper nightly" /TR "python \\"C:\\DRIVE E BACKUP\\Shokker Paint Booth Gold to Platinum\\scripts\\ai_eval\\nightly.py\\""
  Claude scheduled task:   mcp scheduled-tasks create (cron "30 3 * * *"), prompt = run that command and, on a non-zero exit, open a row in the wiki Known Trouble Spots.
  Only the exit code and the one summary line matter: pipe stdout to a file if a scheduler wants a log.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BANK = os.path.join(ROOT, '_easy_claude_work', 'eval', 'bank')
OUTD = os.path.join(ROOT, '_easy_claude_work', 'eval', 'nightly')
CLASS_DROP = 3.0          # points; listed + flagged, not an exit-code trigger


def _run(cmd, label):
    joined = ' '.join(cmd).lower()
    if 'sealed' in joined or '--orchestrator' in joined:      # belt and braces: the nightly runner can never score the sealed split
        print('REFUSED: the nightly runner never runs the sealed split (%s)' % label)
        sys.exit(2)
    p = subprocess.run(cmd, cwd=BANK, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p


def parse_total(line):
    m = re.search(r'items (\d+)/(\d+) ([\d.]+)% \| turns (\d+)/(\d+) ([\d.]+)%(?: \| items with a harm flag (\d+))?', line)
    if not m:
        return None
    return {'items_ok': int(m.group(1)), 'items': int(m.group(2)), 'items_pct': float(m.group(3)), 'turns_ok': int(m.group(4)), 'turns': int(m.group(5)),
            'turns_pct': float(m.group(6)), 'harm': int(m.group(7) or 0)}


def parse_classes(line):
    """'A:finish 21/63 (33.3% t54.7% h2) | B:howto 51/54 (94.4% t94.4%)' -> {class: {ok, n, pct, harm}}"""
    out = {}
    for m in re.finditer(r'([AB]:[\w]+) (\d+)/(\d+) \(([\d.]+)% t[\d.]+%(?: h(\d+))?\)', line):
        out[m.group(1)] = {'ok': int(m.group(2)), 'n': int(m.group(3)), 'pct': float(m.group(4)), 'harm': int(m.group(5) or 0)}
    return out


def parse_checks(line):
    out = {}
    for m in re.finditer(r'(\w[\w-]*) (\d+)/(\d+) ([\d.]+)%', line.replace('CHECKS', '')):
        out[m.group(1)] = float(m.group(4))
    return out


def read_summary(tag, split):
    p = os.path.join(BANK, '_runs', '%s_%s.summary.txt' % (tag, split))
    if not os.path.exists(p):
        return None
    d = {'split': split}
    for ln in open(p, encoding='utf-8', errors='replace'):
        if ln.startswith('TOTAL'):
            d['total'] = parse_total(ln)
        elif ln.startswith('CHECKS'):
            d['checks'] = parse_checks(ln)
        elif ln.startswith('BY ACTION'):
            d['classes'] = parse_classes(ln)
    return d if d.get('total') else None


def last_run():
    p = os.path.join(OUTD, 'runs.jsonl')
    last = None
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8'):
            ln = ln.strip()
            if ln:
                try:
                    last = json.loads(ln)
                except Exception:
                    pass
    return last


def pct_cell(a, b, unit='%'):
    if a is None:
        return '%s%s' % (b, unit)
    d = b - a
    return '%s%s (%+.1f)' % (b, unit, d)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--tag', default='nightly')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args(argv)
    today = datetime.date.today().isoformat()
    now = datetime.datetime.now().isoformat(timespec='seconds')

    g = _run(['node', 'grade_offline.js', '--split', 'train,dev', '--tag', a.tag], 'grade_offline')
    if g.returncode not in (0, 1):
        print('NIGHTLY RUNNER ERROR (grade_offline.js exit %d): %s' % (g.returncode, (g.stderr or g.stdout)[-400:].replace('\n', ' ')))
        return 2
    r = _run([sys.executable, 'run_regression.py'], 'run_regression')
    if r.returncode not in (0, 1):
        print('NIGHTLY RUNNER ERROR (run_regression.py exit %d): %s' % (r.returncode, (r.stderr or r.stdout)[-400:].replace('\n', ' ')))
        return 2

    splits = {s: read_summary(a.tag, s) for s in ('train', 'dev')}
    if not all(splits.values()):
        print('NIGHTLY RUNNER ERROR: missing grade summaries in _runs/ for tag %s' % a.tag)
        return 2
    reg = {'ok': 0, 'n': 0, 'harm_fails': 0, 'fails': []}
    for ln in r.stdout.splitlines():
        m = re.match(r'REGRESSION (\d+)/(\d+) pass', ln)
        if m:
            reg['ok'], reg['n'] = int(m.group(1)), int(m.group(2))
        m = re.match(r'FAIL (\S+)( HARM)?', ln)
        if m:
            reg['fails'].append(m.group(1))
            reg['harm_fails'] += 1 if m.group(2) else 0
    if not reg['n']:
        print('NIGHTLY RUNNER ERROR: could not read the REGRESSION line')
        return 2
    harm_total = splits['train']['total']['harm'] + splits['dev']['total']['harm'] + reg['harm_fails']
    cur = {'ts': now, 'date': today, 'tag': a.tag, 'train': splits['train']['total'], 'dev': splits['dev']['total'],
           'regression': {'ok': reg['ok'], 'n': reg['n'], 'harm_fails': reg['harm_fails'], 'fails': reg['fails']},
           'harm_total': harm_total, 'classes': {s: splits[s].get('classes', {}) for s in splits}, 'checks': {s: splits[s].get('checks', {}) for s in splits}}
    prev = last_run()

    reasons = []
    if prev:
        if harm_total > prev.get('harm_total', 0):
            reasons.append('harm %d > %d' % (harm_total, prev.get('harm_total', 0)))
        pr = prev.get('regression') or {}
        if pr and (reg['ok'] < pr.get('ok', 0) or (pr.get('n') and reg['ok'] / reg['n'] < pr['ok'] / pr['n'] - 1e-9)):
            reasons.append('regression %d/%d < %d/%d' % (reg['ok'], reg['n'], pr.get('ok', 0), pr.get('n', 0)))
    class_drops = []
    if prev:
        for s in ('train', 'dev'):
            for k, v in (cur['classes'].get(s) or {}).items():
                pv = ((prev.get('classes') or {}).get(s) or {}).get(k)
                if pv and v['pct'] - pv['pct'] <= -CLASS_DROP:
                    class_drops.append('%s %s %.1f->%.1f' % (s, k, pv['pct'], v['pct']))
    red = bool(reasons)
    tr, dv = cur['train'], cur['dev']
    pv_harm = prev.get('harm_total') if prev else None
    pr = (prev or {}).get('regression') or {}
    verdict = ('RED: ' + '; '.join(reasons)) if red else ('baseline (no previous run)' if not prev else 'no harm increase, regression held')
    if class_drops:
        verdict += ' | class drops >= %g pts: %s' % (CLASS_DROP, ', '.join(class_drops[:4]) + (' ...' if len(class_drops) > 4 else ''))
    line = 'NIGHTLY %s %s | train %d/%d (%.1f%%) | dev %d/%d (%.1f%%) | harm %d (was %s) | regression %d/%d (was %s) | %s' % (
        today, 'RED' if red else 'OK', tr['items_ok'], tr['items'], tr['items_pct'], dv['items_ok'], dv['items'], dv['items_pct'], harm_total,
        pv_harm if pv_harm is not None else 'n/a', reg['ok'], reg['n'], ('%d/%d' % (pr['ok'], pr['n'])) if pr else 'n/a', verdict)

    md = ['# Helper nightly %s' % today, '', '`%s`' % line, '', 'Run at %s, tag `%s`, tier 1 (Node, no app). Sealed split: NOT run.' % (now, a.tag),
          'Previous run: %s' % (prev.get('ts') if prev else 'none (this run is the baseline)'), '',
          '## Totals', '', '| measure | previous | now |', '|---|---|---|']
    for s in ('train', 'dev'):
        c = cur[s]
        p0 = (prev or {}).get(s) or {}
        md.append('| %s items %% | %s | %s |' % (s, ('%.1f' % p0['items_pct']) if p0 else 'n/a', pct_cell(p0.get('items_pct'), c['items_pct'])))
        md.append('| %s turns %% | %s | %s |' % (s, ('%.1f' % p0['turns_pct']) if p0 else 'n/a', pct_cell(p0.get('turns_pct'), c['turns_pct'])))
        md.append('| %s harm flags | %s | %d |' % (s, p0.get('harm', 'n/a'), c['harm']))
    md.append('| regression pass | %s | %d/%d |' % (('%d/%d' % (pr['ok'], pr['n'])) if pr else 'n/a', reg['ok'], reg['n']))
    md.append('| regression HARMFUL fails | %s | %d |' % (pr.get('harm_fails', 'n/a') if pr else 'n/a', reg['harm_fails']))
    md.append('| **harm total** | %s | **%d** |' % (pv_harm if pv_harm is not None else 'n/a', harm_total))
    md += ['', '## Check rates (%)', '', '| split | check | previous | now |', '|---|---|---|---|']
    for s in ('train', 'dev'):
        for k, v in sorted((cur['checks'].get(s) or {}).items()):
            p0 = ((prev or {}).get('checks') or {}).get(s, {}).get(k)
            md.append('| %s | %s | %s | %s |' % (s, k, p0 if p0 is not None else 'n/a', pct_cell(p0, v)))
    md += ['', '## Per-class moves (items %, |change| >= 1 point)', '']
    moves = []
    for s in ('train', 'dev'):
        for k, v in sorted((cur['classes'].get(s) or {}).items()):
            pv = ((prev or {}).get('classes') or {}).get(s, {}).get(k)
            if pv is not None and abs(v['pct'] - pv['pct']) >= 1.0:
                moves.append('| %s | %s | %.1f | %.1f | %+.1f%s |' % (s, k, pv['pct'], v['pct'], v['pct'] - pv['pct'], '  **DROP**' if v['pct'] - pv['pct'] <= -CLASS_DROP else ''))
    md += (['| split | class | previous | now | change |', '|---|---|---|---|---|'] + moves) if moves else ['(none, or no previous run)']
    md += ['', '## Regression failures (%d)' % len(reg['fails']), '', ', '.join(reg['fails']) if reg['fails'] else '(none)', '']
    if red:
        md += ['## RED', '', '- ' + '\n- '.join(reasons), '', 'Open a row in the wiki Known Trouble Spots (harm up = build red, per HELPER_ARCHITECTURE_V3 3.4 / 3.5).', '']

    if not a.dry:
        os.makedirs(OUTD, exist_ok=True)
        with open(os.path.join(OUTD, today + '.md'), 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(md))
        with open(os.path.join(OUTD, 'runs.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(cur, ensure_ascii=False) + '\n')
    print(line)
    return 1 if red else 0


if __name__ == '__main__':
    sys.exit(main())
