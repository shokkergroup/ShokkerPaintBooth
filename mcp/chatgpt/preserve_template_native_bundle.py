"""Relocate measured bundle bytes without re-freezing an old native test."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[2]
out = root / '_codex_mcp_work/chatgpt-dev/59910'
receipt = out / 'template-download-native-acceptance.json'
original = receipt.read_bytes()
data = json.loads(original)
archive = out / 'template-download-native-bundle'
archive.mkdir(exist_ok=True)
prior = archive / 'original-acceptance.json'
if not prior.exists():
    prior.write_bytes(original)
moved = {}
for relative in ['build/knowledge.json', 'build/cars.json', 'build/manifest.json', 'core.js', 'offline-answer.js']:
    name = Path(relative).name
    source = root / 'mcp/chatgpt/car-knowledge' / relative
    target = archive / name
    oldkey = source.relative_to(root).as_posix()
    newkey = target.relative_to(root).as_posix()
    expected = data['artifact_hashes'].get(oldkey, data['artifact_hashes'].get(newkey))
    assert expected
    if not target.exists():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
        target.write_bytes(source.read_bytes())
    assert hashlib.sha256(target.read_bytes()).hexdigest() == expected
    if oldkey in data['artifact_hashes']:
        del data['artifact_hashes'][oldkey]
        data['artifact_hashes'][newkey] = expected
    moved[oldkey] = newkey
paths = dict(data.get('historical_bundle_archive', {}).get('paths', {}))
paths.update(moved)
data['historical_bundle_archive'] = {'original_receipt_sha256': hashlib.sha256(prior.read_bytes()).hexdigest(),
    'paths': paths, 'reason': 'Exact originally measured bytes preserved; no new native test or inference implied.'}
receipt.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'archived_original_bundle_files': len(moved), 'original_hashes_preserved': True}))
