'use strict';

// Exercise the real MCP handlers and completion path. The render observer
// records the busy state a buyer's composer would see after the call settles.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../js/spb-pro-ai.js'), 'utf8');

function harness() {
  const observed = [], lease = { allowed: true, ends: 0 };
  const sandbox = {
    console, Promise, Date, setTimeout() {}, setInterval() {}, zones: [], selectedZoneIndex: 0,
    document: { readyState: 'loading', addEventListener() {}, getElementById() { return null; } },
    window: {
      SpbTellNLU: { buildIndex() { return {}; } }, SpbAI: { cached() { return {}; } },
      SpbMcpBridge: { stats() { return { enabled: true }; } },
      // Completion tests use a stable empty document, as the real canvas API
      // publishes at startup. Source-switch behavior has its own route tests.
      SPBSourceLoadTransaction: {
        getGeneration() { return 0; },
        getCommittedPath() { return null; },
        getCommittedFingerprint() { return null; }
      },
      SpbProZone: { SCHEMA: {}, zonesForModel() { return []; }, previewImage() { return null; }, whenSettled() { return Promise.resolve(); } },
      SpbAiLease: { begin() { return lease.allowed; }, end() { lease.ends++; } },
      __observeBusy(value) { observed.push(value); }
    }
  };
  vm.createContext(sandbox);
  const marker = '    window.spbProAI =';
  assert.equal(source.split(marker).length, 2, 'one production API export');
  vm.runInContext(source.replace(marker,
    '    render = function () { window.__observeBusy(_busy); };\n' + marker), sandbox);
  return { api: sandbox.window.spbProAI, window: sandbox.window, observed, lease };
}

(async () => {
  const h = harness();
  const success = await h.api.mcpCall('zones');
  assert.equal(success.ok, true);
  assert.equal(h.api.busy(), false);
  assert.equal(h.lease.ends, 1);
  assert.equal(h.observed.at(-1), false, 'success publishes idle to the composer');

  h.observed.length = 0;
  h.window.SpbProZone.zonesForModel = () => { throw Error('handler failed'); };
  const failure = await h.api.mcpCall('zones');
  assert.equal(failure.ok, false);
  assert.match(failure.error, /handler failed/);
  assert.equal(h.api.busy(), false);
  assert.equal(h.lease.ends, 2);
  assert.equal(h.observed.at(-1), false, 'failure also publishes idle');

  h.lease.allowed = false;
  const rejected = await h.api.mcpCall('zones');
  assert.equal(rejected.ok, false);
  assert.equal(h.lease.ends, 2, 'rejected call does not release another owner');

  const uiFailure = harness();
  uiFailure.window.__observeBusy = () => { throw Error('render failed'); };
  assert.equal((await uiFailure.api.mcpCall('zones')).ok, true,
    'UI repaint failure does not replace the completed handler result');
  assert.equal(uiFailure.api.busy(), false);

  const missingIdentity = harness();
  delete missingIdentity.window.SPBSourceLoadTransaction;
  const unsafe = await missingIdentity.api.mcpCall('zones');
  assert.equal(unsafe.ok, false, 'missing document identity refuses safely');
  assert.match(unsafe.error, /source document identity is unavailable/);
  assert.equal(missingIdentity.api.busy(), false);
  assert.equal(missingIdentity.lease.ends, 1, 'refusal still releases its own lease');
  console.log('PASS real MCP completion: idle publication, failure cleanup, ownership rejection and UI failure');
})().catch(error => { console.error(error); process.exitCode = 1; });
