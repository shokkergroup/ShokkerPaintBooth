"""Proposed scripts/mcpb_knowledge_package.py: package the validated prepared tree."""
import hashlib
import json
from pathlib import Path, PurePosixPath

def add_runtime(archive, server_root, plan_path):
    root = Path(server_root).resolve(strict=True)
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8'))
    manifest_path = root / 'mcp/runtime-knowledge-manifest.json'
    raw = manifest_path.read_bytes()
    if len(raw) > 262144:
        raise ValueError('Knowledge manifest too large')
    manifest = json.loads(raw)
    if plan.get('schema') != 'spb-runtime-knowledge-plan/1' or manifest.get('schema') != 'spb-runtime-knowledge-manifest/1':
        raise ValueError('Invalid knowledge schemas')
    files = manifest.get('files', [])
    names = [item['path'] for item in files]
    required = plan['required_files']
    if not names or len(names) > 2000 or len(set(names)) != len(names) or len(set(required)) != len(required) or set(names) != set(required):
        raise ValueError('Incomplete or duplicate knowledge inventory')
    if manifest.get('roles') != plan.get('roles') or manifest.get('server_version') != plan.get('server_version'):
        raise ValueError('Knowledge roles/version differ from release plan')
    validated = []
    for item in files:
        name = item['path']
        rel = PurePosixPath(name)
        if not isinstance(name, str) or '\\' in name or ':' in name or rel.is_absolute() or any(part in ('', '.', '..') for part in name.split('/')):
            raise ValueError('Invalid portable knowledge path')
        target = (root / name).resolve(strict=True)
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError('Knowledge file escapes prepared tree')
        data = target.read_bytes()
        if len(data) > 32 * 1024 * 1024 or len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Prepared knowledge changed: ' + name)
        validated.append((name, data))
    # Validate every byte before writing any runtime member; archive paths preserve imports.
    for name, data in validated:
        archive.writestr(name, data)
    archive.writestr('mcp/runtime-knowledge-manifest.json', raw)
    return len(validated)
