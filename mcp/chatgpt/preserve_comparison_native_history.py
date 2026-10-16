"""Recover the original probe by exact frozen hash; never re-freeze changed bytes."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[2]
out = root / '_codex_mcp_work/chatgpt-dev/59910'
receipt = out / 'template-download-native-acceptance.json'
data = json.loads(receipt.read_text(encoding='utf-8'))
oldkey = 'mcp/chatgpt/car-knowledge/probe_mcp.cjs'
target = out / 'template-download-native-bundle/probe_mcp.cjs'
newkey = target.relative_to(root).as_posix()
expected = data['artifact_hashes'].get(oldkey, data['artifact_hashes'].get(newkey))
assert expected
if not target.exists():
    # The only new block was inserted before the existing template-only block.
    # Reconstruction is accepted only if byte-exact against the prior SHA256.
    source = (root / oldkey).read_bytes().decode('utf-8')
    start = source.index("  if(process.argv.includes('--comparison-only'))")
    end = source.index("  if(process.argv.includes('--template-download-only'))", start)
    old = source[:start] + source[end:]
    lf = old.replace('\r\n', '\n')
    candidates = [old.encode('utf-8'), lf.encode('utf-8'), lf.replace('\n','\r\n').encode('utf-8')]
    correct = next((raw for raw in candidates if hashlib.sha256(raw).hexdigest() == expected), None)
    assert correct is not None, 'No byte-exact historical probe can be recovered'
    target.write_bytes(correct)
assert hashlib.sha256(target.read_bytes()).hexdigest() == expected
if oldkey in data['artifact_hashes']:
    data['artifact_hashes'][newkey] = data['artifact_hashes'].pop(oldkey)
data['historical_bundle_archive']['paths'][oldkey] = newkey
receipt.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print('Original probe recovered by frozen SHA256; relocated only, no re-freeze.')
