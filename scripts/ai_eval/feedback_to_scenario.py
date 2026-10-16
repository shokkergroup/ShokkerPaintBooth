"""HELPER V3 stage S9 (local half), 2026-10-06: feedback.jsonl -> DRAFT bank scenarios for a human to review.

    python scripts/ai_eval/feedback_to_scenario.py            # draft every feedback record not drafted yet (append-only)
    python scripts/ai_eval/feedback_to_scenario.py --show     # one line per feedback record (admin view on the command line)
    python scripts/ai_eval/feedback_to_scenario.py --dry      # print the drafts, write nothing
    options: --in <feedback.jsonl>   --out <drafts.jsonl>   --names "Name1,Name2"   (extra user / customer names to blank)

IN : output/ai_logs/feedback.jsonl (+ rotated .1-.4), written by POST /api/ai/feedback (server_routes/ai_feedback_routes.py).
OUT: _easy_claude_work/eval/bank/drafts/feedback_drafts.jsonl, bank_A / bank_B item format (see bank/README.md), plus:
       status:"DRAFT", origin:"feedback", origin_id (the feedback record id), helper_did (what the helper believed it was doing),
       helper_reply, user_comment, disagrees_with_helper, review[] (what the reviewer must fix).
The drafted `expect` comes from the USER'S WORDS (part / colour / finish vocabulary), never from the helper's frame, because the user just
told us the frame was wrong. When the two disagree the draft says so. NOTHING is added to bank_A/bank_B/regression.jsonl here: a human or
agent reviews the draft, fixes `expect`, then appends it (and, once the helper is fixed, adds it to regression via seed_regression.py).
Everything is SCRUBBED on the way out (scrub()): file paths, user / customer names, emails, urls, digit runs (iRacing customer ids),
machine and drive names. Colours (#rrggbb) are kept. Nothing in this script touches the network.
"""
import argparse
import getpass
import hashlib
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEF_IN = os.path.join(ROOT, 'output', 'ai_logs', 'feedback.jsonl')
DEF_OUT = os.path.join(ROOT, '_easy_claude_work', 'eval', 'bank', 'drafts', 'feedback_drafts.jsonl')


# ------------------------------------------------------------------ scrubbing
def _own_names(extra=''):
    names = set()
    for v in (os.environ.get('USERNAME'), os.environ.get('USER'), os.environ.get('COMPUTERNAME')):
        if v:
            names.add(v)
    try:
        names.add(getpass.getuser())
    except Exception:
        pass
    try:
        names.add(os.path.basename(os.path.expanduser('~')))
    except Exception:
        pass
    names.update(['Ricky', 'Whittenburg', 'Shokker Group'])
    names.update(x.strip() for x in (extra or '').split(',') if x.strip())
    return sorted((n for n in names if len(n) >= 3), key=len, reverse=True)


# a Windows path may contain spaces and apostrophes ("C:\Users\Ricky's PC\..."): first a drive path that ends in a file name, then any space-free drive path
_PATH_FILE_RE = re.compile(r"[A-Za-z]:[\\/](?:[\w .,'()&~-]+[\\/])*[\w .,'()&~-]*\.\w{1,5}\b")
_PATH_RE = re.compile(r"[A-Za-z]:[\\/](?:[^\\/\"<>|\r\n]+[\\/])*[^\s\"<>|\\/]*|\\\\[^\s\"'<>|]+|/(?:Users|home)/[^\s\"'<>|]+")
_URL_RE = re.compile(r'\b(?:https?|file)://[^\s"\'<>]+', re.I)
_MAIL_RE = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
_HEX_RE = re.compile(r'#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b')
_CUST_RE = re.compile(r'(?i)\b(?:customer|cust|member|iracing)\s*(?:id|number|no\.?|#)?\s*[:=#]?\s*\d{3,}')
_DIGITS_RE = re.compile(r'\d{5,}')


def scrub(text, extra_names=''):
    """Blank paths, names, emails, urls, customer ids and long digit runs; keep #rrggbb colours."""
    s = str(text or '')
    keep = []

    def _hide(m):
        keep.append(m.group(0))
        return '\x00%d\x00' % (len(keep) - 1)
    s = _HEX_RE.sub(_hide, s)
    s = _URL_RE.sub('[link]', s)
    s = _MAIL_RE.sub('[email]', s)
    s = _PATH_RE.sub('[path]', _PATH_FILE_RE.sub('[path]', s))
    s = _CUST_RE.sub('[customer id]', s)
    s = _DIGITS_RE.sub('[number]', s)
    for n in _own_names(extra_names):
        s = re.sub(r'(?i)(?<![A-Za-z])' + re.escape(n) + r'(?![A-Za-z])', '[name]', s)
    return re.sub(r'\x00(\d+)\x00', lambda m: keep[int(m.group(1))], s)


