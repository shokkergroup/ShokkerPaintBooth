"""SPB-AI 2026-10-01: local Codex setup; never replace another MCP entry."""
import json
import os
from pathlib import Path
import tempfile
import threading
import tomllib
from server_routes.codex_knowledge import knowledge_status
from server_routes.codex_runtime import resolve_runtime

_LOCK = threading.Lock()
NAME = 'shokker-paint-booth'


def setup_payload(mcp_dir, port):
    port = str(int(port))
    if not 1 <= int(port) <= 65535:
        raise ValueError('Invalid SPB port')
    server = Path(mcp_dir) / 'server' / 'index.js'
    runtime = resolve_runtime(mcp_dir, os.environ.get('SPB_MCP_ELECTRON_EXE'))
    node = runtime.get('command')
    runtime_env = runtime.get('env', {})
    knowledge = knowledge_status(mcp_dir, node, runtime_env)
    ready = bool(runtime.get('ready') and server.is_file() and knowledge.get('ready'))
    cfg_dir = Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')
    quote = lambda value: json.dumps(str(value), ensure_ascii=False)
    block = ('[mcp_servers.' + NAME + ']\ncommand = ' + quote(node or 'node') +
             '\nargs = [' + quote(server.as_posix()) + ']\nstartup_timeout_sec = 20\n'
             'tool_timeout_sec = 200\n\n[mcp_servers.' + NAME + '.env]\nSPB_PORT = ' + quote(port) + '\n')
    block += ''.join(key + ' = ' + quote(value) + '\n' for key, value in runtime_env.items())
    # PowerShell single-quoted literals escape apostrophes by doubling them.
    ps = lambda value: "'" + str(value).replace("'", "''") + "'"
    command = 'codex mcp add ' + NAME + ' --env SPB_PORT=' + str(port) + ''.join(' --env ' + ps(key + '=' + value) for key, value in runtime_env.items()) + ' -- ' + ps(node or 'node') + ' ' + ps(server.as_posix())
    return {'ok': True, 'ready': ready, 'knowledgeReady': bool(knowledge.get('ready')), 'knowledge': knowledge, 'nodeFound': bool(node), 'runtime': runtime,
            'serverFound': server.is_file(), 'configPath': str(cfg_dir / 'config.toml'),
            'config': block if ready else '', 'command': command if ready else '',
            'commandNote': ('The CLI command sets the runtime and environment. Also apply startup_timeout_sec = 20 and tool_timeout_sec = 200 from the shown TOML.' if ready else ''),
            'message': ('SPB’s bundled knowledge is ready. Sign into Codex with ChatGPT and choose your model there; plan limits apply.' if ready else knowledge.get('message', 'SPB setup is incomplete.'))}


def install_setup(payload):
    if not payload['ready']:
        return {'ok': False, 'ready': False, 'knowledge': payload.get('knowledge'), 'message': payload.get('message', 'SPB setup is incomplete. Update or repair SPB.')}
    target = Path(payload['configPath'])
    with _LOCK:
        original = target.read_bytes() if target.exists() else b''
        text = original.decode('utf-8-sig')
        parsed = tomllib.loads(text)
        existing = parsed.get('mcp_servers', {}).get(NAME)
        desired = tomllib.loads(payload['config'])['mcp_servers'][NAME]
        if existing is not None:
            return {'ok': existing == desired, 'alreadyConfigured': existing == desired,
                    'message': 'SPB is already configured. Restart Codex to connect.' if existing == desired else
                    'An SPB entry already exists. It was preserved; use the shown config to update it manually (including tool_timeout_sec = 200).'}
        updated = original + (b'\n' if original else b'') + payload['config'].encode('utf-8')
        tomllib.loads(updated.decode('utf-8-sig'))
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='spb-codex-', suffix='.toml', dir=target.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(updated)
                stream.flush()
                os.fsync(stream.fileno())
            # Refuse a concurrent change instead of silently overwriting it.
            if (target.read_bytes() if target.exists() else b'') != original:
                return {'ok': False, 'message': 'Codex settings changed during setup. Please try again.'}
            if original:
                backup = target.with_name('config.toml.spb-backup')
                # SPB-AI 2026-10-02: reconnect after removing the SPB entry
                # without overwriting the first backup or failing on its name.
                try:
                    backup_fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    backup_fd, _ = tempfile.mkstemp(prefix='config.toml.spb-backup-', dir=target.parent)
                with os.fdopen(backup_fd, 'wb') as stream:
                    stream.write(original)
                    stream.flush()
                    os.fsync(stream.fileno())
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return {'ok': True, 'message': 'SPB connection added. Restart Codex, sign in with ChatGPT, then choose your model in Codex.'}
