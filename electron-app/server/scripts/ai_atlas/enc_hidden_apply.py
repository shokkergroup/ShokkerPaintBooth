"""Sweeper for hand-written Encyclopedia domain files (owner rule 2026-10-04: Easy mode is hidden, see enc_hidden_features.json).

    python scripts/ai_atlas/enc_hidden_apply.py            # structural cleanup (renames, hidden ids out of related / actions / covers / aliases) + report
    python scripts/ai_atlas/enc_hidden_apply.py --report   # report only, writes nothing

Structure it fixes by itself: ids that moved (RENAMES), `related` / `actions` / `covers` entries that point at a hidden article or record, aliases
that name the hidden feature. TEXT it does not rewrite on its own: every user-facing field that still names the feature is printed
(file | article | field | text) so a person rewrites the sentence. Generated pages (help_*, controls_*) are rebuilt by their generators instead.
"""
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import enc_hidden as H  # noqa: E402

ENC = HERE.parents[1] / 'data' / 'encyclopedia'
RENAMES = {'easy_mode.chat_mode': 'ai_copilot.chat_mode', 'easy_mode.offline_vs_ai': 'ai_copilot.offline_vs_ai',
           'easy_mode.edit_existing': 'ai_copilot.edit_existing', 'workflows.pro_chat_easy': 'workflows.pro_or_chat'}
TEXT_FIELDS = ['title', 'summary', 'what', 'when', 'how', 'tips', 'pitfalls', 'aliases']
only_report = '--report' in sys.argv


def hidden_ref(x):
    return H.is_hidden_article_id(x) or H.is_hidden_id(x) or x in ('easy_mode.easy_mode', 'easy_mode.screen_tour')


def walk_files():
    for p in sorted(ENC.glob('*.json')):
        if p.name.startswith('_') or p.name in ('manifest.json', 'graphics.json', 'figures.json'):
            continue
        yield p


changed, reports = 0, []
for p in walk_files():
    try:
        doc = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    if not isinstance(doc, dict) or not doc.get('articles'):
        continue
    dirty = False
    for a in doc['articles']:
        rel = [RENAMES.get(x, x) for x in a.get('related', [])]
        rel = [x for x in rel if not hidden_ref(x)]
        rel = list(dict.fromkeys(rel))
        if rel != a.get('related'):
            a['related'] = rel; dirty = True
        acts = [x for x in a.get('actions', []) if not hidden_ref(x.get('id', ''))]
        if acts != a.get('actions'):
            a['actions'] = acts; dirty = True
        cov = [x for x in a.get('covers', []) if not H.is_hidden_id(x)]
        if cov != a.get('covers'):
            a['covers'] = cov; dirty = True
        if a.get('aliases'):
            al = [x for x in a['aliases'] if not (H.mentions(x) or re.search(r'\beasy\b', x))]
            if al != a['aliases']:
                a['aliases'] = al; dirty = True
        if a.get('generated'):
            continue
        for f in TEXT_FIELDS:
            v = a.get(f)
            vals = v if isinstance(v, list) else [v]
            for t in vals:
                if isinstance(t, str) and H.mentions(t):
                    reports.append((p.name, a['id'], f, t))
        for c in a.get('controls', []):
            for k in ('label', 'range', 'default', 'effect'):
                if isinstance(c.get(k), str) and H.mentions(c[k]):
                    reports.append((p.name, a['id'], 'controls.' + k, c[k]))
    if dirty:
        changed += 1
        if not only_report:
            tmp = p.with_suffix('.json.tmp')
            tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            os.replace(tmp, p)
print('files changed (structure): %d%s' % (changed, ' (report only: nothing written)' if only_report else ''))
for r in reports:
    print('TEXT | %s | %s | %s | %s' % (r[0], r[1], r[2], r[3][:230]))
print('TEXT mentions left in hand-written files: %d' % len(reports))
