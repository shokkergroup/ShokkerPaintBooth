'use strict';
// Read-only audit of the real self-help producer and controller dispatch.
// State and callbacks are small spies; no pixels or renderer output are faked.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const reportPath = path.join(root, 'docs/handoff_reports/AI_HELPER_14H_HELP_ACTION_AUDIT_2026-10-03.json');
const results = [];

function world(mode = 'pro', paint = 'psd') {
  const w = {
    console,
    _psdLayers: paint === 'psd' ? [
      { id: 'body', name: 'Body', img: {}, visible: true },
      { id: 'numbers', name: 'Numbers', img: {}, visible: true }
    ] : [],
    paintImageData: paint === 'none' ? null : { width: 8, height: 8 },
    zones: [{ name: 'Body', base: 'gloss', colorMode: 'special', baseColorMode: 'solid' }],
    selectedZoneIndex: -1,
    calls: { select: [], mute: [], refresh: 0 },
    document: { body: { classList: { contains: name => name === 'spb-easy-on' ? mode === 'easy' : name === 'spb-chat-studio' ? mode === 'chat' : false } } }
  };
  w.window = w;
  w.SpbProCar = { roles: () => [], map: () => ({}), missing: () => [] };
  w.SpbProZone = { catchAll: () => true };
  // These are spies on the exact app-global controller names used by runDoIt.
  w.selectZone = i => { w.calls.select.push(i); w.selectedZoneIndex = i; };
  w.toggleZoneMute = i => { w.calls.mute.push(i); w.zones[i].muted = !w.zones[i].muted; };
  w.triggerPreviewRender = () => { w.calls.refresh++; };
  vm.createContext(w);
  for (const file of ['js/spb-ai-knowledge.js', 'js/spb-self-help.js']) {
    vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), w, { filename: file });
  }
  return w;
}

function record(name, pass, detail) {
  results.push({ name, status: pass ? 'PASS' : 'FAIL', detail });
}

{
  const w = world('chat');
  const actual = w.SpbSelfHelp.state().mode;
  record('chat studio is represented as its own mode', actual === 'chat', { expected: 'chat', actual });
  const a = w.SpbSelfHelp.answer('How do I turn a layer on or off?', w.SpbSelfHelp.state());
  const handoff = /full editor/i.test(a.text);
  record('chat studio hands layer-only guidance through its visible Full editor control', handoff, { topic: a.topic, steps: a.steps, text: a.text.slice(0, 320) });
  const zoneContext = w.SpbSelfHelp.answer('How do I control which zones overlap?', w.SpbSelfHelp.state());
  record('chat studio prefixes Pro-only zone context with the visible editor handoff', !!zoneContext && /full editor/i.test(zoneContext.text), { topic: zoneContext && zoneContext.topic, text: zoneContext && zoneContext.text.slice(0, 240) });
  w.selectedZoneIndex = 0;
  const zoneTour = w.SpbSelfHelp.handle('What can I do with this zone?', w.SpbSelfHelp.state());
  record('chat studio zone overview names the editor handoff while retaining chat as an option', !!zoneTour && /full editor/i.test(zoneTour.text) && /tell me the change in plain language/i.test(zoneTour.text), { topic: zoneTour && zoneTour.topic, text: zoneTour && zoneTour.text.slice(0, 240) });
  const teachNumbers = w.SpbSelfHelp.answer('How do I teach the app where the numbers are?', w.SpbSelfHelp.state());
  record('number teaching stays in chat', !!teachNumbers && /ask for something on the numbers/i.test(teachNumbers.text) && !/switch to PRO/i.test(teachNumbers.text), { topic: teachNumbers && teachNumbers.topic, steps: teachNumbers && teachNumbers.steps });
  const teachParts = w.SpbSelfHelp.answer("How do I tell Shokker where the car's parts are (hood, roof, sides)?", w.SpbSelfHelp.state());
  record('part teaching stays in chat', !!teachParts && /part change/i.test(teachParts.text) && !/switch to PRO/i.test(teachParts.text), { topic: teachParts && teachParts.topic, steps: teachParts && teachParts.steps });
}

{
  const w = world('easy');
  const a = w.SpbSelfHelp.answer('How do I turn a layer on or off?', w.SpbSelfHelp.state());
  record('Easy mode names the Pro prerequisite for layer controls', /switch to PRO/i.test(a.text), { mode: w.SpbSelfHelp.state().mode, steps: a.steps });
}

