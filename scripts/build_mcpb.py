#!/usr/bin/env python
"""Build mcp/shokker-paint-booth.mcpb (Claude Desktop one-click extension) from mcp/server/*.  SPB-AI 2026-09-30.

  python scripts/build_mcpb.py             pack with the tools.json already in mcp/server
  python scripts/build_mcpb.py --tools [--port N]  (N default 59876)  first refresh tools.json from the LIVE app through the bridge (app open in Pro mode, bridge switched on), then pack

An .mcpb is a zip with manifest.json at the root (manifest_version 0.3, server.type node: Claude Desktop runs it with its own bundled Node, nothing for the buyer to install).
"""
import time, json, os, sys, zipfile, io, urllib.request, subprocess, shutil
from mcpb_knowledge_package import add_runtime
from pathlib import Path
R = Path(__file__).resolve().parents[1]
MCP = R / 'mcp'
def _app_version():          # [S22 2026-10-13 beta Claude setup] the connector version ALWAYS equals the app version (electron-app/package.json): SPB compares the two to tell a stale connector from a current one
    try: return str(json.loads((R / 'electron-app' / 'package.json').read_text(encoding='utf-8'))['version'])
    except Exception as e: raise SystemExit('cannot read the app version from electron-app/package.json: %s' % e)
VERSION = _app_version()          # [S22 2026-10-13 beta Claude setup] was a hand-edited '11.0.0'. History: MCP-KNOW 2026-10-10: server/app-knowledge.cjs (instruction head, description facts, app briefing, verified facts; kill switch SPB_MCPKNOW_OFF). Was '1.4.6'          # OA4 2026-10-10 (ONLINE-AI-4): no server behaviour change; pairs with page js/spb-online-kits.js ok1.4 (spb_kit place result lists named-but-unplaced parts in not_placed + not_placed_note; bank KO-07 + probes KP-01..06). Was 1.4.5: OA3 2026-10-10 (ONLINE-AI-3): spb_kit remove honours the named parts (page ok1.3; found by bank item KO-15: remove took every sponsor kit), kit Undo obeys the BUSY + lease guards, colour_source_note on spb_tweak (brightness on a colour-source zone cannot show), spb_do finish-on-a-part = refinish keep_colour, no '2048 square for every template' claim; kill switch env SPB_OA3_OFF=1 (page window.SPB_KIT_REMOVE_SCOPE_OFF / SPB_KIT_UNDO_GUARD_OFF). Was 1.4.4: 2026-10-10 OA2 (ONLINE-AI-2): CX3 merge shipped (spb_edit_layer colour / colour_opacity = the app's native layer colour overlay, advice-only gate for app-chat, layer identity in the layer list; the colour schema line was moved into allTools()) + spb_kit (online Claude drives the Sponsor Kit, Number Kit, Spec Doctor and Spec Autopilot; kill switch env SPB_ONLINE_KITS_OFF=1; page js/spb-online-kits.js). Was 1.4.3: 2026-10-10 ONLINE-AI (2): render ONCE after the LAST change of a buyer request again (spb_render also takes buyer_asked_render; refused when nothing changed and no ask), render_next reminder on write results, after_render_note only on the false-spill symptom, undo-guard regexes fixed (they held literal 0x08 backspaces since R9: the guard never matched; mcp/test/undo_guard_regex.test.cjs); page side P7/P7b/P7c/P7d in js/spb-intent-report.js (kill switch SPB_P7_OFF). Was 1.4.2: per-kind graphic size / honest rotation / logical undo, finish-scale + brightness retarget to the zone that shows, 2-colour checker, render only when the buyer asks (+ after_render_note), alias-aware part guard; kill switch SPB_ONLINE_AI_OFF=1. Was 1.4.1; 2026-10-09 CX2: spb_assistant_context (server/assistant-context.cjs) + design-conversation instruction. Was 1.4.0; 2026-10-09 APPCHAT: spb_wait_for_message / spb_reply (in-app chat box relays to the assistant) + server/wait-inbox.js. Was 1.3.5; 2026-10-09 W1-MCP: spb_tweak re-draws drawn graphics at a new size, hue tweak rotates solid colours (toward), 2 instruction sentences. Was 1.3.4; 2026-10-08 A-ITER: spb_tweak (same-zone scale/brightness/hue/rotation), working-zone tracking, unknown-part refusal. Was 1.3.3

