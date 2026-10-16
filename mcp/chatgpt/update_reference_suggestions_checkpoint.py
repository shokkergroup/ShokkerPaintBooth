"""Bounded current checkpoint; preserve other agents' Wiki sections."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
here = root / 'mcp/chatgpt'
stamp = '23:21EDT'
note = ('Oct10 '+stamp+': [Exact-car suggestion acceptance](REFERENCE_SUGGESTIONS_ACCEPTANCE.md) passes: '
        'asphalt/dirt native chips scoped, misleading dirt-folder legacy card excluded from asphalt, '
        'cached query rechecked;1 native Offline Send/0 models,8 paint fields/two original fixtures exact,14 frozen artifacts. '
        'Common connected caller/component tests pass. Comparison answers remain a separate open identity defect. '
        'Current measured material/template/link/continuity/suggestion cases:10 native Offline Sends/3 actual online answers. '
        'Dirt Big Block research parent checked16 artifacts/three sources; one family-history proposal, not promoted.\n\n')
for name in ['REPORT.md','SMARTER_AI.md','REQUESTS_FOR_CLAUDE.md','SIXTEEN_HOUR_CHECKPOINT_2026-10-10.md']:
    p = here / name
    text = p.read_text(encoding='utf-8')
    anchor = '\n\nUpdated Oct10 22:56EDT.'
    pos = text.index(anchor)
    old_top = text.index('\n\n')
    text = text[:old_top+2] + note + text[pos+2:]
    if name == 'REQUESTS_FOR_CLAUDE.md':
        start = text.index('5. ')
        end = text.index('\n\n',start)
        text = text[:start] + ('5. Review `reference_suggestion_edits.py` and `test_reference_suggestions.cjs`: common exact-car filtering for PBN/connected retrieval, bounded raw cache re-scoped on every use, explicit legacy-folder identity only. Native asphalt/dirt chip tests and one Offline answer pass with8 paint fields/two fixtures exact;14 frozen artifacts. Legacy `car_pages.mini-stock` names dirtministock but omits Dirt in its title; correct that source title in your lane and review its geometry separately. Shared `core.select` still loses asphalt in “Mini Stock vs Dirt Mini Stock”; global modifiers/contained labels need independent mention resolution. Comparison guard keeps article alternatives but does not fix answers. Native Claude/package/startup/usage-limit acceptance remains open.') + text[end:]
    text = text.replace('source-scoped suggestion chips;', 'exact-car comparison resolution;')
    text = text.replace('Sidecar suggestion chips should preserve exact asked-car scope.', 'Sidecar exact-car suggestions now pass privately; next resolve both independent car mentions in comparison questions.')
    p.write_text(text,encoding='utf-8')

p = root / 'SPB_WIKI.html'
text = p.read_text(encoding='utf-8')
start = text.index('| **Codex — sixteen-hour AI / Offline Helper improvement** |')
end = text.index('\n',start)
text = text[:start] + ('| **Codex — sixteen-hour AI / Offline Helper improvement** | Owner window ends Oct11 09:38EDT/13:38UTC; smarter online/Offline assistance. | `mcp/chatgpt/**`, private59910, scoped Wiki/docs; Claude runtime read-only. | ACTIVE'+stamp+' — native asphalt/dirt suggestions/legacy-folder scoping and1 Offline answer pass;14 frozen artifacts,8 paint fields/two fixtures exact,0 models. Connected caller component passes. Separate two-car comparison defect next.291 facts/zero UV; startup/limits/Claude adoption open. | 2026-10-10 |') + text[end:]
text = text.replace('COMPLETE23:22EDT — parent checked16', 'COMPLETE'+stamp+' — parent checked16')
start = text.index('### 2026-10-10 - Codex: AI and Offline Helper (updated ')
head_end = text.index('\n',start)
text = text[:start] + '### 2026-10-10 - Codex: AI and Offline Helper (updated '+stamp+')' + text[head_end:]
insert_at = text.index('\n',start)+1
text = text[:insert_at] + ('- New exact-car suggestions: native asphalt/dirt chips, cached return and one Offline template answer pass;8 exposed paint fields/two original fixtures exact,0 models,14 frozen artifacts. Legacy “Mini Stock: parts and folder” explicitly names dirtministock and is filtered from asphalt. Common connected/PBN callers component-tested; shared/package/native Claude adoption open. [Acceptance](mcp/chatgpt/REFERENCE_SUGGESTIONS_ACCEPTANCE.md). Comparison guard retains alternatives; common two-car answer defect remains OPEN.\n'
    '- Research: Dirt Big Block16 primary artifacts/three sources independently parent-checked; one dated ALL-family contingency timeline proposal, not promoted. 2022 does not name World of Outlaws; no current control/template/UV claim. Completed helper lane recorded retrospectively and released. Corpus unchanged.\n') + text[insert_at:]
text = text.replace('Scoped43 documentation mirrors checked;', 'Scoped44 documentation mirrors checked;')
text = text.replace('Next actual provider-limit handling/customer startup and exact-car suggestion scoping.', 'Next common exact-car comparisons and actual provider-limit/customer startup acceptance.')
marker = '## Known Trouble Spots (OPEN)\n'
assert marker in text
trouble = ('\n### AI exact-car comparisons — OPEN 2026-10-10 '+stamp+'\n'
    '`mcp/chatgpt/car-knowledge/core.js select` currently resolves “Mini Stock vs Dirt Mini Stock” only to Dirt Mini Stock. Whole-query dirt/EVO/etc modifier checks suppress the first independent car; longer-label containment then loses a separate short-name mention. Resolve per-mention identities, keep unknown/ambiguous/negated alternatives explicit, and test common MCP/Offline/online context. Suggestion filtering deliberately retains comparison alternatives; this is not a comparison-answer fix. Legacy `car_pages.mini-stock` title also omits Dirt despite explicit dirtministock folder; Claude source-title/geometry review remains open. No UV inference.\n')
text = text.replace(marker,marker+trouble,1)
p.write_text(text,encoding='utf-8')
manifest = root / '_codex_mcp_work/chatgpt-dev/59910/docs-sync-manifest.json'
data = json.loads(manifest.read_text(encoding='utf-8'))
entry = 'mcp/chatgpt/REFERENCE_SUGGESTIONS_ACCEPTANCE.md'
assert entry not in data['files']
data['files'].append(entry)
manifest.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print('Updated bounded checkpoints, own Wiki lane/log/trouble and44-file documentation scope.')
