#!/usr/bin/env python
"""Hidden-feature gate for every buyer-facing / AI-facing TEXT OUTPUT (owner rule 2026-10-04: Easy mode is hidden, nothing may talk about it).

The ONE list of hidden features is scripts/ai_atlas/enc_hidden_features.json (the same list the Encyclopedia generators use). This gate scans the
shipped outputs that enc_v2_test / enc_stale_refs_check never looked at:

  js/spb-self-help.js, js/spb-ai-knowledge.js, js/spb-support-answers.js         generated / hand-written helper data
  docs/ai_knowledge/*.md                                                         AI knowledge cards (generated app_map.md, 07_ui_map_generated.md, hand-written cards)
  mcp/ (server/tools.json, server/index.js, README.md), integrations/spb-mcp     MCP tool + manual text
  server_routes/ai_copilot_routes.py                                             copilot system prompts
  data/encyclopedia/**/*.json                                                    the Encyclopedia data (must stay at 0)
  scripts/ai_atlas/ui_map.json                                                   the generated UI map

SOURCE-ONLY files are not scanned raw, they are scanned AFTER the same filter the generators apply (enc_hidden.scrub_md): the raw file keeps the hidden
feature's how-tos so that un-hiding is "remove it from the JSON list and re-run the generators".
  docs/ai_knowledge/how_do_i.md

Exit 0 = clean, 1 = a hidden-feature name is still in a shipped output (each hit is printed as file:line text). Run:
  python scripts/ai_atlas/hidden_feature_check.py            (add -q to print only the verdict lines)
Also checks that electron-app/server/ copies of the same files are identical (two-copy rule).
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import enc_hidden as EH  # noqa: E402

FILES = ['js/spb-self-help.js', 'js/spb-ai-knowledge.js', 'js/spb-support-answers.js', 'server_routes/ai_copilot_routes.py',
         'scripts/ai_atlas/ui_map.json', 'mcp/README.md']
GLOBS = ['docs/ai_knowledge/*.md', 'mcp/server/*', 'integrations/spb-mcp/*.json', 'integrations/spb-mcp/*.md', 'integrations/spb-mcp/src/**/*',
         'integrations/spb-mcp/server/**/*', 'data/encyclopedia/*.json', 'data/encyclopedia/pages/*.json']
SOURCE_ONLY = ['docs/ai_knowledge/how_do_i.md']
TEXT_EXT = ('.js', '.json', '.md', '.py', '.txt', '.mjs', '.ts')
# JS / Python comments are developer text, not shipped to a buyer or the AI: ignore full-line comments in code files
_COMMENT = re.compile(r'^\s*(//|#|\*|/\*)')
MIRROR = ['js/spb-self-help.js', 'js/spb-ai-knowledge.js', 'server_routes/ai_copilot_routes.py']


def targets():
    out = []
    for f in FILES:
        if os.path.exists(os.path.join(ROOT, f)):
            out.append(f)
    for g in GLOBS:
        for p in glob.glob(os.path.join(ROOT, g), recursive=True):
            if os.path.isfile(p) and p.lower().endswith(TEXT_EXT) and 'node_modules' not in p and not p.endswith('.backup'):
                out.append(os.path.relpath(p, ROOT).replace('\\', '/'))
    seen, res = set(), []
    for f in out:
        if f not in seen and f not in SOURCE_ONLY:
            seen.add(f)
            res.append(f)
    return res


def scan_text(text, is_code):
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if is_code and _COMMENT.match(line):
            continue
        if EH.mentions(line):
            hits.append((n, re.sub(r'\s+', ' ', line.strip())[:160]))
    return hits


def scan_json(text):
    """JSON data: check string VALUES only; citation keys (source file paths such as js/spb-easy-mode.js:937, ids, covers) are not buyer text."""
    try:
        obj = json.loads(text)
    except ValueError:
        return scan_text(text, False)
    hits = []

    def walk(o, key, path):
        if isinstance(o, str):
            if key not in EH._SKIP_KEYS and EH.mentions(o):
                hits.append((path, re.sub(r'\s+', ' ', o)[:160]))
        elif isinstance(o, list):
            for i, x in enumerate(o):
                walk(x, key, '%s[%d]' % (path, i))
        elif isinstance(o, dict):
            for k, v in o.items():
                walk(v, k, path + '.' + str(k))
    walk(obj, None, '$')
    return hits


def main():
    quiet = '-q' in sys.argv
    bad = 0
    total = 0
    if not EH.HIDDEN:
        print('NOTE no hidden features listed in enc_hidden_features.json: nothing to check')
        return 0
    for rel in targets():
        text = open(os.path.join(ROOT, rel), encoding='utf-8', errors='replace').read()
        hits = scan_json(text) if rel.endswith('.json') else scan_text(text, rel.endswith(('.js', '.py')))
        total += 1
        if hits:
            bad += len(hits)
            print('FAIL %s: %d hit(s)' % (rel, len(hits)))
            if not quiet:
                for n, s in hits[:8]:
                    print('   %d: %s' % (n, s.encode('ascii', 'replace').decode()))
        elif not quiet:
            print('ok   %s: 0' % rel)
    for rel in SOURCE_ONLY:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        filtered = EH.scrub_md(open(p, encoding='utf-8').read().replace('\r\n', '\n'))
        hits = scan_text(filtered, False)
        total += 1
        if hits:
            bad += len(hits)
            print('FAIL %s (after generator filter): %d hit(s)' % (rel, len(hits)))
            for n, s in hits[:8]:
                print('   %d: %s' % (n, s.encode('ascii', 'replace').decode()))
        else:
            print('ok   %s: 0 after the generator filter (raw source keeps the hidden how-tos for un-hiding)' % rel)
    drift = []
    for rel in MIRROR:
        a, b = os.path.join(ROOT, rel), os.path.join(ROOT, 'electron-app', 'server', rel)
        if os.path.exists(a) and os.path.exists(b) and open(a, 'rb').read() != open(b, 'rb').read():
            drift.append(rel)
    for rel in drift:
        print('DRIFT electron-app/server/%s differs from the root copy (run node scripts/sync-runtime-copies.js --write)' % rel)
    print('RESULT %s: %d file(s) scanned for hidden features %s; %d hit(s); %d mirror drift' % (
        'FAIL' if (bad or drift) else 'PASS', total, ','.join(EH.HIDDEN), bad, len(drift)))
    return 1 if (bad or drift) else 0


if __name__ == '__main__':
    sys.exit(main())
