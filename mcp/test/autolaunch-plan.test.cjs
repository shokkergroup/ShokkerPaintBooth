'use strict';
// [S22 2026-10-13 beta Claude setup] pins the SPAWN OPTIONS of the AUTOLAUNCH in mcp/server/index.js (the started SPB must outlive the Claude extension process).
//   node mcp/test/autolaunch-plan.test.cjs
// Runs the real MCP server over stdio with the app down and SPB_AUTOLAUNCH_DRYRUN=<file>, which appends each planned spawn there instead of starting anything. Proves:
//   1. Windows, real exe: FIRST a breakaway start through explorer.exe (absolute path, args [exe], detached, stdio ignore, NO windowsHide), THEN (nothing showed up) a direct start:
//      detached, stdio ignore, cwd = the exe folder, ELECTRON_RUN_AS_NODE and NODE_OPTIONS stripped, NO windowsHide (SW_HIDE would hide the app's own window)
//   2. a .js stand-in (used by autolaunch.test.cjs): one direct start with this node, detached, stdio ignore, windowsHide ON (console child)
//   3. the source still unref()s the child
// Never touches port 59876; starts nothing.
const { spawn } = require('child_process');
const fs = require('fs'), os = require('os'), path = require('path'), assert = require('assert');
const SERVER = path.join(__dirname, '..', 'server', 'index.js');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'spb-alplan-'));
fs.writeFileSync(path.join(TMP, 'token.txt'), 'test-token');

function run(env) {
  const child = spawn(process.execPath, [SERVER], { env: Object.assign({}, process.env, { SPB_MCP_TOKEN_FILE: path.join(TMP, 'token.txt') }, env), stdio: ['pipe', 'pipe', 'pipe'] });
  const pending = new Map(); let buf = '', id = 0;
  child.stdout.on('data', (d) => { buf += d; let i; while ((i = buf.indexOf('\n')) >= 0) { const line = buf.slice(0, i); buf = buf.slice(i + 1); if (!line.trim()) continue; try { const m = JSON.parse(line); if (m.id != null && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } } catch (e) { /* ignore */ } } });
  const rpc = (method, params) => new Promise((resolve, reject) => { const i = ++id; const t = setTimeout(() => reject(new Error('rpc timeout ' + method)), 60000); pending.set(i, (m) => { clearTimeout(t); resolve(m); }); child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: i, method, params }) + '\n'); });
  return { child, rpc, async init() { await rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'claude-ai', version: '1' } }); child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n'); } };
}
const planned = (f) => { try { return fs.readFileSync(f, 'utf8').split(String.fromCharCode(10)).filter(Boolean).map((l) => JSON.parse(l)); } catch (e) { return []; } };

(async () => {
  // source guard (3)
  const src = fs.readFileSync(SERVER, 'utf8');
  const al = src.slice(src.indexOf('function alSpawn('), src.indexOf('async function alRun('));
  assert(/child\.unref\(\)/.test(al), 'alSpawn must unref the child');
  console.log('3 alSpawn unref()s the child');

  // 2: .js stand-in
  const stand = path.join(TMP, 'stand-in.cjs'); fs.writeFileSync(stand, '// not run: dry run');
  const f2 = path.join(TMP, 'plan-js.log');
  let s = run({ SPB_PORT: '59955', SPB_AUTOLAUNCH_EXE: stand, SPB_AUTOLAUNCH_DRYRUN: f2, SPB_AUTOLAUNCH_WAIT_S: '3', SPB_AUTOLAUNCH_COOLDOWN_S: '300' });
  await s.init(); await s.rpc('tools/call', { name: 'spb_status', arguments: {} }); s.child.kill();
  const p2 = planned(f2);
  assert.strictEqual(p2.length, 1, 'js stand-in: exactly one planned start (got ' + p2.length + ')');
  assert.strictEqual(p2[0].kind, 'direct'); assert.strictEqual(p2[0].command, process.execPath); assert.deepStrictEqual(p2[0].args, [stand]);
  assert.strictEqual(p2[0].options.detached, true); assert.strictEqual(p2[0].options.stdio, 'ignore'); assert.strictEqual(p2[0].options.windowsHide, true);
  console.log('2 .js stand-in: one direct start, detached + stdio ignore + windowsHide on');

  // 1: the real exe name (Windows only: the breakaway start is Windows-specific)
  if (process.platform !== 'win32') { console.log('1 skipped (not Windows)'); console.log('autolaunch-plan OK'); process.exit(0); }
  const dir = path.join(TMP, 'Shokker Test Dir'); fs.mkdirSync(dir); const exe = path.join(dir, 'Shokker Paint Booth V11.exe'); fs.writeFileSync(exe, '');
  const f1 = path.join(TMP, 'plan-exe.log');
  s = run({ SPB_PORT: '59956', SPB_AUTOLAUNCH_EXE: exe, SPB_AUTOLAUNCH_DRYRUN: f1, SPB_AUTOLAUNCH_VERIFY_S: '2', SPB_AUTOLAUNCH_WAIT_S: '3', SPB_AUTOLAUNCH_COOLDOWN_S: '300', ELECTRON_RUN_AS_NODE: '1', NODE_OPTIONS: '--max-old-space-size=256' });
  await s.init(); await s.rpc('tools/call', { name: 'spb_status', arguments: {} }); s.child.kill();
  const p1 = planned(f1);
  assert.strictEqual(p1.length, 2, 'real exe on Windows: breakaway start then the direct fallback (got ' + p1.length + ')');
  const [b, d] = p1;
  assert.strictEqual(b.kind, 'breakaway');
  assert.strictEqual(b.command.toLowerCase(), path.join(process.env.SystemRoot || process.env.windir, 'explorer.exe').toLowerCase(), 'explorer by absolute path');
  assert.deepStrictEqual(b.args, [exe]);
  assert.strictEqual(b.options.detached, true); assert.strictEqual(b.options.stdio, 'ignore'); assert.strictEqual(b.options.windowsHide, false, 'windowsHide would hide the app window');
  assert.strictEqual(b.options.env.ELECTRON_RUN_AS_NODE, null); assert.strictEqual(b.options.env.NODE_OPTIONS, null);
  assert.strictEqual(d.kind, 'direct'); assert.strictEqual(d.command, exe); assert.deepStrictEqual(d.args, []);
  assert.strictEqual(d.options.detached, true); assert.strictEqual(d.options.stdio, 'ignore'); assert.strictEqual(d.options.windowsHide, false);
  assert.strictEqual(d.options.cwd, dir, 'cwd = the exe folder');
  assert.strictEqual(d.options.env.ELECTRON_RUN_AS_NODE, null, 'ELECTRON_RUN_AS_NODE must not leak into SPB'); assert.strictEqual(d.options.env.NODE_OPTIONS, null);
  console.log('1 real exe (Windows): explorer breakaway first, direct fallback second; detached, stdio ignore, no windowsHide, env stripped, cwd = exe folder');
  console.log('autolaunch-plan OK');
  process.exit(0);
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
