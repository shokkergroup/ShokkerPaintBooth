#!/usr/bin/env node
/**
 * spb_shot.js - screenshot the live Shokker Paint Booth UI with headless Chrome.
 *
 * Why this exists: the in-harness Browser pane does not composite frames when the
 * pane is not displayed, so screenshots time out and rAF never fires. This drives
 * a real Chrome over CDP instead - no npm install, Node 22's global fetch and
 * WebSocket are enough.
 *
 * Usage:
 *   node spb_shot.js --out DIR [--url URL] [--shot name:WxH:ls_json:js] ...
 *
 * Each --shot is  name:WIDTHxHEIGHT  plus optional pre-navigation localStorage
 * (JSON) and an optional post-load JS snippet to drive the UI before capturing.
 */
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME = process.env.SPB_CHROME ||
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe';
const PORT = Number(process.env.SPB_CDP_PORT || 9333);

function arg(name, dflt) {
  const i = process.argv.indexOf('--' + name);
  return i > -1 ? process.argv[i + 1] : dflt;
}
const URL_ = arg('url', 'http://localhost:59876/paint-booth-v2.html');
const OUT = arg('out', '.');
const BOOT_MS = Number(arg('boot', 14000));

// shots come from a JSON file so we never fight shell quoting
const PLAN = JSON.parse(fs.readFileSync(arg('plan'), 'utf8'));

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitForCdp(port, tries = 60) {
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (r.ok) return await r.json();
    } catch (e) { /* not up yet */ }
    await sleep(500);
  }
  throw new Error('Chrome CDP never came up on port ' + port);
}

