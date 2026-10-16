"""Stage the reviewed shared helper delta; never modify Claude's source."""
import difflib
import hashlib
import json
from pathlib import Path
from owner_promotions import function_text

root = Path(__file__).resolve().parents[2]
source = root / 'js/spb-template-layers.js'
owned = root / 'mcp/chatgpt/car-knowledge/layer-reading.js'
evidence = root / '_codex_mcp_work/chatgpt-dev/59910'
baseline = json.loads((evidence / 'focused-layer-shared-baseline.json').read_text(encoding='utf-8'))
raw = source.read_bytes()
if hashlib.sha256(raw).hexdigest() != baseline['sha256']:
    raise RuntimeError('Shared helper changed after baseline; review before rebasing focused-layer delta')
original = raw.decode('utf-8').replace('\r\n', '\n')
new = owned.read_text(encoding='utf-8')
candidate = original
for name in ['read', 'answer', 'hasEditTail']:
    before, after = function_text(original, name), function_text(new, name)
    assert candidate.count(before) == 1, name
    candidate = candidate.replace(before, after, 1)
anchor = '    function read(rows,source,question){'
assert candidate.count(anchor) == 1
candidate = candidate.replace(anchor, function_text(new, 'focusedLayers') + '\n' + function_text(new, 'focusedQuestion') + '\n' + anchor, 1)
anchor = '    function answerReference(question,metadata)'
assert candidate.count(anchor) == 1
candidate = candidate.replace(anchor, function_text(new, 'focusedAnswer') + '\n' + anchor, 1)
anchor = 'materialQuestion:materialQuestion'
assert candidate.count(anchor) == 1
candidate = candidate.replace(anchor, 'focusedLayers:focusedLayers,focusedQuestion:focusedQuestion,' + anchor, 1)
assert hashlib.sha256(source.read_bytes()).hexdigest() == baseline['sha256']
dest = root / 'mcp/chatgpt/candidates/spb-template-layers.js'
dest.write_bytes(candidate.encode('utf-8'))
patch = ''.join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True), fromfile='a/js/spb-template-layers.js', tofile='b/js/spb-template-layers.js'))
dest.with_suffix('.js.patch').write_bytes(patch.encode('utf-8'))
manifest = {'schema': 'spb-focused-layer-delta/1', 'source': 'js/spb-template-layers.js', 'source_sha256': baseline['sha256'], 'candidate_sha256': hashlib.sha256(candidate.encode('utf-8')).hexdigest(), 'shared_source_written': False, 'basis': 'Exact reviewed shared-source baseline; only three functions, three new functions and exports changed.'}
dest.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'staged': str(dest.relative_to(root)), 'shared_source_written': False, 'patch_bytes': len(patch.encode('utf-8'))}))
