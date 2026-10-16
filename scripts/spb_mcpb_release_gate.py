"""Release gate for the bundled Claude Desktop connector (mcp/shokker-paint-booth.mcpb).  [Claude BETA-READINESS 2026-10-13]

Why: the .mcpb was built by hand on the dev PC; one installer carried an older .mcpb than electron-app/server/mcp/,
and the manifest advertised 31 tools while the server exposes 38. Nothing in the release flow noticed.
Plan: docs/BETA_CLAUDE_SETUP_PLAN_2026-10-12.md item B. Wired into scripts/spb_release_preflight.js (all phases).

Checks (non-zero exit = blocked):
  1. both copies exist (mcp/ and electron-app/server/mcp/) and are byte-identical
  2. manifest version == electron-app/package.json version (the app compares them to show the Update banner)
  3. every packaged file equals its source in electron-app/server/ (the archive is not stale)
  4. the packaged entry starts on plain Node from an EXTRACTED copy (no dev tree, app not running, auto-launch off)
     and tools/list == the manifest's tool list
  5. --mode=prestage: the .mcpb inside electron-app/dist/win-unpacked equals the fresh one (installer not stale)
Usage: python scripts/spb_mcpb_release_gate.py [--mode=prebuild|prestage] [--json]
"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path

R = Path(__file__).resolve().parents[1]
NAME = 'shokker-paint-booth.mcpb'
ROOT_MCPB, SERVER_MCPB = R / 'mcp' / NAME, R / 'electron-app' / 'server' / 'mcp' / NAME
UNPACKED_MCPB = R / 'electron-app' / 'dist' / 'win-unpacked' / 'resources' / 'server' / 'mcp' / NAME
mode = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--mode=')), 'prebuild')
rows = []

def check(name, ok, detail=''):
    rows.append({'name': name, 'ok': bool(ok), 'detail': detail})
    return ok

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def tools_list(entry_dir):
    """initialize + tools/list over stdio against the extracted archive; the app is NOT running (dead port)."""
    env = dict(os.environ, SPB_PORT='1', SPB_AUTOLAUNCH_OFF='1', SPB_MCP_TOKEN_FILE=str(Path(entry_dir) / 'no-token.txt'))
    msgs = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'spb-release-gate', 'version': '1'}}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}]
    node = os.environ.get('SPB_NODE_BIN') or shutil.which('node')
    if not node: raise RuntimeError('no node on PATH (set SPB_NODE_BIN)')
    p = subprocess.Popen([node, str(Path(entry_dir) / 'mcp' / 'server' / 'index.js')], cwd=entry_dir, env=env,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        out, _ = p.communicate(''.join(json.dumps(m) + '\n' for m in msgs).encode(), timeout=45)
    except subprocess.TimeoutExpired:
        p.kill(); out, _ = p.communicate()
    for line in out.decode('utf-8', 'replace').splitlines():
        try: msg = json.loads(line)
        except ValueError: continue
        if msg.get('id') == 2:
            return sorted(t['name'] for t in msg['result']['tools'])
    raise RuntimeError('no tools/list reply; stdout head: %r' % out[:300])

def main():
    app_ver = json.loads((R / 'electron-app' / 'package.json').read_text(encoding='utf-8'))['version']
    if not check('connector present in mcp/ and electron-app/server/mcp/', ROOT_MCPB.exists() and SERVER_MCPB.exists(),
                 'run: python scripts/build_mcpb.py && node scripts/sync-runtime-copies.js --write'):
        return
    check('both connector copies identical', sha(ROOT_MCPB) == sha(SERVER_MCPB), 'run: node scripts/sync-runtime-copies.js --write')
    z = zipfile.ZipFile(SERVER_MCPB)
    man = json.loads(z.read('manifest.json'))
    check('connector version == app version (%s)' % app_ver, man.get('version') == app_ver,
          'manifest says %s; rebuild: python scripts/build_mcpb.py' % man.get('version'))
    stale, missing = [], []
    for n in z.namelist():
        if n.endswith('/') or n in ('manifest.json', 'icon.png'): continue
        src = R / 'mcp' / 'README.md' if n == 'README.md' else R / 'electron-app' / 'server' / n   # build_mcpb.py packs mcp/README.md at the archive root
        if not src.exists(): missing.append(n)
        elif hashlib.sha256(z.read(n)).hexdigest() != sha(src): stale.append(n)
    check('every packaged file matches electron-app/server (%d files)' % len(z.namelist()), not stale and not missing,
          ('stale: %s ' % stale[:8] if stale else '') + ('no source: %s' % missing[:8] if missing else '') + ' -> rebuild: python scripts/build_mcpb.py')
    tmp = tempfile.mkdtemp(prefix='spb_mcpb_gate_')
    try:
        z.extractall(tmp)
        try:
            served = tools_list(tmp)
            listed = sorted(t['name'] for t in man.get('tools', []))
            check('extracted connector starts and lists %d tools' % len(served), len(served) > 0)
            check('manifest tool list == server tools/list', served == listed,
                  'only in server: %s; only in manifest: %s' % (sorted(set(served) - set(listed)), sorted(set(listed) - set(served))))
        except Exception as e:
            check('extracted connector starts and lists tools', False, str(e)[:400])
    finally:
        z.close(); shutil.rmtree(tmp, ignore_errors=True)
    if mode == 'prestage':
        check('installer build carries the fresh connector (win-unpacked)', UNPACKED_MCPB.exists() and sha(UNPACKED_MCPB) == sha(SERVER_MCPB),
              'rebuild the installer after: python scripts/build_mcpb.py')

main()
ok = all(r['ok'] for r in rows)
if '--json' in sys.argv: print(json.dumps({'ok': ok, 'mode': mode, 'checks': rows}, indent=1))
else:
    for r in rows: print(('PASS  ' if r['ok'] else 'FAIL  ') + r['name'] + ('' if r['ok'] or not r['detail'] else '\n      ' + r['detail']))
    print('MCPB gate %s' % ('passed' if ok else 'BLOCKED'))
sys.exit(0 if ok else 1)
