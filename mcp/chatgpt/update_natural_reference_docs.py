"""Bounded, repeatable documentation reconciliation for the private reference lane."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
LANE = ROOT / 'mcp/chatgpt'
STAMP = '16:22 EDT'

report = '''## Natural template questions — common facts, native answers — Oct10

“Anything unusual about the Skip Barber template?” previously fell into generic palette advice. The common `car-knowledge/core.js` now supplies bounded, read-only `referenceIntent()` to Offline and actual MCP context. Questions about quirks/gotchas/current-car preparation reach the compiled reference; palette questions and mixed/edit requests stay on their existing routes. Explicit short canonical names such as SRX resolve only in a template phrase, with negation preserved. No new car facts or UV geometry are created.

`natural_reference_edits.py` stages the exact Send integration: wait for the local reference index with visible busy state, preserve a newly typed draft, reject stale provider/document completions, then use the existing factual-answer lifecycle. The direct reader supplements follow-up retrieval. Reference packets carry `reference_context` and `chat_summary`; the same loaded-file verification limit appears in chat and expanded source details. Completed reads retire an older staged plan rather than displaying unrelated builder choices or unchanged-edit feedback. No actions or executor expansion.

Private59910 native: three questions about Skip Barber resolution, RUF shared archive/base/Wing labels, and current ARCA template preparation produce three completed answers, pending null and no live changes. Every exposed paint-state field is unchanged; all256px preview RGBA values remain exact. This current Codex model then receives the common facts and intent through actual `spb_assistant_context` and replies to latest inbox seq43 inside the ChatGPT panel. Existing status warms only derived unnamed-panel observations. Three retained project hashes match; zero new project saves/API calls. Receipt: `car-natural-native-acceptance.json`; replay: `verify_natural_reference_native.py`.

`car-knowledge/test_reference_intent.cjs` exercises all192 compiled records (routing, not192 native imports). `test_natural_reference_send.cjs` exercises actual generated Send/composer/store calls with the real readiness helper and conversation kernel, including cold load, draft retention, stale document/provider, failure, kill and mixed requests. Relevant answer/composer/relay/common reader/context/reference regressions pass. Current candidates preserve Claude's new clear-handler Undo stash and both W28 settled-preview spill checks; shared sources remain untouched.

Limits: first settled-page question is native; cold-index waiting is component-tested. An earlier Send during initial source restoration left its draft unsent and required retry; startup behavior remains open. The online reply required explicit message waiting. Actual Claude model parity, shared/package adoption, unattended connection, full-resolution output and verified car geometry remain open.192 qualified records /188 inspected templates /zero verified UV maps.

'''
handoff = '''## Latest: natural reference questions and faithful source limits

Review common `car-knowledge/core.js` `referenceIntent(text, knownNamedCar)`, consumed by `offline-answer.js` and `assistant-context.cjs`. Use its read-only question/current-context/overview flags to route factual template questions; retain mixed-edit, design and short-name negation boundaries. All192 compiled-record routes pass component checks; this does not establish complete quirk coverage or192 native imports.

Review exact `natural_reference_edits.py`: local index readiness before advice routing, guarded provider/document epoch, busy composer, retained unsent draft, then direct `readOnlyQuestion()` after follow-up lookup. `reference_context` clears stale builder choices. Keep `chat_summary` qualified with the same loaded-file/source limits as full text. Reuse completed-answer lifecycle; no new execution authority. Candidate rebase retains your clear-handler `stashUndo()` and both W28 settled-preview spill comparisons; do not wholesale-copy private candidates over owner changes.

Actual private Offline Skip/RUF/current-ARCA answers and this current model's actual MCP/ChatGPT reply seq43 pass; paint settings/256px preview unchanged and three retained projects hash-match. See `test_natural_reference_send.cjs`, `car-knowledge/test_reference_intent.cjs`, `verify_natural_reference_native.py` and `car-natural-native-acceptance.json`. Cold readiness is component evidence, settled-page first question native evidence. A Send during source restoration retained its draft but needed retry; investigate document-startup lifecycle before claiming immediate startup readiness. Unattended connection, actual Claude inference parity and shared adoption remain open.

'''

for name, section in [('REPORT.md', report), ('REQUESTS_FOR_CLAUDE.md', handoff)]:
    p = LANE / name
    txt = p.read_text(encoding='utf-8')
    if section.splitlines()[0] not in txt:
        marker = '\n## '
        at = txt.index(marker)
        txt = txt[:at+1] + section + txt[at+1:]
    txt = txt.replace('15:52 EDT', STAMP, 1)
    p.write_text(txt, encoding='utf-8')

p = LANE / 'SMARTER_AI.md'
txt = p.read_text(encoding='utf-8')
old = 'The next customer-facing gap is an enabled-looking Send while prior verification still holds the operation lease; a click was ignored with input retained. Repair busy feedback without replaying delivered edits.'
new = 'Busy feedback now has focused composer/native verification evidence. The next recovery gap is a first Send during initial source restoration: the draft remained but needed retry. Investigate the document-startup lifecycle without replaying delivered edits. Natural template questions now use the common factual reader; keep source qualification visible in chat as well as expanded details.192 compiled routes and three native questions pass, with cold-index readiness component-tested; adopt the exact shared integration before treating this as packaged delivery.'
assert old in txt or new in txt
txt = txt.replace(old, new)
p.write_text(txt, encoding='utf-8')

p = ROOT / 'SPB_WIKI.html'
w = p.read_text(encoding='utf-8')
rows = re.findall(r'^\| \*\*Codex — eight-hour AI / Offline Helper restart\*\*.*$', w, re.M)
assert len(rows) == 1
row = rows[0]
needle = 'Next: broader customer journeys, connection recovery and exact shared adoption.'
addition = 'Natural template questions now reach common car facts; three native Offline answers plus current-model MCP/ChatGPT reply pass with source limits visible and paint unchanged.192 reference routes/cold index guards component-tested; initial source-restoration Send still needs recovery. Next: broader customer journeys, connection recovery and exact shared adoption.'
if addition not in row:
    assert needle in row
    w = w.replace(row, row.replace(needle, addition), 1)
pat = r'### 2026-10-10 - Codex: AI and Offline Helper.*?(?=\n### |</script>)'
m = re.search(pat, w, re.S)
assert m
s = m.group(0)
s = re.sub(r'\(updated [^)]+\)', '(updated '+STAMP+')', s, count=1)
oldbullet = next(l for l in s.splitlines() if l.startswith('- Shared knowledge contains'))
newbullet = '- Shared knowledge: **192 qualified records /188 inspected templates /zero verified UV maps**. Natural Skip/RUF/current-car questions now reach the common factual reader; three native Offline answers and current-model MCP/ChatGPT reply seq43 pass with source limits visible, no pending ask, exact256px preview/settings and retained project hashes.192 compiled routes and cold-index/provider/document/draft guards component-tested. `car-natural-native-acceptance.json`; initial source-restoration Send needed retry. Shared adoption, actual Claude parity and unattended startup/connection remain open.'
s = s.replace(oldbullet, newbullet)
s = s.replace('rechecked 15:52 EDT', 'rechecked '+STAMP)
assert len([l for l in s.splitlines() if l.startswith('- ')]) == 6
w = w[:m.start()] + s + w[m.end():]
tr = re.search(r'(<script type="text/markdown" data-section="trouble"[^>]*>)(.*?)(</script>)', w, re.S)
assert tr
note = '\n\n### Codex private59910 — initial restoration can leave first Send unsent (Oct10)\n\nObserved while opening AI immediately after a fresh page showed the restored layer: first question remained in the composer and no answer appeared; retry after source restoration settled succeeded. Natural reference readiness now passes cold-index component guards and first settled-page native reads, but initial document-startup behavior is still open. Preserve the draft and show readiness honestly; do not auto-replay a possibly delivered edit. Exact root cause and shared fix are unverified. See `mcp/chatgpt/REPORT.md` natural-reference evidence.\n'
if '### Codex private59910 — initial restoration can leave first Send unsent' not in tr.group(2):
    w = w[:tr.end(2)] + note + w[tr.end(2):]
p.write_text(w, encoding='utf-8')
print('Reconciled four scoped documents; Wiki own row/log and one trouble note only.')
