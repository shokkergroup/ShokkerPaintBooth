'use strict';
// [S22 2026-10-13 beta Claude setup] regression test for AUTOLAUNCH in mcp/server/index.js ("Claude can open SPB").
//   node mcp/test/autolaunch.test.cjs
// Runs the real MCP server over stdio with the app NOT running and SPB_AUTOLAUNCH_EXE pointed at a dummy script (a fake "installed app"
// that, after a short delay, serves /api/health, /api/mcp/status and /api/mcp/call on a spare port). Proves:
//   1. two parallel tool calls with the app down start the app ONCE, wait for health + the page, retry, and both succeed
//   2. a later call (app up) starts nothing
//   3. a DEV run (no installed exe, port != 59876) is unchanged: same "Could not reach ... Is the app running?" text, nothing started
//   4. an app that never comes up gives a plain-English note (and the cooldown stops a second start)
//   5. SPB_AUTOLAUNCH_OFF=1 is a kill switch
// Never touches port 59876.
const { spawn } = require('child_process');
const fs = require('fs'), os = require('os'), path = require('path'), assert = require('assert');
const SERVER = path.join(__dirname, '..', 'server', 'index.js');
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'spb-autolaunch-'));
const LOG = path.join(TMP, 'launches.log');
const FAKE = path.join(TMP, 'fake-spb.cjs');
fs.writeFileSync(path.join(TMP, 'token.txt'), 'test-token');
fs.writeFileSync(FAKE, `
const http = require('http'), fs = require('fs');
fs.appendFileSync(${JSON.stringify(LOG)}, 'launch ' + process.pid + '\\n');
if (process.env.FAKE_NEVER_UP) { setTimeout(() => process.exit(0), 300); return; }
const t0 = Date.now() + 2500;          // health comes up after 2.5 s
const page0 = Date.now() + 5000;       // the app page connects to the bridge after 5 s
http.createServer((req, res) => {
  if (Date.now() < t0) { req.destroy(); return; }
  const send = (o, c) => { res.writeHead(c || 200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(o)); };
  if (req.url === '/api/health') return send({ status: 'ok' });
  if (req.url === '/api/mcp/status') return send({ ok: true, enabled: true, connected: Date.now() > page0 });
  if (req.url === '/api/mcp/call') { let b = ''; req.on('data', (c) => b += c); req.on('end', () => { if (Date.now() < page0) return send({ ok: false, error: 'app_not_ready', message: 'not ready' }, 503); const j = JSON.parse(b || '{}'); send({ ok: true, result: { fake: true, tool: j.tool } }); }); return; }
  send({ ok: false, error: 'nope' }, 404);
}).listen(Number(process.env.SPB_PORT), '127.0.0.1');
`);

function launches() { try { return fs.readFileSync(LOG, 'utf8').split('\n').filter(Boolean).length; } catch (e) { return 0; } }
function startServer(env) {
  const child = spawn(process.execPath, [SERVER], { env: Object.assign({}, process.env, { SPB_MCP_TOKEN_FILE: path.join(TMP, 'token.txt') }, env), stdio: ['pipe', 'pipe', 'pipe'] });
  const pending = new Map(); let buf = '', id = 0, errTxt = '';
  child.stdout.on('data', (d) => { buf += d; let i; while ((i = buf.indexOf('\n')) >= 0) { const line = buf.slice(0, i); buf = buf.slice(i + 1); if (!line.trim()) continue; try { const m = JSON.parse(line); if (m.id != null && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } } catch (e) { /* ignore */ } } });
  child.stderr.on('data', (d) => { errTxt += d; });
  const rpc = (method, params) => new Promise((resolve, reject) => { const i = ++id; const t = setTimeout(() => reject(new Error('rpc timeout ' + method)), 90000); pending.set(i, (m) => { clearTimeout(t); resolve(m); }); child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: i, method, params }) + '\n'); });
  return { child, rpc, err: () => errTxt, async init() { await rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'claude-ai', version: '1' } }); child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }) + '\n'); } };
}
const text = (m) => ((m.result && m.result.content) || []).map((c) => c.text).join('\n');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const port = (n) => String(59950 + n);

