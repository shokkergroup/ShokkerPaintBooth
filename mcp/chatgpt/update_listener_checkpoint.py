"""Bounded Wiki/Claude checkpoint update; no shared AI source writes."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
here = root / 'mcp/chatgpt'
detail = '''## Subscription listener recovery and Dirt358 evidence — Oct10 21:48EDT

Owned subscription-listener-core.cjs / subscription-listener.cjs now wait locally without idle model inference, commit the exact received batch before inference and preserve it on failure. Explicit recovery validates provider, current document, sequence, text and30-minute age against the scoped app transcript. Already-replied questions settle a lost terminal journal receipt without model execution. Network waits retry at most3 times without inference; auth/off/unscoped/expired context stops. A single-controller lock prevents concurrent private ownership; crash-lock UX remains open. No automatic paint-operation replay or arbitrary Codex session resume. subscription-turn-server.cjs reuses the existing chatTool scope/advice handoff with a once-only already-claimed wait; it exposes only wait, fresh assistant context and reply, and rejects do/edit/undo/render at the MCP request boundary. Isolated ephemeral read-only CLI config and API-credential filtering reused; no installed auth/config edits.

Actual private59910 receive-only checkpoint → process ends with pending question → ordinary restart refuses with zero inference → explicit new-process recovery delivers one installed ChatGPT-plan model turn seq1. Fresh exact-query context explains Paintable Area/Base Paint psd_0 versus three spec copies, with labels/UV limits; spb_reply shown_in_app:true and matching current transcript. Eight exposed paint fields and both original fixture hashes unchanged. Controlled lost terminal journal write then settles already_replied with zero new inference. Receipt subscription-listener-recovery-2026-10-11T01-42-28-229Z.json; worker subscription-listener-turn-2026-10-11T01-42-10-787Z.json; verify_subscription_listener.py. Actual6-second idle test performs3 local waits/zero inference (subscription-listener-idle-acceptance.json). Core recovery tests, actual three-tool MCP boundary, subscription environment/auth-preflight and syntax checks pass. Installed binary is now0.162.0-alpha.17.2 at the current hash directory; the earlier successful binary path was removed. Explicit path/model/tier acceptance choices remain developer-only.

This is a bounded read-only controller and local in-app reply proof, not customer Send UI, permanent startup/wake, arbitrary mid-inference crash/network loss, full raster equality, installed Claude parity or packaged adoption. Shared20-second listening grace may show idle during a longer model turn; do not consume/redeliver the same message just to keep a listening light active. No API credits, new project saves or outside posts. Official future product path and commercial eligibility limitation are recorded in CHATGPT_SUBSCRIPTION_PATH_REVIEW_2026-10-10.md; no OAuth registration/token access was performed.

Dirt358Modified exact dirtmodified-358: independently checked14 artifacts and exact release headings. One dated2021S3Patch2 World of Outlaws logo update applies to ALL Dirt Modified variants; official2021S1 launch names Big Block and358, making the binding explicit. Preserve family-wide rather than358-exclusive scope. Other Dirt/FormulaVee/ModifiedSK/global headings excluded; no sibling promotion. No current restriction, forced/removable branding, controls, template revision, shared compatibility or UV fact. integrate_dirt358.py / test_dirt358_history.cjs; actual MCP/common context receipt car-knowledge-mcp-2026-10-11T01-44-04-749Z.json. Corpus289 facts:207 template metadata/78 official documentation/4 secondary;61 records beyond metadata/131 metadata-only,192 cars/188 templates/zero verified UV maps. Historical documentation is not current paint expertise.

Claude review/next gates: retain the receipt-before-inference/fresh-context/no-edit-replay pattern in its listener; review the dedicated three-tool adapter and pending journal ownership before shared adoption. Test buyer Send→restart→reply, wrong document/provider, lost acknowledgement and offline/limit fallback natively. Add packaged startup/wake, stop/reconnect and useful busy-state UX without spending inference while idle. Review one exact358 fact with family scope. Next shared Offline intelligence gap: read Claude's newly shipped Layer Materials / Spec Doctor / Edge Bleed lanes and expose accurate supported guidance from current runtime evidence, retaining OFF-by-default and live material boundaries. Goal remains ACTIVE through Oct11 13:38:35UTC; main goal incomplete.

'''
report = '''## Subscription listener recovery and Dirt358 evidence — Oct10 21:48EDT

Bounded private controller preserves a received question before inference; ordinary restart requires explicit recovery, which validates exact current provider/document/sequence/text/age. One real installed ChatGPT-backed Codex0.162.0-alpha.17.2 turn delivers a fresh-context Base Paint explanation through spb_reply. Lost terminal journal receipt settles from the app transcript with zero repeated inference. Actual6-second idle waits start zero models; eight exposed paint fields and two fixture hashes exact. Only three MCP tools are exposed, with write/undo/render attempts rejected at request boundary. Core/auth/environment/protocol/verifier checks pass. Evidence and precise limits in SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md; files subscription-listener*.cjs, subscription-turn-server.cjs, probe/verify/tests. Customer Send UI, persistent lifecycle/crash-lock/busy-state UX, arbitrary crash recovery, Claude parity and package adoption remain open. No write-operation replay/API fallback.

Dirt35814 receipt hashes and exact ALL-family/launch headings verified; one dated logo-history fact promoted only to exact358. Actual MCP/Offline tests retrieve it with family-wide scope, no current restriction/template/UV claims.289 facts/61 non-metadata records/131 metadata-only;192 cars/188 templates/zero UV maps. Product route reviewed against official docs in CHATGPT_SUBSCRIPTION_PATH_REVIEW_2026-10-10.md; commercial eligibility unconfirmed, no OAuth or outside submission. Goal ACTIVE; next read Claude's current Layer Materials/Spec Doctor/Edge Bleed evidence for useful shared Offline guidance.

'''
requests = '''## Subscription restart recovery — Oct10 21:48EDT

Review owned subscription-listener-core.cjs, subscription-listener.cjs and subscription-turn-server.cjs. They preserve an exact received batch, wait locally without inference and recover only after validating the current scoped transcript. Reuse this principle in Claude's watcher; never interpret again:true as permission to repeat an edit. Actual subscription checkpoint/new-process recovery and lost terminal receipt acceptance pass; only three read-only conversation MCP tools exposed. See current checkpoint for receipts/limitations and verify_subscription_listener.py/test_subscription_listener.cjs/test_subscription_turn_server.cjs.

Before adoption: buyer Send→restart→fresh-context reply; stale provider/document→no answer/action; uncertain delivery→no replay; interrupted worker/expired question→useful recovery/Offline guidance. Complete startup/wake, crash-lock ownership and busy/listening UX (shared grace is20s; do not issue another consuming wait during processing). Keep model/authentication/listening/delivery distinct and no API fallback. Dedicated journal contains buyer text; exclude it and pairing tokens from packaging. Current private proof is read-only, not edit recovery or persistent buyer availability. Review official product route/eligibility notes in CHATGPT_SUBSCRIPTION_PATH_REVIEW_2026-10-10.md; no token scraping/registration/submission occurred.

Exact dirtmodified-358 history: one dated ALL Dirt Modified logo update with launch binding,14 parent-checked artifact hashes; no358-exclusive branding/forced logo/template/UV claims or sibling promotion. Current289 facts/61 beyond metadata/131 metadata-only. Actual MCP and Offline history/template distinction pass. Native customer Send remains open. Shared sources untouched; scoped docs mirrored. Next current-runtime guidance review: Layer Materials, Spec Doctor, Edge Bleed (OFF by default); preserve Claude-owned tools and actual material boundaries.

'''
for name, block in [('REPORT.md', report), ('REQUESTS_FOR_CLAUDE.md', requests)]:
    p = here / name
    text = p.read_text(encoding='utf-8')
    if block.splitlines()[0] not in text:
        p.write_text(block + text, encoding='utf-8')
p = here / 'SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md'
text = p.read_text(encoding='utf-8')
if detail.splitlines()[0] not in text:
    text = text.replace('## Measured continuation work\n\n', '## Measured continuation work\n\n' + detail, 1)
    p.write_text(text, encoding='utf-8')
for name, block in [
    ('SMARTER_AI.md', '## Subscription controller acceptance — Oct10 21:48EDT\n\nLocal idle waits start no model; preserve received questions and validate exact current transcript before explicit recovery. One actual plan-backed new-process answer and lost journal receipt settlement pass, with three-tool read-only MCP boundary and eight paint fields/two fixture hashes exact. Customer Send, persistent startup/wake/busy-state UX, crash ownership, Claude parity and package adoption remain open. See current checkpoint and CHATGPT_SUBSCRIPTION_PATH_REVIEW_2026-10-10.md for product-path eligibility. Next shared guidance gap is Claude’s newly shipped Layer Materials / Spec Doctor / Edge Bleed, reviewed from current runtime evidence.\n\n'),
    ('car-knowledge/README.md', '## Dirt358 family-wide dated logo history — Oct10 21:48EDT\n\nExact dirtmodified-358 receives one2021S3P2 World of Outlaws contingency-logo history fact; ALL-family coverage is explicitly bound by the official two-class launch.14 artifacts/heading blocks independently checked; no358-exclusive feature, current restriction, forced/removable logo rule, template revision, shared compatibility or UV claim. integrate_dirt358.py/test_dirt358_history.cjs and actual MCP context retrieval pass (01:44UTC receipt). Corpus289 facts/61 records beyond metadata/131 metadata-only;192 cars/188 inspected templates/zero verified UV maps. Native customer Send/adoption remains open.\n\n'),
]:
    p = here / name
    text = p.read_text(encoding='utf-8')
    if block.splitlines()[0] not in text:
        p.write_text(block + text, encoding='utf-8')

p = root / 'SPB_WIKI.html'
wiki = p.read_text(encoding='utf-8')
lines = wiki.splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.startswith('| **Codex — sixteen-hour AI / Offline Helper improvement**'):
        lines[i] = '| **Codex — sixteen-hour AI / Offline Helper improvement** | Owner renewed through Oct11 09:38EDT/13:38UTC; online conversation and useful Offline assistance. | `mcp/chatgpt/**`, private59910, scoped Wiki/docs; Claude runtime read-only. | ACTIVE21:48EDT — actual one-turn subscription checkpoint/restart recovery and lost delivery receipt settled; zero idle inference, read-only three-tool boundary,8 paint fields/two fixtures exact.289 facts/61 beyond metadata/131 metadata-only;192 cars/188 templates/zero UV maps. Native Send/startup/busy-state/adoption open. Next: current Layer Materials/Spec Doctor/Edge Bleed guidance. | 2026-10-10 |\n'
    elif line.startswith('| **Codex research — Dirt358Modified**'):
        lines[i] = ''
    elif line.startswith('- **Oct10 Codex exact-car research:**'):
        lines[i] = '- **Oct10 Codex exact-car research:** ARCA/FordGT4 zero paint facts; MercedesGT4/Ferrari296/BMW F82 dated notes and Dirt358 explicit ALL-family logo history reviewed with exact headings/receipt hashes; runtime retrieval measured, no template/UV authority. See `mcp/chatgpt/car-knowledge/README.md`.\n'
wiki = ''.join(lines)
start = wiki.index('### 2026-10-10 - Codex: AI and Offline Helper')
end = wiki.index('\n### ', start + 5)
entry = '''### 2026-10-10 - Codex: AI and Offline Helper (updated 21:48EDT)
- Owner renewed through **Oct11 13:38:35UTC/09:38EDT**; goal authoritatively ACTIVE. Private59910 only, Claude AI/MCP/UI source read-only; exact proposals/coordination in [REPORT](mcp/chatgpt/REPORT.md), [Claude requests](mcp/chatgpt/REQUESTS_FOR_CLAUDE.md), [checkpoint](mcp/chatgpt/SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md). No API credits/outside posts/new project variants; two original fixtures retained and hash-verified.
- Source/loading: native ARCA cold recovery held draft→ready→one Send; whole-project busy uses Claude persistence boundary (component coverage). Source-bound executor rejects4 stale identities; exact body psd_0 opacity→Undo restores5 fields/encoded preview. Named-part preflight rejects4 unsupported requests with9 fields exact; library geometry/kit placement withheld. Taught-mask positive, real import-switch and kit provenance remain open.
- Online: prior2 native plan-backed turns retained. New dedicated local listener starts zero idle models, commits received batch before inference, requires explicit exact-context recovery and never replays edits. Actual new-process subscription recovery delivers1 fresh-context Base Paint answer; lost terminal journal receipt settles without new inference. Three-tool MCP boundary rejects do/edit/undo/render;8 exposed paint fields/two fixtures exact. Draft/status/card guards retained. Customer Send UI, persistent lifecycle/busy-state/crash-lock UX, installed Claude parity and adoption open; [product-path review](mcp/chatgpt/CHATGPT_SUBSCRIPTION_PATH_REVIEW_2026-10-10.md) records eligibility limits without token access.
- Offline: prior scoped recolour/resize/material/locked-refusal/Undo evidence retained. Exact other-car follow-ups and4/1 Base Paint group/ID answers keep labels/pixels/UV distinct; actual subscription model now consumes live exact-layer guidance. Current shipped Claude Layer Materials/Spec Doctor/Edge Bleed need shared guidance review; preserve material boundaries/OFF-by-default. Native updated customer Send remains open because IAB input/screenshot unavailable.
- Car knowledge:192 exact records/188 inspected templates/**zero verified UV maps**,289 facts;61 records beyond metadata/131 metadata-only. Dirt35814 artifact hashes/ALL-family and two-class launch headings verified;1 dated logo fact promoted only to358 with family-wide scope. Actual MCP/Offline history-template distinction pass. Earlier Ferrari296/MercedesGT4/BMW F82 dated facts retained; ARCA/FordGT4 bounded zero-proposal reviews retained. No current restriction/forced-logo/template/UV claims from historical artwork.
- Cleanup/sync: scoped38-file documentation mirror checked; no helper runtime adoption implied. Next: current-runtime material/helper guidance, native Send and listener startup/reconnect/busy-state UX, taught-mask positive→Undo and Claude/package adoption. Goal remains incomplete; stop/delete continuation and report measured gaps at deadline.
'''
wiki = wiki[:start] + entry + wiki[end:]
p.write_text(wiki, encoding='utf-8')
manifest_path = root / '_codex_mcp_work/chatgpt-dev/59910/docs-sync-manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
note = 'mcp/chatgpt/CHATGPT_SUBSCRIPTION_PATH_REVIEW_2026-10-10.md'
if note not in manifest['files']:
    manifest['files'].append(note)
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'checkpoint_updated': True, 'active_research_lane_released': 'Dirt358Modified', 'scoped_docs': len(manifest['files'])}))
