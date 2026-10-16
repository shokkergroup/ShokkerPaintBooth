"""Reconcile selected-material evidence without expanding the shared daily log."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
LANE=ROOT/'mcp/chatgpt'
STAMP='16:47 EDT'
report='''## Independent artwork/body materials and selected layer facts — Oct10

Native “Can I keep my sponsors matte while the body stays chrome? Explain only” previously took a Spec Doctor detour. Common `editor-capabilities.js` now distinguishes that design choice from a shiny-artwork symptom, explains the existing owner Layer Materials controls, and reports bounded current selected-layer material facts. Selected IDs must uniquely match current layers; missing/duplicate/out-of-budget/unreadable selection stays qualified. None means no Layer Material assignment, not no spec. Spec presets versus finish paint/Keep Art Colour, layer coverage and current availability remain explicit. No material write tool or executor was added.

Native private59910: natural design answer; selected Sponsors None; actual current-model MCP context/in-app reply; temporary Matte Vinyl through the owner’s existing UI; actual MCP/Offline reader reports Matte Vinyl; native keyboard Undo; fresh Offline answer reports None. All exposed paint state matches after Undo and all256px preview RGBA values remain exact. Three retained project hashes match; no new saves/API usage. Stored material retrieval is not full-resolution spec/appearance proof. V3 acceptance: `layer-material-native-acceptance.json`, `verify_layer_material_guidance_native.py`; earlier failures remain retained.

The comparison also exposed incorrect generic conversation inference: sponsors + chrome left a soft “missing look” slot. Exact `material_answer_lifecycle_edits.py` stages `completeReadOnly()` in the shared kernel and a locally registered WeakMap/WeakSet producer call after actual entry completion. Only a completed local material fact retires its inferred target/look and pending slot; real asks, changes, offers and other topics retain their semantics. No saved/model flag can claim local identity or edit authority. V3 native history has three answers, no pending/last target/offer/change. The first staged replay failed because a test assumed an enc field absent from the actual payload; corrected registration and actual generated Send tests catch that boundary.

Latest current-document binding attaches the reader’s document stamp to the local payload and checks it before completion; this addition after V3 native evidence is component-tested. `test_layer_material_guidance.cjs`, `test_material_answer_lifecycle.cjs`, extended `test_answer_lifecycle.cjs` and capability/context/reference regressions pass.25 review candidates preserve owner changes; shared source files remain read-only. Private server restarted only to add the new kernel route, now PID281604. Startup correctly refused a stale car build; rebuilding/checking it restored service with the same192/188/zero coverage. Source-restoration race, actual Claude inference parity, shared/package adoption, unattended connection and material write integration remain open.

'''
handoff='''## Latest: independent materials, exact selection and completed facts

Use `editor-capabilities.js` `layer_materials.selection` alongside stored assignments. It reads only current selected IDs, ordinary names, normalized records, visibility/lock state and explicit missing/unreadable/omitted limits. Natural independent artwork/body questions now explain your Layer Materials controls rather than misclassifying the request as a shiny-artwork fault; actual “why are sponsors chrome” remains diagnostic. None does not mean no spec. No new write capability is advertised; applying materials through AI remains a separate integration gap.

Review exact `material_answer_lifecycle_edits.py` and `candidates/spb-convo-state.js.patch`: a local completed material answer must not infer sponsor-chrome from a matte-art/chrome-body comparison or leave a soft missing-look prompt. `completeReadOnly()` checks actual noted entry/text/answer role and refuses ask/change/offer. The producer uses WeakMap/WeakSet identity, not a model/saved boolean or assumed enc field. Current-document stamps feed the existing finish guard and completion check. Do not apply this behavior to all conversation topics or redesign normal edit/offer/Undo semantics.

Private V3 native None→actual owner UI Matte Vinyl→fresh common MCP/Offline reading→native Undo→None passes with no pending/last target and exact exposed paint/256px preview; current-model reply uses matching new-run seq1.Three retained projects unchanged. `verify_layer_material_guidance_native.py` / `layer-material-native-acceptance.json`; actual generated producer/kernel tests in `test_answer_lifecycle.cjs`, `test_material_answer_lifecycle.cjs`, selection/design tests in `test_layer_material_guidance.cjs`. Document binding added after V3 is component-tested; actual Claude inference/shared adoption/full material-output proof remain open. Initial incorrect diagnostic, soft-slot and missing-producer-field replays remain as negative receipts.

'''
for name,section in [('REPORT.md',report),('REQUESTS_FOR_CLAUDE.md',handoff)]:
 p=LANE/name;s=p.read_text(encoding='utf-8')
 if section.splitlines()[0] not in s:
  at=s.index('\n## ');s=s[:at+1]+section+s[at+1:]
 s=s.replace('16:27 EDT',STAMP,1);p.write_text(s,encoding='utf-8')
p=LANE/'SMARTER_AI.md';s=p.read_text(encoding='utf-8')
note='\nSelected material facts and natural artwork/body contrasts now have native reader/current-model evidence, including an actual owner-UI Matte Vinyl assignment and native Undo. Reuse the owner feature; do not reinterpret a comparison as one inferred chrome target. Completed local material facts retire the misleading soft slot. AI material application still needs an advertised tool and verified native Undo/scope contract; reading a supported editor control is not that delivery.\n'
if note.strip() not in s:s=s.replace('\n## Shared behavior',note+'\n## Shared behavior',1)
p.write_text(s,encoding='utf-8')
p=ROOT/'SPB_WIKI.html';w=p.read_text(encoding='utf-8')
rows=re.findall(r'^\| \*\*Codex — eight-hour AI / Offline Helper restart\*\*.*$',w,re.M);assert len(rows)==1
newrow='| **Codex — eight-hour AI / Offline Helper restart** | Owner Oct10: customer-facing online/subscription-free Offline work through17:13EDT/21:13UTC. | `mcp/chatgpt/**`, private59910, scoped Wiki/docs; Claude runtime read-only. | ACTIVE — latest: natural artwork/body material guidance and current selected-layer facts pass native Offline/current-model retrieval; actual owner-UI Matte Vinyl→keyboardUndo→None restores exposed state/256px preview. Completed material answers retire misleading soft look/target slots.25 exact review candidates; shared adoption/AI material write/Claude parity/startup-reconnect remain open. Natural car questions/cold reference first Send pass;192 qualified records/188 inspected templates/zero verified UV maps. Three unchanged fixtures, no new projects. [Evidence](mcp/chatgpt/REPORT.md). | 2026-10-10 |'
w=w.replace(rows[0],newrow,1)
m=re.search(r'### 2026-10-10 - Codex: AI and Offline Helper.*?(?=\n### |</script>)',w,re.S);assert m
s=m.group(0);s=re.sub(r'\(updated [^)]+\)','(updated '+STAMP+')',s,count=1)
old=next(l for l in s.splitlines() if l.startswith('- Offline now'))
new='- Offline natural artwork/body material questions now explain owner Layer Materials; common selected-layer facts report None/Matte Vinyl without guessing shine. Native current-model retrieval/reply and actual owner-UI assignment→keyboardUndo→None pass; exact exposed paint/256px preview and project hashes restored. New local material-answer completion retires incorrect sponsor-chrome/missing-look inference; genuine asks/edits/offers stay intact. `layer-material-native-acceptance.json`; document guard added afterward is component-tested. Earlier material/guide/pattern/composer scope evidence remains in REPORT.'
s=s.replace(old,new);assert len([l for l in s.splitlines() if l.startswith('- ')])==6
w=w[:m.start()]+s+w[m.end():]
pm=re.search(r'(<script type="text/markdown" data-section="postmortems"[^>]*>)(.*?)(</script>)',w,re.S);assert pm
post='\n\n### Codex Oct10 — test the real factual-answer payload\n\nThe first material-conversation completion proposal passed an isolated test that supplied an enc object, but the actual fast-answer producer carries no enc field. Native replay still left an incorrect sponsor-chrome/missing-look slot. Fix: register topic/source stamp against the exact local payload in WeakMap, retain WeakSet completion identity, and exercise actual generated Send plus actual kernel/terminal caller. Corrected V3 native None→Matte Vinyl→Undo→None has no pending/target; shared adoption remains open. The private restart also refused stale reference generation; rebuild/check restored59910 with unchanged192/188/zero coverage. See `mcp/chatgpt/REPORT.md` and retained negative receipts.\n'
if '### Codex Oct10 — test the real factual-answer payload' not in pm.group(2):w=w[:pm.end(2)]+post+w[pm.end(2):]
p.write_text(w,encoding='utf-8')
print('Reconciled report/handoff/strategy and bounded own Wiki row/log/post-mortem.')