/** Minimal CDP session over one websocket. */
class Session {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.events = []; this.dialogs = []; }
  static async open(wsUrl) {
    const ws = new WebSocket(wsUrl);
    const s = new Session(ws);
    ws.addEventListener('message', (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && s.pending.has(msg.id)) {
        const { resolve, reject, timer } = s.pending.get(msg.id);
        s.pending.delete(msg.id);
        clearTimeout(timer);
        msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
      } else if (msg.method) {
        s.events.push(msg.method);
        // A native window.confirm/alert blocks the page AND the CDP evaluate
        // that triggered it, so one un-handled dialog hangs the whole run until
        // the outer timeout. Auto-accept so automation can drive flows that use
        // them; `s.dialogs` records that it happened so a probe can assert on it.
        if (msg.method === 'Page.javascriptDialogOpening') {
          s.dialogs.push((msg.params && msg.params.message) || '');
          s.send('Page.handleJavaScriptDialog', { accept: true }).catch(function () {});
        }
      }
    });
    await new Promise((res, rej) => {
      ws.addEventListener('open', res, { once: true });
      ws.addEventListener('error', rej, { once: true });
    });
    return s;
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      // [SPB-VERIFY-LATENCY 2026-08-23] Resolved CDP calls used to leave their
      // 120 s watchdog timers referenced. A completed 19-shot Easy sweep then
      // sat idle for two extra minutes before Node could exit. Clear successful
      // watchdogs and unref the live one; timeout behavior stays fail-closed.
      const timer = setTimeout(() => {
        if (this.pending.has(id)) { this.pending.delete(id); reject(new Error('CDP timeout: ' + method)); }
      }, 120000);
      if (timer.unref) timer.unref();
      this.pending.set(id, { resolve, reject, timer });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() { try { this.ws.close(); } catch (e) {} }
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  try {
    await fetch(`http://127.0.0.1:${PORT}/json/version`);
    throw new Error('refusing occupied Chrome CDP port ' + PORT);
  } catch (e) {
    if (String(e && e.message || e).includes('refusing occupied')) throw e;
  }
  // Every invocation gets a genuinely fresh origin-storage/profile state. A
  // fixed profile previously let old localStorage and cached scripts turn a
  // candidate run into evidence from some earlier tree.
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'spb-shot-profile-'));

  const chrome = spawn(CHROME, [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-extensions',
    '--force-device-scale-factor=1',
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`,
    'about:blank',
  ], { stdio: 'ignore', detached: false });

  const results = [];
  try {
    await waitForCdp(PORT);
    const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
    const page = targets.find((t) => t.type === 'page');
    if (!page) throw new Error('no page target');

    const s = await Session.open(page.webSocketDebuggerUrl);
    await s.send('Page.enable');
    await s.send('Runtime.enable');

    for (const shot of PLAN) {
      // [GAUNTLET 2026-08-20] One shot must never destroy the whole run. A CDP
      // timeout in R13 aborted an 11-minute sweep and lost EVERY result,
      // including the 12 shots that had already passed. Each shot is now
      // isolated: it fails on its own line and the sweep carries on.
      try {
      const [w, h] = shot.size.split('x').map(Number);
      await s.send('Emulation.setDeviceMetricsOverride',
        { width: w, height: h, deviceScaleFactor: 1, mobile: false });

      // Seed localStorage BEFORE the app's scripts run.
      const seed = shot.ls ? JSON.stringify(shot.ls) : null;
      if (seed) {
        await s.send('Page.addScriptToEvaluateOnNewDocument', {
          source: `try{localStorage.clear();var d=${seed};for(var k in d)localStorage.setItem(k,d[k]);}catch(e){}`,
        });
      }

      // [GAUNTLET 2026-08-20] per-shot url so a plan can drive deep links
      // (e.g. ?easy=spec-sculpt) without a second harness invocation.
      await s.send('Page.navigate', { url: shot.url || URL_ });
      await sleep(shot.boot || BOOT_MS);

      if (shot.js) {
        try {
          const r = await s.send('Runtime.evaluate', {
            expression: shot.js, awaitPromise: true, returnByValue: true,
          });
          // A page-side throw comes back as a NORMAL result with
          // exceptionDetails set - not as a rejected CDP call. Ignoring it made
          // a broken step look like a step that simply returned nothing, which
          // cost a full screenshot cycle to notice.
          if (r.exceptionDetails) {
            const ex = r.exceptionDetails;
            const msg = (ex.exception && (ex.exception.description || ex.exception.value)) || ex.text || 'page threw';
            results.push({ name: shot.name, jsThrew: String(msg).split(String.fromCharCode(10))[0].slice(0, 240) });
          } else {
            const v = r.result ? r.result.value : undefined;
            results.push({ name: shot.name, js: v === undefined ? '(undefined)' : v });
          }
        } catch (e) {
          results.push({ name: shot.name, jsError: String(e.message).slice(0, 240) });
        }
        await sleep(shot.after || 2500);
      }

      if (s.dialogs.length) results.push({ name: shot.name, nativeDialogs: s.dialogs.splice(0) });
      const cap = await s.send('Page.captureScreenshot', { format: 'png' });
      const file = path.join(OUT, `${shot.name}.png`);
      fs.writeFileSync(file, Buffer.from(cap.data, 'base64'));
      const kb = Math.round(fs.statSync(file).size / 1024);
      console.log(`SHOT ${shot.name} ${w}x${h} -> ${file} (${kb} KB)`);
      } catch (shotErr) {
        console.log(`SHOT ${shot.name} FAILED: ${shotErr.message}`);
        results.push({ name: shot.name, shotError: String(shotErr.message).slice(0, 200) });
      }
    }
    s.close();
  } finally {
    try { chrome.kill(); } catch (e) {}
    await Promise.race([
      new Promise((resolve) => chrome.once('exit', resolve)),
      sleep(3000),
    ]);
    try {
      fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
    } catch (e) {
      console.warn('WARN could not remove temporary Chrome profile: ' + e.message);
    }
  }
  if (results.length) console.log('JS ' + JSON.stringify(results));
  console.log('DONE');
})().catch((e) => { console.error('FAIL ' + e.message); process.exit(1); });
