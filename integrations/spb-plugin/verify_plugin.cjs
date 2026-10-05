/* Verify the private pilot over actual stdio; live mode calls ONLY spb_status. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');
const lane = __dirname;
const root = path.resolve(lane, '../..');
const pkg = path.join(lane, 'shokker-paint-booth-local');
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const live = process.argv.includes('--live-status');
const child = spawn(process.execPath, [path.join(pkg, 'server/index.js')], {
  cwd: pkg, stdio: ['pipe', 'pipe', 'pipe'], env: process.env,
});
const pending = new Map();
let next = 1, buffer = '';
child.stdout.setEncoding('utf8');
child.stdout.on('data', chunk => {
  buffer += chunk;
  let position;
  while ((position = buffer.indexOf('\n')) >= 0) {
    const line = buffer.slice(0, position); buffer = buffer.slice(position + 1);
    if (!line.trim()) continue;
    const message = JSON.parse(line);
    const waiter = pending.get(message.id);
    if (waiter) { clearTimeout(waiter.timer); pending.delete(message.id); waiter.resolve(message); }
  }
});
child.stderr.on('data', () => {}); // Do not copy client/runtime diagnostics into buyer evidence.
child.on('error', error => {
  for (const waiter of pending.values()) { clearTimeout(waiter.timer); waiter.reject(error); }
  pending.clear();
});
function rpc(method, params = {}, timeout = 10000) {
  const id = next++;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(method + ' timed out')); }, timeout);
    pending.set(id, { resolve, reject, timer });
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
  });
}
const report = { date: '2026-10-04', scope: 'Private local pilot; protocol and optional read-only status',
  checks: {}, native_host_installation: 'unverified', painting_acceptance: 'not run' };
(async () => {
  try {
    const provenance = JSON.parse(fs.readFileSync(path.join(pkg, 'BUILD_PROVENANCE.json'), 'utf8'));
    for (const [source, details] of Object.entries(provenance.sources)) {
      assert.equal(hash(path.join(root, source)), details.sha256, 'Production source changed: rebuild ' + source);
      assert.equal(hash(path.join(pkg, 'server', path.basename(source))), details.sha256);
    }
    report.checks.exact_source_snapshots = 'pass';
    assert.equal(provenance.official_schema_validation.length, 2);
    assert(provenance.official_schema_validation.every(item => item.result === 'pass'));
    report.checks.official_schemas = '2 pass at build time';
    const init = await rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {},
      clientInfo: { name: 'spb-plugin-pilot-audit', version: '0.1.0' } });
    assert.equal(init.result.serverInfo.name, 'shokker-paint-booth');
    assert.equal(init.result.protocolVersion, '2025-06-18');
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n');
    report.checks.initialize = 'pass';
    const tools = (await rpc('tools/list')).result.tools;
    const names = tools.map(tool => tool.name);
    assert.equal(new Set(names).size, names.length);
    for (const required of ['spb_status', 'spb_get_state', 'spb_get_car_map', 'spb_preview',
      'spb_find_finishes', 'spb_apply_scheme', 'spb_edit_zone', 'spb_undo']) assert(names.includes(required));
    const generated = JSON.parse(fs.readFileSync(path.join(root, 'mcp/server/tools.json'), 'utf8'));
    for (const tool of generated) assert(names.includes(tool.name), 'Missing production tool: ' + tool.name);
    assert(tools.every(tool => tool.inputSchema && tool.inputSchema.type === 'object'));
    report.checks.tool_discovery = { result: 'pass', count: tools.length, names };
    const prompts = (await rpc('prompts/list')).result.prompts;
    assert(prompts.length > 0);
    report.checks.prompt_discovery = { result: 'pass', count: prompts.length };
    assert.deepEqual((await rpc('ping')).result, {});
    report.checks.ping = 'pass';
    const resourceResult = await rpc('resources/list');
    assert.deepEqual(resourceResult.result.resources, []);
    report.checks.ui_resources = 'None; embedded UI is not implemented';
    if (live) {
      try {
        const response = await rpc('tools/call', { name: 'spb_status', arguments: {} }, 20000);
        assert(response.result && Array.isArray(response.result.content));
        report.live_status = { result: response.result.isError ? 'app reports unavailable/error' : 'pass',
          response_received: true, paint_mutation: false };
      } catch (error) { report.live_status = { result: 'unverified', reason: error.message, paint_mutation: false }; }
    } else report.live_status = { result: 'not requested' };
    for (const [source, details] of Object.entries(provenance.sources))
      assert.equal(hash(path.join(root, source)), details.sha256, 'Production source changed during audit');
    report.result = 'package protocol pass';
    fs.writeFileSync(path.join(lane, 'verification.json'), JSON.stringify(report, null, 2) + '\n');
    console.log(JSON.stringify({ result: report.result, tools: tools.length, prompts: prompts.length,
      live_status: report.live_status, native_host_installation: report.native_host_installation }));
  } finally {
    child.stdin.end(); child.kill();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; child.kill(); });