# ------------------------------------------------------------------ vocabulary (the bank's own scope strings)
PARTS = [('left side', 'left side'), ('right side', 'right side'), ('left door', 'left door'), ('right door', 'right door'), ('doors', 'doors'), ('door', 'doors'),
         ('hood', 'hood'), ('bonnet', 'hood'), ('roof', 'roof'), ('top of the car', 'roof'), ('trunk', 'trunk'), ('boot', 'trunk'), ('bed', 'bed'), ('cab', 'cab'),
         ('front bumper', 'front bumper'), ('rear bumper', 'rear bumper'), ('back bumper', 'rear bumper'), ('bumpers', 'bumpers'), ('spoiler', 'spoiler'),
         ('rear wing', 'rear wing'), ('wing', 'wing'), ('mirrors', 'mirrors'), ('mirror', 'mirrors'), ('nose', 'nose'), ('fenders', 'fenders'), ('trim', 'trim')]
ELEMENTS = [('numbers', 'numbers'), ('number', 'numbers'), ('sponsors', 'sponsors'), ('sponsor', 'sponsors'), ('logos', 'logos'), ('logo', 'logos'),
            ('stripes', 'stripes'), ('stripe', 'stripes')]
COLOURS = ['red', 'orange', 'yellow', 'gold', 'green', 'teal', 'blue', 'navy', 'purple', 'pink', 'brown', 'black', 'white', 'silver', 'grey', 'gray']
FINISHES = [('chrome', 'chrome'), ('matte', 'matte'), ('satin', 'satin'), ('gloss', 'gloss'), ('candy', 'candy'), ('metallic', 'metallic'), ('pearl', 'pearl'),
            ('carbon', 'carbon'), ('brushed', 'brushed'), ('flame', 'flames'), ('camo', 'camo')]
Q_RE = re.compile(r"^\s*(?:how|what|why|where|when|which|who|can i|can you|do you|does|is |are |should|could)\b|\?\s*$", re.I)
ANAPHORA = re.compile(r"\b(?:it|that|those|them|this|too|also|same|again|instead|undo|back|previous|before)\b", re.I)
SPEC_RE = re.compile(r"\b(?:only the (?:shine|metal|finish)|keep the colou?rs?|don'?t change the colou?r|same colou?r)\b", re.I)
EDIT_VERB = re.compile(r"\b(?:change|make|paint|put|add|recolou?r|turn|set|colou?r)\b", re.I)


def _find(text, vocab):
    t = ' ' + text.lower() + ' '
    out = []
    for word, norm in vocab:
        if re.search(r'(?<![a-z])' + re.escape(word) + r'(?![a-z])', t) and norm not in out:
            out.append(norm)
    return out


def _drop_subsumed(parts):
    drop = set()
    if 'left side' in parts or 'right side' in parts or 'left door' in parts or 'right door' in parts:
        drop.add('doors')
    if 'front bumper' in parts or 'rear bumper' in parts:
        drop.add('bumpers')
    if 'rear wing' in parts:
        drop.add('wing')
    return [p for p in parts if p not in drop]


def draft_expect(text, ref):
    """A bank-format expect[] turn drafted from the user's words alone."""
    parts = _drop_subsumed(_find(text, PARTS))
    elems = _find(text, ELEMENTS)
    low = text.lower()
    cols = [c for c in COLOURS if re.search(r'(?<![a-z])' + c + r'(?![a-z])', low)]
    fins = _find(text, FINISHES)
    m = _HEX_RE.search(text)
    hx = m.group(0) if m else None
    if re.search(r'(?i)\bundo\b|\btake (?:that|it) back\b|\brevert\b', text):
        return {'do': 'nothing', 'must_change': ['last change'], 'must_not_change': ['every part or layer not named'], 'colour': None, 'finish_class': None,
                'spec_only': False, 'refers_to_turn': ref, 'note': 'DRAFT: an undo request; check the history target.'}
    if Q_RE.search(text) and not (parts and (cols or fins or hx)):
        return {'do': 'answer', 'answer_must_cover': [], 'gold_ids': [], 'must_not': '', 'refers_to_turn': ref,
                'note': 'DRAFT: reads as a question; reviewer fills answer_must_cover + gold_ids.'}
    edited = bool(EDIT_VERB.search(text))
    changed_elems = [e for e in elems if edited and re.search(r'(?i)(?:change|make|paint|recolou?r|turn|add|put)\s+(?:\w+\s+)?(?:the\s+)?(?:\w+\s+)?' + e[:-1], text)]
    keep = [e for e in ('numbers', 'sponsors') if e not in changed_elems]
    mc = parts + [e for e in changed_elems if e not in parts]
    if not mc and (cols or hx or fins):
        mc = ['body base colour']
    mn = list(dict.fromkeys(keep + ['every part or layer not named']))
    return {'do': 'change' if (mc or cols or fins or hx) else 'ask', 'must_change': mc, 'must_not_change': mn,
            'colour': hx or (cols[0] if cols else None), 'finish_class': fins[0] if fins else None,
            'spec_only': bool(SPEC_RE.search(text)), 'refers_to_turn': ref,
            'note': "DRAFT from the user's words; the helper got this wrong (see helper_did). Reviewer confirms every field."}