def refresh_tools(port=59876):
    # 2026-10-07 S8: port is a parameter (--port N, default 59876) so a test server can feed tools.json; SPB_MCP_TOKEN_FILE overrides the token path (same env the server and mcp/server/index.js honour)
    tf = os.environ.get('SPB_MCP_TOKEN_FILE') or str(Path(os.environ.get('APPDATA', str(Path.home()))) / 'ShokkerPaintBooth' / 'mcp' / 'token.txt')
    tok = Path(tf).read_text(encoding='utf-8').strip()
    rq = urllib.request.Request('http://127.0.0.1:%d/api/mcp/call' % int(port), data=json.dumps({'tool': 'list_tools', 'args': {}}).encode(), headers={'Content-Type': 'application/json', 'X-SPB-MCP-Token': tok})
    d = json.loads(urllib.request.urlopen(rq, timeout=60).read().decode('utf-8'))
    tools = d['result']['tools']
    (MCP / 'server' / 'tools.json').write_text(json.dumps(tools, indent=1, ensure_ascii=False), encoding='utf-8')
    print('tools.json refreshed:', len(tools), 'tools')

def icon_bytes():
    try:
        from PIL import Image
        im = Image.open(R / 'assets' / 'branding' / 'ShokkerPaintBooth Logo 2 PNG.png').convert('RGBA')
        w, h = im.size; s = max(w, h); sq = Image.new('RGBA', (s, s), (0, 0, 0, 0)); sq.paste(im, ((s - w) // 2, (s - h) // 2)); sq = sq.resize((512, 512), Image.LANCZOS)
        b = io.BytesIO(); sq.save(b, 'PNG'); return b.getvalue()
    except Exception as e:
        print('no icon:', e); return None

def server_tools(prepared, node, timeout=45):
    """[S22 2026-10-13 beta Claude setup] Run the prepared mcp/server/index.js once over stdio (initialize + tools/list) and return its real tool list [{name, description, ...}].
    Never talks to the app (tools/list is answered locally) and SPB_AUTOLAUNCH_OFF keeps it from starting one. Fails the build rather than shipping a stale or empty list."""
    entry = Path(prepared) / 'mcp' / 'server' / 'index.js'
    if not entry.is_file(): raise SystemExit('server_tools: %s is missing' % entry)
    env = {**os.environ, 'ELECTRON_RUN_AS_NODE': '1', 'SPB_AUTOLAUNCH_OFF': '1', 'SPB_PORT': '59999'}
    p = subprocess.Popen([node, str(entry)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, cwd=str(Path(prepared) / 'mcp' / 'server'))
    try:
        msgs = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'build_mcpb', 'version': '1'}}},
                {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list', 'params': {}}]
        p.stdin.write(''.join(json.dumps(m) + '\n' for m in msgs).encode('utf-8')); p.stdin.flush()
        import threading
        out = {}
        def rd():
            for line in p.stdout:
                try: m = json.loads(line.decode('utf-8'))
                except Exception: continue
                if m.get('id') == 2: out['m'] = m; return
        t = threading.Thread(target=rd, daemon=True); t.start(); t.join(timeout)
        m = out.get('m')
        tools = ((m or {}).get('result') or {}).get('tools') if m else None
        if not tools: raise SystemExit('server_tools: the server did not answer tools/list (%s)' % (m if m else 'timeout'))
        names = [x.get('name') for x in tools]
        if len(set(names)) != len(names) or not all(names): raise SystemExit('server_tools: duplicate or empty tool names: %s' % names)
        return tools
    finally:
        try: p.stdin.close()
        except Exception: pass
        try: p.terminate()
        except Exception: pass


def main():
    port = int(sys.argv[sys.argv.index('--port') + 1]) if '--port' in sys.argv else 59876
    if '--tools' in sys.argv: refresh_tools(port)
    # [S22 2026-10-13 beta Claude setup] the manifest tool list is NOT hand-maintained any more: it is whatever the shipped server answers to tools/list (was a 7-name static list + tools.json = 31 of the real 38 names; the manifest lagged the server).
    # The probe is run below, after the prepared tree and the Node runtime are known (it runs the PREPARED mcp/server/index.js = the file that ships).
    manifest = {
        'manifest_version': '0.3', 'name': 'shokker-paint-booth', 'display_name': 'Shokker Paint Booth', 'version': VERSION,
        'description': 'Connect an MCP-capable assistant to Shokker Paint Booth: shared app knowledge, car references, finishes, layers and preview tools.',
        'long_description': 'Shokker Paint Booth 11.00 shares its bundled app knowledge and reference tools with Claude and ChatGPT/Codex connections. Open Pro mode and enable the AI bridge in AI settings. This MCPB is the Claude desktop extension; Codex uses the app setup flow for the same MCP server. Supported subscription hosts run the conversation through the user account and its limits; SPB needs no separate model API key. Check the actual layers and preview before edits. Car references describe verified facts and limitations; they do not supply calibrated UV geometry. The built-in Offline Helper remains available without an AI subscription.',
        'author': {'name': 'Shokker Group'},
        'icon': 'icon.png',
        'server': {'type': 'node', 'entry_point': 'server/index.js', 'mcp_config': {'command': 'node', 'args': ['${__dirname}/server/index.js'], 'env': {'SPB_PORT': '${user_config.port}'}}},
        'user_config': {'port': {'type': 'string', 'title': 'Shokker server port', 'description': 'Leave as is unless Shokker Paint Booth runs on another port.', 'required': False, 'default': '59876'}},
        'tools': [],          # filled from the server's real tools/list below
        'tools_generated': True, 'prompts_generated': True,
        'compatibility': {'platforms': ['win32', 'darwin'], 'runtimes': {'node': '>=16.0.0'}},
        'keywords': ['iracing', 'paint', 'livery', 'racing', 'design'], 'license': 'Proprietary',
    }
    # Requires adopted knowledge/setup modules and the complete prepared runtime tree.
    prepared = Path(os.environ.get('SPB_MCPB_PREPARED_SERVER', str(R / 'electron-app/server'))).resolve(strict=True)
    node = os.environ.get('SPB_NODE_BIN') or shutil.which('node')
    try:          # [S22 2026-10-13 beta Claude setup] the server's own VERSION constant should equal the manifest version (warn only)
        import re; m = re.search(r"const VERSION = '([^']+)'", (prepared / 'mcp/server/index.js').read_text(encoding='utf-8'))
        if m and m.group(1) != VERSION: print('WARNING: mcp/server/index.js VERSION %s != manifest version %s' % (m.group(1), VERSION))
    except Exception as e: print('version cross-check skipped:', e)
    if not node: raise RuntimeError('A verified build Node runtime is required')
    real = server_tools(prepared, node)          # [S22 2026-10-13 beta Claude setup]
    names = [t['name'] for t in real]
    manifest['tools'] = [{'name': t['name'], 'description': (t.get('description') or '').split('. ')[0][:160]} for t in real]
    print('manifest tools from the server\'s own tools/list:', len(names))
    subprocess.run([sys.executable, str(MCP / 'chatgpt/car-knowledge/build_knowledge.py'), '--check'], cwd=R, check=True)
    subprocess.run([node, str(R / 'scripts/runtime-knowledge-gate.cjs'), str(prepared)],
                   cwd=R, env={**os.environ, 'ELECTRON_RUN_AS_NODE': '1'}, check=True)
    manifest['server']['entry_point'] = 'mcp/server/index.js'
    manifest['server']['mcp_config']['args'] = ['${__dirname}/mcp/server/index.js']
    out = MCP / 'shokker-paint-booth.mcpb'
    tmp_out = MCP / 'shokker-paint-booth.mcpb.tmp'          # ONLINE-AI 2026-10-10: write beside + os.replace (a direct open(w) on the installed .mcpb failed with EINVAL while another app held it)
    with zipfile.ZipFile(tmp_out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(manifest, indent=2))
        add_runtime(z, prepared, R / 'scripts/runtime-knowledge-plan.json')
        ic = icon_bytes()
        if ic: z.writestr('icon.png', ic)
        z.write(MCP / 'README.md', 'README.md') if (MCP / 'README.md').exists() else None
    for _try in range(6):
        try:
            os.replace(tmp_out, out); break
        except OSError as e:
            if _try == 5: raise
            time.sleep(5)
    print('wrote', out, round(out.stat().st_size / 1024), 'KB;', len(names), 'tools')

if __name__ == '__main__':
    main()
