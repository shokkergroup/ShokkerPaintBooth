#!/usr/bin/env node
/* Shokker Paint Booth — app-chat wake-up for Claude Code  (APPCHAT 2026-10-09)
 *
 * Claude Code runs this as a BACKGROUND command. It waits (costing nothing) until the buyer types in the Shokker app's own chat box,
 * prints the message(s) and EXITS. Claude Code wakes the session the moment a background command exits, so the assistant answers at once:
 * a push, not a poll. The assistant then acts, answers with spb_reply, and starts this script again.
 *
 *   node "<SPB>/mcp/server/wait-inbox.js"            (waits up to 6 hours; the server holds each request ~9 minutes and this re-asks)
 *   env SPB_PORT (default 59876), SPB_MCP_TOKEN_FILE, SPB_WAIT_HOURS (default 6)
 *
 * Output (stdout, one JSON line): {"messages":[{"seq":12,"text":"..."}]}  or  {"stopped":"<why>"}
 */
'use strict';
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');

const PORT = Number(process.env.SPB_PORT) || 59876;
const DEADLINE = Date.now() + (Number(process.env.SPB_WAIT_HOURS) || 6) * 3600 * 1000;
function tokenFile() { return process.env.SPB_MCP_TOKEN_FILE || path.join(process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming'), 'ShokkerPaintBooth', 'mcp', 'token.txt'); }
function readToken() { try { return fs.readFileSync(tokenFile(), 'utf8').trim(); } catch (e) { return ''; } }
function done(obj) { process.stdout.write(JSON.stringify(obj) + '\n'); process.exit(0); }

function once(secs) {
  return new Promise((resolve) => {
    const req = http.request({ host: '127.0.0.1', port: PORT, path: '/api/mcp/inbox/wait?timeout=' + secs, method: 'GET', headers: { 'X-SPB-MCP-Token': readToken(), 'X-SPB-MCP-Client': 'claude-code-watcher' } }, (res) => {
      const chunks = []; res.on('data', (c) => chunks.push(c));
      res.on('end', () => { let j = null; try { j = JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch (e) { /* not json */ } resolve({ status: res.statusCode, json: j }); });
    });
    req.on('error', (e) => resolve({ status: 0, error: String(e && e.message || e) }));
    req.setTimeout((secs + 30) * 1000, () => req.destroy(new Error('timeout')));
    req.end();
  });
}

(async function main() {
  let fails = 0;
  while (Date.now() < DEADLINE) {
    const r = await once(540);
    if (r.json && r.json.messages && r.json.messages.length) return done({ messages: r.json.messages });
    if (r.json && r.json.ok && r.json.enabled === false) return done({ stopped: 'the buyer switched the AI connection off in Shokker' });
    if (r.status === 401) return done({ stopped: 'pairing token rejected: switch the AI connection on in the Shokker AI panel' });
    if (r.status === 404) return done({ stopped: 'this Shokker version has no app chat (update Shokker Paint Booth)' });
    if (r.status === 0 || r.status >= 500) { fails++; if (fails > 40) return done({ stopped: 'Shokker is not reachable on 127.0.0.1:' + PORT }); await new Promise((ok) => setTimeout(ok, 15000)); }
    else fails = 0;
  }
  done({ stopped: 'waited the full time with no message' });
})();
