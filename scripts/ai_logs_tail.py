"""Print the AI copilot request log, one line per turn (newest last).

HELPER_V2 fix pass 5 2026-10-05 owner: keep improving the Offline Helper -- FINAL 5a owner MANDATE:
"anything I type into the AI helper boxes gets logged somewhere at least temporarily where you can pull
the chat logs and SEE what happened". The log is written by server_routes/ai_copilot_routes.py
(/api/ai/turn-log from the page, /api/ai/chat for every online model call) to
output/ai_logs/copilot_turns.jsonl (5 MB rotation, .1 .. .4 kept). Local only.

    python scripts/ai_logs_tail.py            # last 20 records
    python scripts/ai_logs_tail.py -n 50
    python scripts/ai_logs_tail.py --full 3   # the last 3 records as full JSON
    python scripts/ai_logs_tail.py --dir <folder>
    python scripts/ai_logs_tail.py --live      # only the live server (port 59876); --test = only the test server (59879)
    python scripts/ai_logs_tail.py --port N    # only records that came in on port N

Every record carries 'port' (the server it came in on) and 'src' (enter / send / chip / run / askai from the page, model for /api/ai/chat).
Records written before 2026-10-05 01:40 have no port (shown as '?', kept by --live/--test filters only with --port 0).
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def records(d):
    files = [os.path.join(d, 'copilot_turns.jsonl.%d' % i) for i in range(4, 0, -1)] + [os.path.join(d, 'copilot_turns.jsonl')]
    for f in files:
        if not os.path.exists(f):
            continue
        with open(f, encoding='utf-8', errors='replace') as fh:
            for ln in fh:
                ln = ln.strip()
                if ln:
                    try:
                        yield json.loads(ln)
                    except Exception:
                        pass


def one(r):
    ts = str(r.get('ts', ''))[5:19].replace('T', ' ') + ' :' + str(r.get('port') or '?')
    k = r.get('kind')
    if k in ('chat', 'chat_fail'):
        tools = ','.join(t.get('name') or '?' for t in (r.get('tool_calls') or []))
        return '%s  MODEL %-9s %s | asked: %s | %s%s' % (ts, k, r.get('model', ''), (r.get('user') or '')[:90].replace('\n', ' '),
                                                        ('tools: ' + tools + ' ') if tools else '', ('reply: ' + (r.get('reply') or '')[:80].replace('\n', ' ')) if r.get('reply') else ('$%.4f' % (r.get('cost') or 0)))
    off = r.get('offline') or {}
    b = r.get('builder') or {}
    z = r.get('zones_changed') or []
    zs = '; '.join('%s %s%s%s' % (x.get('change'), x.get('name', '')[:40], (' [' + str(x.get('layers'))[:40] + ']') if x.get('layers') else '', (' ' + str(x.get('base'))) if x.get('base') else '') for x in z[:3]) + (' +%d' % (len(z) - 3) if len(z) > 3 else '')
    last_ai = next((m.get('text') for m in reversed(r.get('replies') or []) if m.get('role') == 'ai'), '') or ''
    return '%s  TURN  %-5s %-7s %-22s | %s | %s%s | zones: %s | reply: %s' % (
        ts, r.get('src', ''), r.get('mode', ''), (r.get('path') or '')[:22], (r.get('text') or '')[:90].replace('\n', ' '),
        (off.get('cls') or '-') + '/' + str(off.get('via') or off.get('pass') or '-'),
        (' steps %s open %s' % (b.get('steps'), b.get('open'))) if b else '', zs or 'none', last_ai[:90].replace('\n', ' '))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-n', type=int, default=20)
    ap.add_argument('--full', type=int, default=0)
    ap.add_argument('--live', action='store_true', help='only port 59876')
    ap.add_argument('--test', action='store_true', help='only port 59879')
    ap.add_argument('--port', type=int, default=None)
    ap.add_argument('--dir', default=os.environ.get('SPB_AI_LOG_DIR') or os.path.join(ROOT, 'output', 'ai_logs'))
    a = ap.parse_args()
    R = list(records(a.dir))
    want = a.port if a.port is not None else (59876 if a.live else (59879 if a.test else None))
    if want is not None:
        R = [r for r in R if (r.get('port') or 0) == want]
    if not R:
        print('no records' + (' for port %s' % want if want is not None else '') + ' in', a.dir)
        return
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    if a.full:
        for r in R[-a.full:]:
            print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    for r in R[-a.n:]:
        print(one(r))


if __name__ == '__main__':
    main()
