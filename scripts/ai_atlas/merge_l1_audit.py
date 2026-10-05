"""Merge an independent (Codex) card audit into the card pipeline:  flagged cards (verdict fix / bad) get their audit issues written as QA hints, their old
cards are dropped from cards.jsonl (backup kept) so annotate_cards.py re-writes just those, with the hint appended to the item's line.
   python scripts/ai_atlas/merge_l1_audit.py <audit.jsonl> [--dry]
   python scripts/ai_atlas/annotate_cards.py --workers 3 --cap 0.5        # re-annotate the dropped ones
   python scripts/ai_atlas/build_cards_js.py"""
import os, sys, json, shutil
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, '_atlas_cards')
audit = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
flag = [r for r in audit if r.get('verdict') in ('fix', 'bad') and r.get('issues')]
hints_p = os.path.join(OUT, 'qa_hints.json')
hints = json.load(open(hints_p, encoding='utf-8')) if os.path.exists(hints_p) else {}
for r in flag:
    parts = []
    for i in r['issues']:
        parts.append('[%s] %s -> %s' % (i.get('field'), str(i.get('problem', '')).strip(), str(i.get('suggest', '')).strip()))
    hints[r['k']] = ('an independent reviewer who LOOKED at the 128px picture found these faults in the previous card; fix them (describe only what the picture shows, keep naming-based associations out of look / analog / syn unless the picture supports them): ' + ' | '.join(parts))[:900]
print('flagged', len(flag), 'of', len(audit), '| verdicts', {v: sum(1 for r in audit if r.get('verdict') == v) for v in ('ok', 'fix', 'bad')})
if '--dry' in sys.argv:
    sys.exit(0)
json.dump(hints, open(hints_p, 'w', encoding='utf-8'), ensure_ascii=False)
keys = {r['k'] for r in flag}
shutil.copy(os.path.join(OUT, 'cards.jsonl'), os.path.join(OUT, 'cards.before_l1_merge.jsonl'))
keep = []; dropped = 0
for l in open(os.path.join(OUT, 'cards.jsonl'), encoding='utf-8'):
    if not l.strip():
        continue
    try:
        k = json.loads(l)['k']
    except Exception:
        continue
    if k in keys:
        dropped += 1
    else:
        keep.append(l if l.endswith('\n') else l + '\n')
open(os.path.join(OUT, 'cards.jsonl'), 'w', encoding='utf-8', newline='').write(''.join(keep))
print('dropped', dropped, 'cards to re-annotate; kept', len(keep))
