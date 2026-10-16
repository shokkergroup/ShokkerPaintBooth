"""Freeze exact candidate evidence for native car-scoped suggestion cards."""
from pathlib import Path
import hashlib
import json
import sys

root = Path(__file__).resolve().parents[2]
out = root / '_codex_mcp_work/chatgpt-dev/59910'
here = root / 'mcp/chatgpt'
bundle = out / 'reference-suggestions-native-bundle'
receipt = out / 'reference-suggestions-native-acceptance.json'

def obj(name):
    return json.loads((out / name).read_text(encoding='utf-8'))

def panel(name):
    return (out / name).read_text(encoding='utf-8').split('- generic "Drag to move":')[-1]

before, after = [obj('named-material-native-arca-suggestions-' + p + '.json') for p in ['before', 'after']]
assert before['port'] == after['port'] == 59910
assert before['paint'] == after['paint'] and len(before['paint']) == 8
assert before['fixture_hashes'] == after['fixture_hashes'] and len(before['fixture_hashes']) == 2
asphalt = panel('reference-suggestions-native-asphalt.txt')
assert 'button "📖 Mini Stock — template reference' in asphalt
assert 'Dirt Mini Stock — template reference' not in asphalt
assert 'Mini Stock: parts and folder' not in asphalt
assert 'Choosing the right template for your car' in asphalt
dirt = panel('reference-suggestions-native-dirt.txt')
assert 'button "📖 Dirt Mini Stock — template reference' in dirt
assert 'button "📖 Mini Stock — template reference' not in dirt
assert 'Mini Stock: parts and folder' in dirt
answer = panel('reference-suggestions-native-answer.txt')
assert 'Mini Stock.psd (2048 × 2048)' in answer
assert 'built-in guidance · no AI used' in answer
historical = panel('relay-transport-native-offline.txt')
assert 'Mini Stock — template reference' in historical and 'Dirt Mini Stock — template reference' in historical
test = obj('reference-suggestions-components.json')
assert test['pass'] and test['records'] == 192 and test['paint_actions'] == 0
names = ['reference-suggestions-native-asphalt.txt', 'reference-suggestions-native-dirt.txt',
         'reference-suggestions-native-answer.txt', 'reference-suggestions-native-asphalt.jpg',
         'reference-suggestions-native-dirt.jpg', 'reference-suggestions-components.json',
         'named-material-native-arca-suggestions-before.json', 'named-material-native-arca-suggestions-after.json',
         'relay-transport-native-offline.txt']
for name in names:
    if name.endswith('.jpg'):
        assert (out / name).read_bytes().startswith(b'\xff\xd8\xff')
sources = ['reference_suggestion_edits.py', 'test_reference_suggestions.cjs',
           'candidates/spb-offline-answer.js', 'candidates/spb-pbn.js', 'candidates/spb-pro-ai.js']
if '--freeze' in sys.argv:
    assert not receipt.exists(), 'Existing acceptance must never be silently replaced'
    bundle.mkdir(exist_ok=True)
    for source in sources:
        (bundle / Path(source).name).write_bytes((here / source).read_bytes())
files = [out / n for n in names] + [bundle / Path(n).name for n in sources]
hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
if '--freeze' in sys.argv:
    receipt.write_text(json.dumps({'schema': 'spb-reference-suggestions-native-acceptance/1',
        'native_offline_sends': 1, 'native_suggestion_queries': 2, 'model_inferences': 0,
        'paint_fields': 8, 'original_fixtures': 2, 'artifact_hashes': hashes,
        'limits': ['Private staged Offline UI; connected caller component tested, no new native model turn.',
            'Legacy pages scoped only when an explicit article/summary folder is available; no geometry acceptance.',
            'Comparison guard retains search alternatives; shared two-car resolver defect remains open.',
            'Historical wrong-card snapshot is from the prior transport test, not a fresh same-session baseline.',
            'Exposed state preservation, not full raster or packaged/installed Claude acceptance.']}, indent=2) + '\n', encoding='utf-8')
assert obj(receipt.name)['artifact_hashes'] == hashes
print(json.dumps({'pass': True, 'native_suggestion_queries': 2, 'native_offline_sends': 1,
    'model_inferences': 0, 'paint_fields_unchanged': 8, 'fixtures_unchanged': 2, 'frozen_artifacts': len(hashes)}))
