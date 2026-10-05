#!/usr/bin/env python
"""Build mcp/shokker-paint-booth.mcpb (Claude Desktop one-click extension) from mcp/server/*.  SPB-AI 2026-09-30.

  python scripts/build_mcpb.py             pack with the tools.json already in mcp/server
  python scripts/build_mcpb.py --tools     first refresh tools.json from the LIVE app through the bridge (app open in Pro mode, bridge switched on), then pack

An .mcpb is a zip with manifest.json at the root (manifest_version 0.3, server.type node: Claude Desktop runs it with its own bundled Node, nothing for the buyer to install).
"""
import json, os, sys, zipfile, io, urllib.request
from pathlib import Path
R = Path(__file__).resolve().parents[1]
MCP = R / 'mcp'
VERSION = '1.1.0'          # 2026-10-05: MCPSCEN overnight fixes + tool text synced with the app

def refresh_tools():
    tok = (Path(os.environ.get('APPDATA', str(Path.home()))) / 'ShokkerPaintBooth' / 'mcp' / 'token.txt').read_text(encoding='utf-8').strip()
    rq = urllib.request.Request('http://127.0.0.1:59876/api/mcp/call', data=json.dumps({'tool': 'list_tools', 'args': {}}).encode(), headers={'Content-Type': 'application/json', 'X-SPB-MCP-Token': tok})
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

def main():
    if '--tools' in sys.argv: refresh_tools()
    tools = json.loads((MCP / 'server' / 'tools.json').read_text(encoding='utf-8')) if (MCP / 'server' / 'tools.json').exists() else []
    static = ['spb_status', 'spb_get_zones', 'spb_preview', 'spb_request_parts', 'spb_undo', 'spb_encyclopedia']
    names = static + [t['name'] for t in tools if t['name'] not in static]
    desc = {t['name']: (t.get('description') or '').split('. ')[0][:160] for t in tools}
    manifest = {
        'manifest_version': '0.3', 'name': 'shokker-paint-booth', 'display_name': 'Shokker Paint Booth', 'version': VERSION,
        'description': 'Design iRacing paints by talking to Claude: Claude drives Shokker Paint Booth (zones, finishes, spec maps, car parts, live preview) using your own Claude plan.',
        'long_description': 'Shokker Paint Booth must be open in Pro mode with "Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth" switched on (AI panel -> settings). Claude then lays out liveries on the named parts of your car, changes only the spec (shine / metal) when asked, searches the 4,800-finish catalogue and looks at the live preview to check its work. Every change appears in the Shokker AI panel with an Undo button. Uses your Claude subscription: no API key and no extra cost.',
        'author': {'name': 'Shokker Group'},
        'icon': 'icon.png',
        'server': {'type': 'node', 'entry_point': 'server/index.js', 'mcp_config': {'command': 'node', 'args': ['${__dirname}/server/index.js'], 'env': {'SPB_PORT': '${user_config.port}'}}},
        'user_config': {'port': {'type': 'string', 'title': 'Shokker server port', 'description': 'Leave as is unless Shokker Paint Booth runs on another port.', 'required': False, 'default': '59876'}},
        'tools': [{'name': n, 'description': desc.get(n, '')} for n in names],
        'tools_generated': True, 'prompts_generated': True,
        'compatibility': {'platforms': ['win32', 'darwin'], 'runtimes': {'node': '>=16.0.0'}},
        'keywords': ['iracing', 'paint', 'livery', 'racing', 'design'], 'license': 'Proprietary',
    }
    out = MCP / 'shokker-paint-booth.mcpb'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(manifest, indent=2))
        z.write(MCP / 'server' / 'index.js', 'server/index.js')
        if (MCP / 'server' / 'tools.json').exists(): z.write(MCP / 'server' / 'tools.json', 'server/tools.json')
        ic = icon_bytes()
        if ic: z.writestr('icon.png', ic)
        z.write(MCP / 'README.md', 'README.md') if (MCP / 'README.md').exists() else None
    print('wrote', out, round(out.stat().st_size / 1024), 'KB;', len(names), 'tools')

if __name__ == '__main__':
    main()
