"""Archive repetitive notes exactly; publish a bounded, current coordination slice."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[2]
here = root / 'mcp/chatgpt'
archive = here / 'archive/2026-10-10-2305-ai-checkpoint'
names = ['REPORT.md', 'SMARTER_AI.md', 'REQUESTS_FOR_CLAUDE.md', 'SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md']
archive.mkdir(exist_ok=True)
manifest_path = archive / 'manifest.json'
if not manifest_path.exists():
    hashes = {}
    for name in names:
        raw = (here / name).read_bytes()
        (archive / name).write_bytes(raw)
        hashes[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    manifest_path.write_text(json.dumps({'schema': 'spb-checkpoint-archive/1', 'files': hashes}, indent=2) + '\n', encoding='utf-8')
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
for name, entry in manifest['files'].items():
    raw = (archive / name).read_bytes()
    assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256']

common = '''Updated Oct10 22:56EDT. Owner window ends **Oct11 13:38:35UTC /09:38:35EDT**; goal ACTIVE. Private59910 only. Shared Claude AI/MCP/UI source read-only; exact reviewable patches under mcp/chatgpt. No API credits, outside posts or new project-save variants; two original reusable fixtures retained. At deadline stop, delete continuation and report measured outcomes/gaps.

'''
archive_note = '''The full preceding notes are preserved byte-for-byte in [the checkpoint archive](archive/2026-10-10-2305-ai-checkpoint/manifest.json). This compact slice describes current priorities; historical acceptance details and unresolved earlier adoption requests remain available there. Source archive is canonical, not a runtime feature.
'''
report = '''# AI and Offline Helper — current measured status

''' + common + '''Native connected source links now pass: one actual installed ChatGPT-plan gpt-6.1-sol question/reply renders a friendly clickable official Mini Stock ZIP link. The model says latest revision is unverified and reports the stored Oct9 check, not a fresh download. Eight exposed paint fields, DOM history/layers/selection and both original fixture hashes remain exact; no link click/download. Worker exits after one batch, API fallback false. `verify_answer_links_native.py` binds10 artifacts; screenshot `answer-links-native-answer.jpg` under private59910. Both providers pass the common formatter component tests; installed Claude/shared/package adoption remains open.

Retained current native proof: eight named-material/template Offline Sends and two actual subscription answers, plus this new third connected answer. Named-layer reads distinguish duplicate/missing/hidden/unreadable state without substituting selection. Template guide supplies188 exact official ZIPs with recorded checks, PSD choices and latest/current-file/UV limits. Same-document pronoun follow-ups preserve exact reference identity; history questions remain distinct from PSD revision. Native proof is bounded by the measured questions, not a general accuracy score.

Online ownership/stop proof passes two actual idle starts/stops, distinct instances and ignored old stop; zero inference, pending questions/two fixtures exact. Actual read-only pending recovery uses one model; explicit recovery prevents uncertain replay. Customer automatic startup/wake/reconnect, limit fallback and supported editing recovery remain open. A recorded process/PID or prior reply never proves current availability.

Car corpus unchanged:192 exact records,188 inspected templates,291 facts (207 metadata/80 official documentation/4 secondary);63 records beyond metadata,129 metadata-only, zero verified UV maps. Ford Mustang GT3 research:15 artifacts/three primary sources parent-checked; three historical proposals awaiting integration, not counted. Banner-display repair is not a Paint Shop preview change; no current decal controls/template version/compatibility/geometry inferred.

Prior private recolour/opacity/Undo, protected artwork, source-bound refusal, template reading and kit guidance evidence retained. Native assigned-material/unreadable positives, taught-mask positive, import-switch, real-car output and installed/package/Claude parity remain gaps. Do not market staged tests as shipping availability.

Next narrow customer gate: fresh startup/reconnect and retained drafts through unavailable provider/usage limits; avoid repeated model polling. Keep online and Offline using the same current-document capability/evidence context. Detailed proof index: [checkpoint](SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md).

''' + archive_note
requests = '''# Requests for Claude — current adoption priorities

''' + common + '''1. Review `answer_links_edits.py`, `test_answer_links.cjs` and `candidates/spb-pro-ai.js.patch`: shared fmt renders bounded HTTPS bare/simple Markdown links for both providers. Keeps old escaping/bold/newlines; rejects credentials/backslashes/nonstandard ports, limits12 links, uses escaped attributes and noopener noreferrer. Flag `SPB_ANSWER_LINKS_OFF` restores old formatting. No fetch/download/paint dispatch. Actual native ChatGPT proof: `verify_answer_links_native.py`; native Claude and packaged acceptance still required. Rebuild25 candidates and check source hashes before applying; do not apply an old whole generated file over current shared work.

2. Customer startup/wake/reconnect is still the largest online gap. Your push-wake/Stop-listening work and our `subscription-control.cjs`/`subscription-listener.cjs` should share exact instance ownership, retained drafts and explicit delivery state. Two idle process cycles pass with zero models; bounded plan-backed replies/recovery pass. PID presence does not certify readiness. No automatic stale-lock removal, credential copying, API fallback, or uncertain edit replay. Test disconnected/limit cases from actual AI-button entry, not a developer-only CLI.

3. Adopt shared `car-knowledge/core.js` template_download, `car-knowledge/offline-answer.js`, `assistant-context.cjs` and exact caller patches together.188 recorded official archive links, document choices and unverified latest/current-file/UV status. Same committed document alone may retain prior exact reference; ambiguous families/mixed edits/source changes must not borrow it. Four template Offline questions and one native plan answer pass, separately from the new source-link answer.

4. Preserve named-layer material reader/focused context, stale-document/action preflight, delivery-confirmed drafts, actual receipt Undo, named-part geometry refusal and kit menu discovery. Earlier detailed requests—including J10/live-car shortcut guards, J02 relative recolour and kit provenance—remain in the linked archive. Current common retrieval must distinguish requested car from open paint; no catalog-to-UV inference.

5. Connected reply still displayed Dirt Mini Stock/Encyclopedia suggestion chips during an exact asphalt Mini Stock question. Model/context/link were correct; inspect suggestion scoping before presenting those chips as relevant. Native Claude parity, startup/limit fallback, supported writes/recovery and package acceptance are open. Keep shared Wiki status honest about staged versus shipped.

Ford GT3 proposals parent verified but not promoted; if integrating, classify camera-distance banner repair as display history, not Paint Shop preview. Three dated notes establish no current restrictions, latest PSD, controls, compatibility or UV.

''' + archive_note
strategy = '''# Shared intelligence strategy — current lane

''' + common + '''Prioritize what a customer reaches by clicking AI in the full editor: actual current document and requested car, useful conversation, a retained draft when connection/usage fails, and safe small edits with truthful receipt/Undo. Subscription-backed providers and subscription-free Offline answers should consume the same bounded capability/car evidence rather than maintain competing manuals. Preserve exact identity across follow-ups; confidence should track evidence and current scope.

Recent measured improvement is useful template acquisition:188 exact source links and opening steps, separate history/revision/latest status, natural follow-ups, and readable connected hyperlinks. Offline native8 questions/online3 actual answers cover named material/template/link cases; they are case evidence, not a spectacular-AI claim. Common formatter tests cover both providers; Claude native adoption remains open.

Next highest-value work is startup/wake/reconnect and provider-limit continuity, followed by supported edits with no uncertain replay. Current bounded subscription worker/ownership tests are preparation for customer lifecycle, not a finished service. Sidecar suggestion chips should preserve exact asked-car scope. Continue primary car research only for actionable customer gaps; dated display/artwork history must not become UV/control/latest-version claims.

Keep evidence immutable: the three compiled bundle files consumed by the prior template test are archived under `template-download-native-bundle`; original hashes/receipt retained. Future unrelated facts can grow without re-freezing an old native test against new bytes. Verify current corpus separately. Keep the active handoff short; archive exact older checkpoints with hashes instead of repeating long blocks into every document.

''' + archive_note
checkpoint = '''# Sixteen-hour AI / Offline Helper checkpoint

''' + common + '''## Current proof index

- Connected links: `verify_answer_links_native.py`, `answer-links-native-acceptance.json` (10 artifacts), one real ChatGPT-plan reply; common provider formatting tests `test_answer_links.cjs`. Screenshot `answer-links-native-answer.jpg`.8 exposed paint fields/two fixtures exact, no navigation/download.
- Template acquisition: `verify_template_download_native.py`, `template-download-native-acceptance.json` (29 artifacts):4 native Offline Sends/1 actual plan answer, stored guide and exact source-card link; separate artwork versus PSD history. `test_template_download.cjs`, `test_ministock_history.cjs`, common-context probe;188 guides/all192 identities tested. Historical compiled bundle preserved unchanged with original receipt by `preserve_template_native_bundle.py`.
- Named material: `verify_named_material_native.py`, `named-material-native-acceptance.json` (20 artifacts):4 native Offline Sends/1 actual plan answer. Hidden ancestors/duplicates/none/assigned/unreadable/unknown/incomplete IDs tested in components; native fixture material is none.
- Listener lifecycle: `verify_subscription_lifecycle.py`, `subscription-lifecycle-acceptance.json`:2 actual idle starts/stops, matching ownership/old-stop isolation/zero inference. `test_subscription_control.cjs` and `test_subscription_listener.cjs` cover malformed/stale/replacement/claim/busy cases. Earlier actual read-only pending recovery: `verify_subscription_listener.py`; recovery receipt01:42UTC. Bounded workers terminal; automatic startup open.
- Retained earlier source-bound refusals, paint/Undo/protected-artwork, reference conversation and kit guidance: detailed receipts/limits in exact prior checkpoint archive. No installed/packaged/full-raster/simulator acceptance inferred.

Car reference291 facts/63 beyond metadata/129 metadata-only;192 exact cars/188 inspected templates/zero UV. Mini Stock15-artifact exact-asphalt dated sponsor-history promotion retained. Ford Mustang GT3 parent verified15 artifacts;3 historical proposals **not promoted**, including banner display (not Paint Shop), IMSA decal use and a new built-in pattern announcement. Current placement/controls/latest-template/compatibility remain unknown.

Next narrow gates: customer startup/wake/reconnect/usage fallback and retained drafts; supported writes without replay; source-scoped suggestion chips; native Claude/package adoption. Stop/delete active continuation at13:38:35UTC and report measured results/gaps. All processes used for the new link test ended; only two original fixtures retained.

''' + archive_note
for name, text in zip(names, [report, strategy, requests, checkpoint]):
    (here / name).write_text(text, encoding='utf-8')

# Parent audit records evidence without changing facts or the helper-owned review.
review = here / 'car-knowledge/research/road/fordmustanggt3_primary_2026-10-10'
rm = json.loads((review / 'review-manifest.json').read_text(encoding='utf-8'))
for entry in rm['files']:
    raw = (review / entry['name']).read_bytes()
    assert len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256']
parent = here / 'car-knowledge/research/fordmustanggt3_parent_review'
parent.mkdir(exist_ok=True)
(parent / 'parent-review.json').write_text(json.dumps({'schema': 'spb-car-primary-parent-review/1',
    'car_id': 'fordmustanggt3', 'verified_artifacts': 15,
    'manifest_sha256': hashlib.sha256((review / 'review-manifest.json').read_bytes()).hexdigest(),
    'status': 'parent reviewed; proposal only', 'promoted_facts': [], 'proposed_historical_facts': 3,
    'topic_correction_before_promotion': 'Window-banner camera-distance repair is display history, not Paint Shop preview.',
    'exact_headings_checked': ['2024S3P1 GT3 89-98 / Mazda99', '2024S4P2 GT3 67-68 / Hyundai69', '2025S4P2 GT3 88-89 / GT4 90'],
    'current_controls_verified': False, 'latest_template_verified': False, 'verified_uv_maps': 0}, indent=2) + '\n', encoding='utf-8')

p = root / 'SPB_WIKI.html'
text = p.read_text(encoding='utf-8')
lines = text.splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.startswith('| **Codex — sixteen-hour AI / Offline Helper improvement**'):
        lines[i] = '| **Codex — sixteen-hour AI / Offline Helper improvement** | Owner window ends Oct11 09:38EDT/13:38UTC; smarter online/Offline assistance. | `mcp/chatgpt/**`, private59910, scoped Wiki/docs; Claude runtime read-only. | ACTIVE22:56EDT — clickable connected source links:1 actual ChatGPT-plan answer/10 frozen artifacts;8 paint fields/two fixtures exact. Both formatter tests pass; Claude native/adoption open. Prior8 Offline/2 online proofs retained.291 facts/63 beyond metadata/129 metadata-only; zero UV. Next startup/reconnect/limit continuity. | 2026-10-10 |\n'
    if line.startswith('| **Codex research — Ford Mustang GT3**'):
        lines[i] = '| **Codex research — Ford Mustang GT3** | Exact primary paint/display history. | `mcp/chatgpt/car-knowledge/research/road/fordmustanggt3_primary_2026-10-10/**` only. | COMPLETE22:56EDT — parent checked15 hashes/three exact headings;3 historical proposals not promoted. Banner display not Paint Shop preview; no current control/template/UV inference. Lane released. | 2026-10-10 |\n'
text = ''.join(lines)
start = text.index('### 2026-10-10 - Codex: AI and Offline Helper')
end = text.index('\n### ', start + 5)
entry = text[start:end]
entry = entry.replace(entry.splitlines()[0], '### 2026-10-10 - Codex: AI and Offline Helper (updated 22:56EDT)', 1)
for prefix, replacement in [
    ('- Native intelligence:', '- Native intelligence: previous8 named-material/template Offline Sends/2 actual subscription answers retained. New1 real ChatGPT-plan Markdown-link answer displays exact friendly official ZIP hyperlink; stored check/latest-unverified phrasing correct.8 exposed paint fields/DOM/two fixture hashes exact; no click/download/save/API fallback. `verify_answer_links_native.py` binds10 artifacts; screenshot `answer-links-native-answer.jpg`. Both provider formatter components pass; native Claude/shared/package adoption open.'),
    ('- Cleanup/sync:', '- Cleanup/sync: repetitive REPORT/SMARTER_AI/Claude handoff/checkpoint archived byte-for-byte with hashes in `archive/2026-10-10-2305-ai-checkpoint`, current concise notes published. Historical template native bundle archived with original29 artifact hashes retained, no re-freeze against future facts. Ford GT3 parent checked15 artifacts/three headings,3 historical proposals not promoted; banner topic correction noted. Bounded workers terminal; two fixtures only. Scoped documentation sync required after this checkpoint. Next startup/wake/reconnect/usage continuity and source-scoped suggestion chips. Main goal ACTIVE until deadline.')]:
    old = next(line for line in entry.splitlines() if line.startswith(prefix))
    entry = entry.replace(old, replacement, 1)
p.write_text(text[:start] + entry + text[end:], encoding='utf-8')
print(json.dumps({'archived_bytes': sum(x['bytes'] for x in manifest['files'].values()),
    'current_chars': sum(len((here / n).read_text(encoding='utf-8')) for n in names),
    'ford_parent_review_only': True, 'native_link_artifacts': 10}))
