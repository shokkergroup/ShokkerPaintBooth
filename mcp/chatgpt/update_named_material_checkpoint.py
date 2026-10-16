"""Record bounded named-layer acceptance without touching shared AI source."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
here = root / 'mcp/chatgpt'
heading = '## Named layer material evidence and Limited history — Oct10 22:01EDT'
detail = heading + '''

Customer gap: a buyer asking “What material is on Sponsors?” could miss current evidence or get selected-layer guidance. The owned editor-capabilities.js now resolves only exact current layer names, group paths or IDs. Repeated names are listed separately with exact IDs; missing/duplicate/unreadable identities and bounded omissions remain unresolved. Observed visibility is true/false/unknown; hidden ancestors force hidden, unknown does not imply active material. None does not imply no spec: zones/imported spec can still supply it. Disabled/unavailable material support and stored-versus-rendered limits are explicit. No selection, assignment, scan, render or Undo is performed. Different-car and mixed question/edit requests retain their existing routes.

The existing shared reader already explained Layer Materials, Spec Doctor and Edge Bleed accurately; that work was retained rather than duplicated. named_layer_material_edits.py composes exact spb-pro-ai.js state/get_state patches adding an optional bounded editor_query. assistant-context.cjs forwards the buyer question; focused named evidence survives unrelated oversized inventories with explicit omissions, while oversized focused evidence remains unavailable. build_candidates.py prepares25 candidates with unchanged shared source and precise patches. test_named_layer_materials.cjs uses Claude’s actual LayerMat core, generated state caller and Offline route; selected-layer isolation, duplicate names/IDs, numeric/string ID collisions, >120-character IDs, hidden ancestors, unknown visibility, disabled/unreadable/bounded inventories and changed documents pass. test_editor_capabilities.cjs also executes the generated Offline Send branch for the named question; test_assistant_context.cjs verifies query forwarding/context limits. Existing material-choice and diagnostic guidance pass. These are component checks, not a newly measured native Send or deployed customer feature.

Private59910 native DOM still reads42 ARCA layers/5 zones/0 history actions, but a real AI-button click again times out in Input.dispatchMouseEvent. No server restart or new fixture/save was made for that observation failure. Native named-question Send and current-page reload remain open; the older page may not yet contain the new query caller. Shared/package adoption and installed Claude parity remain open. No model inference/API credits were used in this continuation.

Exact dirtlatemodel-350 Limited:16 receipt hashes independently verified and archived PDF page3 visually inspected. One dated ALL Dirt Late Model passenger-side WOO decal artwork-history note promoted only to Limited, with family-wide rather than Limited-exclusive scope. The2019S2Patch2 label comes from filename/path; no printed exact patch event date is asserted. Official2025S4 Limited qualifier confirms name scope only; physics and neighboring Dallara controls excluded. No current placement instruction, removable/forced logo, numberboard/control/material/export rule, template revision, compatibility or UV fact. integrate_dirt_limited.py/test_dirt_limited_history.cjs pass, along with knowledge/depth/Dirt358 regressions and source/build verification. Actual MCP/common context receipt car-knowledge-mcp-2026-10-11T01-59-30-156Z.json retrieves the qualified fact with zero paint/model reads. Corpus290 facts:207 metadata/79 official documentation/4 secondary;62 records beyond metadata/130 metadata-only;192 exact records/188 inspected templates/zero verified UV maps. Historical documentation does not establish current painting expertise.

Next customer gate: native named-question Send, then persistent listener startup/reconnect and busy-state UX without idle inference, re-consuming a pending question or paint replay. Keep owner deadline Oct11 13:38:35UTC and main goal ACTIVE. Claude review handoff is in REQUESTS_FOR_CLAUDE.md; scoped documentation mirrors only, no shared runtime adoption implied.

'''
short = heading + '''

Exact named-layer material read guidance is staged for both assistants and Offline Helper: full group/ID choice for duplicate names, true/false/unknown visibility including hidden ancestors, unreadable/bounded identity limits and no selected-layer substitution. Stored assignments remain distinct from composited spec; None can still receive zone/imported spec. Generated state/get_state caller accepts bounded editor_query; MCP forwards it and preserves focused evidence when unrelated inventories exceed budget. Actual owner LayerMat core, generated Offline route/Send and context tests pass. No edits/scans/renders/inference. Native Send remains unmeasured because private IAB mouse input still times out; do not market this as installed acceptance. Files/tests and precise evidence are in the current checkpoint.

Limited exact dirtlatemodel-350 receives one qualified2019 ALL-family WOO artwork-history fact after16 hashes and visual PDF scope review; no current placement/template/UV rule, Pro/Super promotion or exact printed event date. Actual MCP/Offline retrieval and regressions pass.290 facts/62 beyond metadata/130 metadata-only;192 records/188 inspected templates/zero verified UV maps. Next: native Send and persistent listener/busy-state reliability; main goal remains ACTIVE through Oct11 13:38:35UTC.

'''
requests = heading + '''

Review owned editor-capabilities.js, named_layer_material_edits.py and assistant-context.cjs plus the generated exact spb-pro-ai.js patch. Reuse the current capability reader; generic Layer Materials/Doctor/Edge Bleed guidance already existed. The new gap is named current layers: resolve exact group paths/IDs, list repeated names separately, preserve unknown/ancestor-hidden visibility, distinguish stored material from final spec and never substitute the selection. Optional editor_query focuses read evidence; oversized unrelated inventories must not erase it. test_named_layer_materials.cjs, test_editor_capabilities.cjs, test_layer_material_guidance.cjs and test_assistant_context.cjs pass against actual material core/generated callers. No material edit/tool is advertised by this read. Native buyer Send, reload, Claude parity and shared/package adoption remain required; current IAB mouse timeout is observation failure, not a server failure.

One exact Limited dirtlatemodel-350 historical ALL-family decal note is qualified and tested; filename supplies2019S2P2 label, no exact printed event date or present-day move instruction.16 archived artifacts/visual PDF scope verified; neighboring Dallara control blocks and Limited physics excluded. Corpus290 facts/62 beyond metadata/130 metadata-only. Keep zero UV maps and template incompatibility limits. Prior subscription recovery remains read-only; prioritize customer startup/reconnect/busy state without idle inference or consuming the pending message again. No API fallback/new saves/outside messages.

'''
for name, block in [('REPORT.md', short), ('REQUESTS_FOR_CLAUDE.md', requests), ('EDITOR_CAPABILITIES_ACCEPTANCE.md', detail), ('SMARTER_AI.md', short)]:
    p = here / name
    text = p.read_text(encoding='utf-8')
    if heading not in text:
        p.write_text(block + text, encoding='utf-8')
p = here / 'SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md'
text = p.read_text(encoding='utf-8')
if heading not in text:
    text = text.replace('## Measured continuation work\n\n', '## Measured continuation work\n\n' + detail, 1)
    p.write_text(text, encoding='utf-8')
p = here / 'car-knowledge/README.md'
text = p.read_text(encoding='utf-8')
note = '## Limited family-wide historical artwork — Oct10 22:01EDT\n\nOne exact dirtlatemodel-350 ALL-family WOO decal-history note promoted after16 receipt hashes and visual PDF scope review.2019S2P2 filename label only; no exact printed event date, Limited-exclusive/current placement instruction, controls, revision, shared compatibility or UV fact. Actual Offline/MCP retrieval pass; car-knowledge-mcp-2026-10-11T01-59-30-156Z.json.290 facts/62 records beyond metadata/130 metadata-only;192 cars/188 inspected templates/zero verified UV maps. See integrate_dirt_limited.py/test_dirt_limited_history.cjs and current checkpoint.\n\n'
if note.splitlines()[0] not in text:
    p.write_text(note + text, encoding='utf-8')
p = root / 'SPB_WIKI.html'
wiki = p.read_text(encoding='utf-8')
lines = wiki.splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.startswith('| **Codex — sixteen-hour AI / Offline Helper improvement**'):
        lines[i] = '| **Codex — sixteen-hour AI / Offline Helper improvement** | Owner renewed through Oct11 09:38EDT/13:38UTC; online conversation and useful Offline assistance. | `mcp/chatgpt/**`, private59910, scoped Wiki/docs; Claude runtime read-only. | ACTIVE22:01EDT — named-layer material evidence/Offline Send/MCP caller components pass; native IAB input still unavailable.290 facts/62 beyond metadata/130 metadata-only;192 cars/188 templates/zero UV maps. Next: native Send, persistent listener/busy-state/adoption. | 2026-10-10 |\n'
    elif line.startswith('| **Codex research — Dirt Late Model Limited**'):
        lines[i] = ''
    elif line.startswith('- **Oct10 Codex exact-car research:**'):
        lines[i] = '- **Oct10 Codex exact-car research:** ARCA/FordGT4 zero proposals; Ferrari296/MercedesGT4/BMW F82 and Dirt358/Limited qualified historical notes verified by source headings/receipt hashes, with PDF visual scope where needed. Runtime retrieval measured; no current template/UV authority. See `mcp/chatgpt/car-knowledge/README.md`.\n'
wiki = ''.join(lines)
start = wiki.index('### 2026-10-10 - Codex: AI and Offline Helper')
end = wiki.index('\n### ', start + 5)
entry = '''### 2026-10-10 - Codex: AI and Offline Helper (updated 22:01EDT)
- Owner window ends **Oct11 13:38:35UTC/09:38EDT**; main goal ACTIVE. Private59910 only, shared Claude AI/MCP/UI read-only; [REPORT](mcp/chatgpt/REPORT.md), [Claude requests](mcp/chatgpt/REQUESTS_FOR_CLAUDE.md), [checkpoint](mcp/chatgpt/SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md). No API credits/outside posts/new project variants; two original reusable fixtures retained.
- Online: prior2 native plan-backed turns and actual new-process read-only subscription recovery retained. Pending question committed before inference; explicit fresh-scope recovery, lost delivery receipt settles without repeated inference, zero idle models. Three-tool MCP boundary rejects edits/Undo/render;8 exposed fields/two fixture hashes exact. Draft/status/card guards retained. Customer Send, persistent startup/reconnect/busy-state/crash-lock UX, Claude parity and adoption open; [product path review](mcp/chatgpt/CHATGPT_SUBSCRIPTION_PATH_REVIEW_2026-10-10.md) records eligibility limits.
- Offline intelligence: exact named-layer material questions now resolve full current group paths/IDs rather than substituting selection. Duplicate names require choice; hidden ancestors/unknown visibility, None-versus-zone/imported spec, disabled/unreadable/bounded evidence and stored-versus-rendered limits preserved. Existing shared material/Doctor/Edge Bleed guidance reused. Actual owner core + generated Offline route/Send/state + MCP query/budget component tests pass. Native new Send is unmeasured; IAB DOM works but input still times out. No new model turn or edit.
- Source/actions: prior native ARCA loading/draft recovery and source-bound4 stale rejections retained; exact body opacity→Undo restores5 fields/encoded preview.4 unsupported part requests withheld with9 fields/two fixture hashes exact; unverified geometry and kit placement withheld. Prior protected recolour/resize/material/locked refusal/Undo evidence retained. Taught-mask positive, import-switch, actual kit provenance and real-car output remain open.
- Car knowledge:192 exact records/188 inspected templates/**zero verified UV maps**;290 facts,62 records beyond metadata/130 metadata-only. Limited16 artifacts + visual PDF page3 verified;1 dated ALL-family WOO decal-history note, filename season/patch label only, no current placement/template/UV instruction. Actual MCP/common context and Offline history/template separation pass. Earlier qualified dated notes and bounded zero-proposal reviews retained; historical documentation is not current paint expertise.
- Cleanup/sync: scoped38 documentation/depth mirrors current; no runtime adoption implied. Next customer gap: native named-question Send and listener lifecycle/busy-state reliability without idle inference, duplicate consumption or edit replay; shared/package review in Claude requests. Main goal incomplete; stop/delete continuation and report measured gaps at deadline.
'''
p.write_text(wiki[:start] + entry + wiki[end:], encoding='utf-8')
print('Updated named-layer acceptance, Claude handoff, Limited evidence and compact active Wiki lane.')