(async () => {
  // 1 + 2: app down -> one launch, wait, retry
  let s = startServer({ SPB_PORT: port(1), SPB_AUTOLAUNCH_EXE: FAKE, SPB_AUTOLAUNCH_WAIT_S: '40', SPB_AUTOLAUNCH_COOLDOWN_S: '300' });
  await s.init();
  const t0 = Date.now();
  const [a, b] = await Promise.all([s.rpc('tools/call', { name: 'spb_status', arguments: {} }), s.rpc('tools/call', { name: 'spb_get_zones', arguments: {} })]);
  const took = Math.round((Date.now() - t0) / 1000);
  assert(!(a.result && a.result.isError), 'call 1 should succeed after the launch: ' + text(a).slice(0, 300));
  assert(!(b.result && b.result.isError), 'call 2 should succeed after the launch: ' + text(b).slice(0, 300));
  assert(/fake/.test(text(a)) && /fake/.test(text(b)), 'both calls must reach the fake app');
  assert.strictEqual(launches(), 1, 'two parallel calls must start the app exactly once (got ' + launches() + ')');
  assert(took >= 4, 'must have waited for the page to connect (took ' + took + ' s)');
  console.log('1 launched once, waited ' + took + ' s (health 2.5 s, page 5 s), both parallel calls succeeded');
  const c = await s.rpc('tools/call', { name: 'spb_status', arguments: {} });
  assert(!(c.result && c.result.isError), 'call 3 should succeed');
  assert.strictEqual(launches(), 1, 'a call with the app up must start nothing');
  console.log('2 later call with the app up: no second launch');
  s.child.kill();

  // 3: dev run (no installed exe, non-production port): exactly the old behaviour
  const before = launches();
  s = startServer({ SPB_PORT: port(2), SPB_AUTOLAUNCH_EXE: '' });
  await s.init();
  const d = await s.rpc('tools/call', { name: 'spb_status', arguments: {} });
  assert(d.result && d.result.isError, 'dev run must still return an error');
  assert(new RegExp('^Could not reach Shokker Paint Booth on 127\\.0\\.0\\.1:' + port(2) + ' \\(connect ECONNREFUSED 127\\.0\\.0\\.1:' + port(2) + '\\)\\. Is the app running\\?$').test(text(d)), 'dev run text changed: ' + text(d));
  assert.strictEqual(launches(), before, 'dev run must start nothing');
  console.log('3 dev run unchanged: ' + text(d));
  s.child.kill();

  // 4: the app never comes up -> plain note, one start only (cooldown)
  s = startServer({ SPB_PORT: port(3), SPB_AUTOLAUNCH_EXE: FAKE, SPB_AUTOLAUNCH_WAIT_S: '4', SPB_AUTOLAUNCH_COOLDOWN_S: '300', FAKE_NEVER_UP: '1' });
  await s.init();
  const e1 = await s.rpc('tools/call', { name: 'spb_status', arguments: {} });
  assert(e1.result && e1.result.isError && /still opening|could not be started/.test(text(e1)), 'needs a plain-English note: ' + text(e1));
  const n1 = launches();
  const e2 = await s.rpc('tools/call', { name: 'spb_status', arguments: {} });
  assert(e2.result && e2.result.isError, 'second call must also fail cleanly');
  assert.strictEqual(launches(), n1, 'the cooldown must stop a second start');
  console.log('4 never-up app: "' + text(e1).slice(0, 150) + '" ; no second start inside the cooldown');
  s.child.kill();

  // 5: kill switch
  const n5 = launches();
  s = startServer({ SPB_PORT: port(4), SPB_AUTOLAUNCH_EXE: FAKE, SPB_AUTOLAUNCH_OFF: '1' });
  await s.init();
  const k = await s.rpc('tools/call', { name: 'spb_status', arguments: {} });
  assert(k.result && k.result.isError && /Is the app running\?/.test(text(k)), 'kill switch: old error');
  assert.strictEqual(launches(), n5, 'kill switch: nothing started');
  console.log('5 SPB_AUTOLAUNCH_OFF=1: nothing started');
  s.child.kill();
  await sleep(300);
  try { fs.readFileSync(LOG, 'utf8').split(String.fromCharCode(10)).filter(Boolean).forEach((l) => { try { process.kill(Number(l.split(' ')[1])); } catch (e) { /* gone */ } }); } catch (e) { /* none */ }          // stop the fake apps
  console.log('autolaunch OK');
  process.exit(0);
})().catch((e) => { console.error('FAIL', e && e.stack || e); process.exit(1); });
