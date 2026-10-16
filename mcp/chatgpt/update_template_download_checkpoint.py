"""Record exact car guidance, real native Sends and remaining adoption gaps."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
here = root / 'mcp/chatgpt'
heading = '## Exact template links and natural follow-ups — Oct10 22:42EDT'
detail = heading + '''

Customer gap: asking where to get the latest template could return dimensions/history instead of a useful download. Shared car-knowledge/core.js now exposes template_download with exact official archive, recorded HTTP check time, up to five inspected PSD document names/dimensions/hashes and explicit latest/current-file/UV limits.188 exact official ZIP links; four models with unavailable/custom-paint-disabled references gain no sibling download. Exact car/variant choice and custom-paint restrictions retain precedence. No fresh download/network check is claimed: recorded HTTP dates are not installed-build revision evidence. The guide explains extracting/opening the matching PSD and preserving an existing paint before replacing its source; compatibility is not inferred.

Offline car-knowledge/offline-answer.js answers natural download/newest questions with a source-card link and useful opening steps, preserving history queries separately. “Where can I get it?”/“How do I open that template?” retain the actual prior car reference only within the same committed document. Source change, missing scoped answer, ambiguous family or mixed edit cannot borrow that target. Internal applicability tags are kept out of the customer prose. assistant-context.cjs gives both subscription assistants the same structured guide and explicit stored-versus-fresh evidence rule. test_template_download.cjs exercises all192 references/188 allowed links, malformed/unverified links, actual generated Offline route, follow-up/document invalidation, ambiguity, restrictions and history. Existing car/assistant-context checks pass.

Native private Chrome59910:4 actual Offline Sends cover latest Mini Stock archive, pronoun follow-up, exact asphalt rear-sponsor artwork history and a distinct PSD revision question. Expanded Reference details and sources exposes the exact official ZIP hyperlink; actual screenshot captured. The answer does not certify latest template; history stays separate from unverified PSD revision. A real native ChatGPT Send starts exactly one installed ChatGPT-authenticated gpt-6.1-sol read-only model, receives fresh exact question/current paint/shared template_download and replies in app with the official ZIP, recorded Oct9 check date and correct “not verified latest/no fresh check” limit. It gives actual Open Paint→Layered template steps and distinguishes the open ARCA source from the named Mini Stock reference. Draft retained while Sending acknowledgement is pending. Both phases preserve eight exposed paint fields and both original project hashes; observed DOM history/layers/selection unchanged. No paint/edit/render/save/API fallback/outside post/new project. Bounded worker stops after batch_limit; an earlier idle controller stopped connection_off during provider selection, then was explicitly restarted only after verified terminal state. This illustrates the still-open customer startup/wake gap.

Evidence: template-download-native-acceptance.json binds29 native/MCP/worker/implementation artifacts; verify_template_download_native.py checks them. Actual worker subscription-listener-turn-2026-10-11T02-39-10-011Z.json has exactly wait/context/reply and shown_in_app:true. Current standalone/common context receipt template-download-mcp-2026-10-11T02-35-36-730Z.json; probe_mcp.cjs --template-download-only performs zero model/paint reads. Native source-card/answer screenshots and first/follow-up/history/revision/sent text are under private59910. Exposed-state preservation is not full raster/simulator validation. Installed Claude and packaged/shared adoption remain open; do not market private acceptance as shipping availability.

Mini Stock primary research: reused researcher, three official sources,15 artifacts independently checked with exact headings. One2024S4P2 rear-sponsor paint-artwork history note belongs to asphalt ministock, not dirtministock. Official launch binds Asphalt Oval identity;2026S1 Mini Stock has setup changes only, neighboring Dallara template update excluded. No current sponsor placement, forced/removable decals, editable controls, downloadable PSD revision, latest-version/compatibility or UV claim. integrate_ministock.py/test_ministock_history.cjs and parent-review.json retain evidence. Corpus291 facts (207 metadata/80 official documentation/4 secondary),63 records beyond metadata/129 metadata-only;192 records/188 inspected templates/zero verified UV maps. Knowledge SHA1c3fbf732e35423974d77b366d848e5670106bdd8344ba6a4efbf709c79e9a77.

Claude adoption: review the owned common core/offline-answer/assistant-context files and exact current generated caller patches together; keep source-card rendering and same-document reference follow-ups. Shared sources are read-only here. Next customer gaps: automatic startup/wake/reconnect and limit fallback, clickable source links in connected replies, supported edits without uncertain replay, installed Claude parity and package acceptance. Main goal ACTIVE through Oct11 13:38:35UTC. Two original fixtures only.

'''
for name in ['REPORT.md', 'SMARTER_AI.md', 'REQUESTS_FOR_CLAUDE.md']:
    p = here / name
    text = p.read_text(encoding='utf-8')
    if heading not in text:
        p.write_text(detail + text, encoding='utf-8')
p = here / 'SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md'
text = p.read_text(encoding='utf-8')
if heading not in text:
    marker = '## Measured continuation work\n'
    assert marker in text
    p.write_text(text.replace(marker, marker + '\n' + detail, 1), encoding='utf-8')
p = here / 'car-knowledge/README.md'
text = p.read_text(encoding='utf-8')
if heading not in text:
    p.write_text(heading + '\n\nShared exact template-download guide:188 official archive links with recorded check dates, PSD choices and unverified latest/current-file/UV status.4 native Offline Sends +1 actual native plan-backed answer consume the guide;8 exposed paint fields/two project hashes exact. Source link/follow-up and history-versus-PSD distinction measured; private acceptance/adoption limits in current checkpoint. Mini Stock asphalt-only historical rear-sponsor note:15 parent-verified artifacts/three sources; no current placement/control/revision/compatibility or UV rule. See integrate_ministock.py/test_ministock_history.cjs and research/ministock_primary/parent-review.json.291 facts/63 records beyond metadata/129 metadata-only;192 records/188 templates/zero UV.\n\n' + text, encoding='utf-8')
p = root / 'SPB_WIKI.html'
text = p.read_text(encoding='utf-8')
lines = text.splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.startswith('| **Codex — sixteen-hour AI / Offline Helper improvement**'):
        lines[i] = '| **Codex — sixteen-hour AI / Offline Helper improvement** | Owner window ends Oct11 09:38EDT/13:38UTC; smarter online/Offline assistance. | `mcp/chatgpt/**`, private59910, scoped Wiki/docs; Claude runtime read-only. | ACTIVE22:42EDT — exact template guide/link/follow-up:4 native Offline Sends +1 native ChatGPT-plan answer pass,8 paint fields/two fixtures exact;29 frozen artifacts.291 facts/63 beyond metadata/129 metadata-only; zero UV. Next: customer startup/reconnect, connected source links, supported writes and Claude/package adoption. | 2026-10-10 |\n'
text = ''.join(lines)
start = text.index('### 2026-10-10 - Codex: AI and Offline Helper')
end = text.index('\n### ', start + 5)
entry = text[start:end]
entry = entry.replace(entry.splitlines()[0], '### 2026-10-10 - Codex: AI and Offline Helper (updated 22:42EDT)', 1)
old = next(line for line in entry.splitlines() if line.startswith('- Native intelligence:'))
entry = entry.replace(old, '- Native intelligence: previous4 named-material Offline Sends/1 native ChatGPT answer retained. New4 template-reference Offline Sends +1 native ChatGPT-plan answer: exact ZIP/source-card link, scoped pronoun follow-up, asphalt artwork history distinct from PSD revision and explicit unverified latest status. New structured guide consumed by actual model;8 paint fields/two original fixture hashes exact.29 frozen artifacts verified by `verify_template_download_native.py`. No edits/renders/new saves/API fallback. Shared/package/Claude adoption open.')
old = next(line for line in entry.splitlines() if line.startswith('- Car knowledge:'))
entry = entry.replace(old, '- Car knowledge:192 exact records/188 inspected templates/zero verified UV maps;291 facts,63 beyond metadata/129 metadata-only. Asphalt Mini Stock15 artifacts/three primary sources parent-checked; one dated rear-sponsor artwork-history note, Dirt/neighboring Dallara facts excluded. No current placement/control/PSD revision/compatibility claim.188 exact official ZIP guides, stored check time/PSD choices/latest unverified; actual common MCP context/Offline/ChatGPT uptake verified. Research lane released.')
old = next(line for line in entry.splitlines() if line.startswith('- Cleanup/sync:'))
entry = entry.replace(old, '- Cleanup/sync: scoped42 documentation/depth/review mirrors current; no runtime adoption implied. All bounded model/proof processes terminal. Two original fixtures only. Next: customer startup/wake/reconnect/limit fallback, clickable connected source links and supported editing without replay; Claude requests contain exact review files/limits. Main goal incomplete; stop/delete continuation and report measured gaps at deadline.')
p.write_text(text[:start] + entry + text[end:], encoding='utf-8')
mp = root / '_codex_mcp_work/chatgpt-dev/59910/docs-sync-manifest.json'
manifest = json.loads(mp.read_text(encoding='utf-8'))
for name in ['mcp/chatgpt/car-knowledge/research/oval/ministock_primary_2026-10-10/REVIEW.md',
    'mcp/chatgpt/car-knowledge/research/ministock_primary/parent-review.json']:
    if name not in manifest['files']:
        manifest['files'].append(name)
mp.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'native_offline_sends': 4, 'native_model_turns': 1, 'corpus_facts': 291,
    'research_lane_released': 'asphalt Mini Stock', 'scoped_docs': len(manifest['files'])}))
