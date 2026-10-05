#!/usr/bin/env node
/* Minimal MCP test client: spawns mcp/server/index.js and runs a scripted conversation over stdio.
 * node mcp/test/client.js [scenario]   scenarios: smoke (writes + undo) | design | spec | list | read
 * Prints one line per call (tool, ok/error, short result, images) and saves returned images under mcp/test/out/. */
'use strict';
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const server = path.join(__dirname, '..', 'server', 'index.js');
const out = path.join(__dirname, 'out'); fs.mkdirSync(out, { recursive: true });
const scenario = process.argv[2] || 'smoke';
const child = spawn(process.execPath, [server], { stdio: ['pipe', 'pipe', 'inherit'], env: process.env });
let nextId = 1; const waiting = new Map(); let buf = '';
child.stdout.setEncoding('utf8');
child.stdout.on('data', (c) => { buf += c; let i; while ((i = buf.indexOf('\n')) >= 0) { const l = buf.slice(0, i); buf = buf.slice(i + 1); if (!l.trim()) continue; const m = JSON.parse(l); if (m.id != null && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); } } });
function rpc(method, params) { const id = nextId++; return new Promise((res) => { waiting.set(id, res); child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n'); }); }
function note(method, params) { child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method, params }) + '\n'); }
let imgN = 0;
async function call(name, args) {
  const t0 = Date.now(); const r = await rpc('tools/call', { name, arguments: args || {} });
  const res = r.result || {}; const parts = res.content || []; let text = '', imgs = 0;
  for (const p of parts) { if (p.type === 'text') text += p.text + '\n'; else if (p.type === 'image') { imgs++; const f = path.join(out, 'img_' + (++imgN) + '_' + name + '.' + (p.mimeType.split('/')[1] || 'png')); fs.writeFileSync(f, Buffer.from(p.data, 'base64')); } }
  console.log(('[' + name + ']').padEnd(22), res.isError ? 'ERROR' : 'ok   ', ((Date.now() - t0) / 1000).toFixed(1) + 's', 'images=' + imgs, '|', text.replace(/\s+/g, ' ').slice(0, 330));
  if (res.isError) throw new Error(name + ': ' + text.slice(0, 300));
  return { res, text };
}
(async () => {
  const init = await rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'spb-test-client', version: '0' } });
  console.log('initialize ->', init.result.serverInfo.name, init.result.protocolVersion, 'instructions chars', (init.result.instructions || '').length);
  note('notifications/initialized', {});
  const tl = await rpc('tools/list', {}); console.log('tools:', tl.result.tools.length, tl.result.tools.map((t) => t.name).join(', '));
  const pl = await rpc('prompts/list', {}); console.log('prompts:', pl.result.prompts.map((p) => p.name).join(', '));
  if (scenario === 'list') { fs.writeFileSync(path.join(out, 'tools_list.json'), JSON.stringify(tl.result.tools, null, 1)); }
  else {
    await call('spb_status');
    await call('spb_get_car_map');
    if (scenario === 'read') await call('spb_preview', { spec: true, parts: false });
    if (scenario === 'smoke' || scenario === 'design') {
      await call('spb_design_recipes', { query: 'Gulf style' });
      await call('spb_apply_scheme', { preset: 'classic_stripes', palette_id: 'gulf-style', paint_finish: 'base::gloss' });
      await call('spb_preview', { parts: false });
      await call('spb_get_zones');
      await call('spb_undo', { steps: 1 });
    }
    if (scenario === 'spec') {
      await call('spb_add_zone', { name: 'Hood chrome (spec only)', finish: 'base::f_chrome', color: 'source', region: { part: 'hood' } });
      await call('spb_preview', { spec: true });
    }
  }
  child.stdin.end(); setTimeout(() => process.exit(0), 300);
})().catch((e) => { console.error('client error', e); process.exit(1); });