def _frame_summary(rec):
    fr = rec.get('frame') or {}
    ops = []
    for o in fr.get('ops') or []:
        t = (o.get('target') or {})
        look = o.get('look') or {}
        col = (look.get('colour') or {})
        ops.append({'verb': o.get('verb'), 'target': t.get('parts') or t.get('element') or t.get('kind'), 'colour': col.get('word') or col.get('hex'),
                    'finish': (look.get('finish') or {}).get('key')})
    return {'act': fr.get('act'), 'ops': ops[:6], 'verify': (rec.get('verify') or fr.get('verify') or {}).get('verdict')}


def _helper_parts(summary):
    out = set()
    for o in summary.get('ops') or []:
        t = o.get('target')
        for x in (t if isinstance(t, list) else [t]):
            if x:
                out.add(str(x))
    return out


def draft_item(rec, extra_names=''):
    def sc(s):
        return scrub(s, extra_names)
    convo = [m for m in (rec.get('convo') or []) if isinstance(m, dict) and m.get('role') == 'user' and m.get('text')]
    texts = [sc(m['text']) for m in convo][-4:]
    last = sc(rec.get('text') or '')
    if not texts or texts[-1].strip() != last.strip():
        texts.append(last)
    texts = [t for t in texts if t.strip() and not t.lstrip().startswith('▶')][-4:] or texts[-1:]          # drop the synthetic "Run: ..." turn texts
    expects = []
    for i, t in enumerate(texts):
        ref = i - 1 if (i > 0 and ANAPHORA.search(t)) else None
        expects.append(draft_expect(t, ref))
    summary = _frame_summary(rec)
    want = set(expects[-1].get('must_change') or [])
    did = _helper_parts(summary)
    disagree = bool(did and want and not (want & did))
    is_b = expects[-1].get('do') == 'answer' and len(texts) == 1
    review = ["confirm the drafted expect for EVERY turn (it comes from the user's words, not from the helper)",
              'write harmful_if (what would hurt the buyer if the helper repeated this mistake)']
    if is_b:
        review.append('fill answer_must_cover + gold_ids (encyclopedia ids)')
    if rec.get('comment'):
        review.append('read user_comment: it may say what was wrong')
    if not rec.get('matched_turn', True):
        review.append('the turn log had no matching record: frame / verify are missing')
    oid = str(rec.get('id') or '')
    h = hashlib.sha1(oid.encode('utf-8')).hexdigest()[:6]
    return {'id': ('FB-B-' if is_b else 'FB-A-') + h, 'persona': 'feedback', 'kind': 'howto' if is_b else ('convo' if len(texts) > 1 else 'edit'),
            'turns': texts, 'expect': expects, 'harmful_if': 'DRAFT: reviewer writes this (the user reported "did not do what I asked").',
            'bank': 'B' if is_b else 'A', 'origin': 'feedback', 'origin_id': oid, 'status': 'DRAFT', 'needs_review': True,
            'helper_did': summary, 'helper_reply': sc(rec.get('reply') or '')[:400], 'user_comment': sc(rec.get('comment') or ''),
            'undo_state': rec.get('undo') or None, 'disagrees_with_helper': disagree, 'review': review}


def read_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    for ln in open(path, encoding='utf-8', errors='replace'):
        ln = ln.strip()
        if ln:
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    return out


def read_all_feedback(path):
    recs = []
    for i in range(4, 0, -1):
        recs += read_jsonl('%s.%d' % (path, i))
    return recs + read_jsonl(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--in', dest='inp', default=DEF_IN)
    ap.add_argument('--out', default=DEF_OUT)
    ap.add_argument('--names', default='')
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args(argv)
    recs = read_all_feedback(a.inp)
    if a.show:
        for r in recs:
            s = _frame_summary(r)
            print('%s %s seq=%s undo=%s matched=%s | %s | helper: %s %s | %s' % (r.get('id'), r.get('ts'), (r.get('turn_id') or {}).get('seq'), (r.get('undo') or {}).get('done'),
                  r.get('matched_turn'), scrub(r.get('text'), a.names)[:70], s.get('act'), json.dumps(s.get('ops'))[:80], scrub(r.get('comment') or '', a.names)[:60]))
        print('FEEDBACK %d record(s)' % len(recs))
        return 0
    have = {d.get('origin_id') for d in read_jsonl(a.out)}
    new = [draft_item(r, a.names) for r in recs if r.get('id') and r.get('id') not in have]
    if a.dry:
        for d in new:
            print(json.dumps(d, ensure_ascii=False))
    elif new:
        os.makedirs(os.path.dirname(a.out), exist_ok=True)
        with open(a.out, 'a', encoding='utf-8') as f:
            for d in new:
                f.write(json.dumps(d, ensure_ascii=False) + '\n')
    print('FEEDBACK DRAFTS: %d feedback record(s), %d already drafted, %d new draft(s)%s -> %s'
          % (len(recs), len(have & {r.get('id') for r in recs}), len(new), ' (dry)' if a.dry else '', os.path.relpath(a.out, ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