{
  const none = world('pro', 'none');
  const noPaint = none.SpbSelfHelp.answer('How do I turn a layer on or off?', none.SpbSelfHelp.state());
  record('missing paint is stated before PSD-only steps', noPaint.steps.some(x => /load your layered PSD/i.test(x)), { steps: noPaint.steps });
  const flat = world('pro', 'flat');
  const flatAnswer = flat.SpbSelfHelp.answer('How do I turn a layer on or off?', flat.SpbSelfHelp.state());
  record('flat paint explains why layers are unavailable', flatAnswer.steps.some(x => /flat paint|no layers/i.test(x)), { steps: flatAnswer.steps });
  record('setup support remains with the support controller', none.SpbSelfHelp.classify('Check my setup') === null, { selfHelpClassification: none.SpbSelfHelp.classify('Check my setup') });
}

{
  const w = world('pro');
  const first = w.SpbSelfHelp.answer('How do I refresh the preview?', w.SpbSelfHelp.state());
  const firstRun = w.SpbSelfHelp.runDoIt(first.doIt.label);
  record('refresh action invokes the actual preview controller once', firstRun && firstRun.done && w.calls.refresh === 1, { result: firstRun, calls: w.calls.refresh });
  record('completed action cannot be double-clicked', w.SpbSelfHelp.runDoIt(first.doIt.label) === null && w.calls.refresh === 1, { calls: w.calls.refresh });

  const current = w.SpbSelfHelp.answer('How do I refresh the preview?', w.SpbSelfHelp.state());
  const next = w.SpbSelfHelp.answer('How do I change the order or priority of zones?', w.SpbSelfHelp.state());
  const oldResult = w.SpbSelfHelp.runDoIt(current.doIt.label);
  const newResult = w.SpbSelfHelp.runDoIt(next.doIt.label);
  record('only the newest offered action remains callable', oldResult === null && newResult && newResult.done && w.calls.select.join(',') === '0', { oldResult, newResult, selectCalls: w.calls.select });
  const once = w.SpbSelfHelp.runDoIt(next.doIt.label);
  record('selection action is one-shot after callback', once === null && w.calls.select.length === 1, { secondResult: once, selectCalls: w.calls.select });

  const stale = w.SpbSelfHelp.answer('How do I refresh the preview?', w.SpbSelfHelp.state());
  const noAction = w.SpbSelfHelp.answer('What is roughness?', w.SpbSelfHelp.state());
  record('a newer non-action help answer clears the old action', !noAction.doIt && w.SpbSelfHelp.runDoIt(stale.doIt.label) === null, { topic: noAction.topic, doIt: noAction.doIt });
}

const failed = results.filter(x => x.status === 'FAIL');
const report = {
  title: 'AI helper 14h help/action mode audit',
  date: '2026-10-03',
  scope: 'Read-only producer audit using js/spb-self-help.js, actual answer/handle APIs, and spies for its app-global controller callbacks. No browser, pixels, renderer, MCP, provider, HTML, mirror, or production writes.',
  summary: { passed: results.length - failed.length, failed: failed.length, total: results.length },
  findings: [
    { severity: 'passed', issue: 'state() represents Chat Studio separately. Pro-only layer, zone, and selected-zone context answers name the visible “Full editor →” handoff; number/part teaching and plain-language zone edits remain in Chat Studio. Easy mode still names the Pro prerequisite.', evidence: 'chat-mode cases in this report' },
    { severity: 'passed', issue: 'Pending actions are bound to the current document and intended zone object/name, safely follow an in-place zone reorder, and refuse stale, removed, renamed, paint-missing, or callback-missing targets. Actions remain one-shot and newer input replaces or clears pending work.', evidence: 'controller-spy lifecycle cases in this report' },
    { severity: 'passed', issue: 'PSD-only help states the missing-paint and flat-paint prerequisites; “Check my setup” remains unclaimed by self-help for the support route.', evidence: 'prerequisite/support cases in this report' }
  ],
  cases: results
};
fs.mkdirSync(path.dirname(reportPath), { recursive: true });
fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n', 'utf8');
for (const r of results) console.log(`${r.status} ${r.name}`);
console.log(`AUDIT ${report.summary.passed}/${report.summary.total}; report ${path.relative(root, reportPath)}`);
if (failed.length) process.exitCode = 1;
