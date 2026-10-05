'use strict';
// Fresh W4 semantic probes. These paraphrase six error families and inspect
// relevant topic citations plus answer content or correct command ownership.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const world = { console, fetch: () => { throw Error('provider called'); } };
world.window = world; world.document = {};
vm.createContext(world);
for (const f of ['js/spb-ai-knowledge.js', 'js/spb-self-help.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, f), 'utf8'), world, { filename: f });
}

function makeState(kind = 'flat') {
  const psd = kind === 'psd';
  return {
    paint: psd ? 'psd' : 'flat',
    layers: psd ? [
      { id: 'body', name: 'Body', role: 'paint', hidden: false },
      { id: 'door-num', name: 'Door Numbers', role: 'decal', hidden: false }
    ] : [{ id: 'body', name: 'Body', role: 'paint', hidden: false }],
    zones: [
      { i: 0, name: 'Roof', muted: false, base: 'gloss', finish: 'Gloss', colourMode: 'solid', colour: '#202020',
        pattern: 'Carbon', patternMode: 'overlay', patternOpacity: 80, spec: 1, catchAll: false, selects: true, layers: [], intensity: 100 },
      { i: 1, name: 'Door', muted: false, base: 'gloss', finish: 'Gloss', colourMode: 'solid', colour: '#b02020',
        pattern: null, patternMode: 'overlay', patternOpacity: 100, spec: 0, catchAll: false, selects: true, layers: [], intensity: 100 }
    ],
    selected: 0, carMap: { known: true, missing: [] }, mode: 'pro', last: null
  };
}

const cases = [
  { id: 'number-size-help', owner: 'help', q: 'Can I make the door number lettering taller while keeping its current color?', state: 'psd', cite: ['hdi.move_logo'], need: /resize|transform|scale|larger|size/i, forbid: /recolou?r|change the color/i },
  { id: 'number-color-command', owner: 'action', q: 'Please recolor the door number cyan and leave its proportions alone.', state: 'psd' },
  { id: 'orbit-car-help', owner: 'help', q: 'Can I orbit this stock car in the booth to check the passenger side?', cite: ['hdi.not_in_shokker'], need: /not available|not in shokker/i, forbid: /rotate a pattern/i },
  { id: 'pattern-rotation-help', owner: 'help', q: 'How do I turn the carbon weave sideways on the roof?', cite: ['hdi.rotate_pattern', 'zone_pattern_rotation'], need: /rotate|rotation/i, forbid: /3d view is not available/i },
  { id: 'flat-preview-size-help', owner: 'help', q: 'How do I zoom the on-screen flat livery view without changing any paint pixels?', cite: ['hdi.preview_bigger'], need: /preview|zoom|display|window/i, forbid: /load your paint|open layered/i },
  { id: 'imperative-load-request', owner: 'action', q: 'Bring the new TGA from my desktop into the source area for me.' },
  { id: 'saved-weak-sim-help', owner: 'help', q: 'The finish looked punchy here but washed out after I loaded the render in iRacing. What could explain that?', cite: ['hdi.look_differs'], need: /iracing|sim|sun|shadow|spec|render/i, forbid: /custom gradient|add a new logo/i },
  { id: 'color-strength-command', owner: 'action', q: 'Make the faded red on my car more saturated.' },
  { id: 'mixed-3d-and-flat-help', owner: 'help', q: 'Can the booth spin the whole car, or should I use the flat preview and channel swatches to inspect this finish?', cite: ['hdi.not_in_shokker'], need: /not available|not in shokker/i, forbid: /zoom and move around/i },
  { id: 'flat-only-inspection-help', owner: 'help', q: 'Where can I check the roughness and clearcoat channels on the flat sheet?', cite: ['channel_previews'], need: /channel|rough|clearcoat|preview/i, forbid: /3d view is not available/i },
  { id: 'roof-clearcoat-control-help', owner: 'help', q: 'Which roof-zone setting reduces its glassy clearcoat reflection?', cite: ['hdi.gloss_level'], need: /clearcoat|b coat|spec|shine|gloss/i, forbid: /change.*color/i },
  { id: 'shiny-preface-roof-command', owner: 'action', q: 'This whole paint feels too shiny; lower clearcoat on the roof only, please.' }
];

const failures = [];
const outcomes = [];
for (const c of cases) {
  const state = makeState(c.state || 'flat');
  const before = JSON.stringify(state);
  const classified = world.SpbSelfHelp.classify(c.q);
  const answer = world.SpbSelfHelp.handle(c.q, state);
  try {
    assert.equal(JSON.stringify(state), before, 'helper mutated supplied state');
    if (c.owner === 'action') {
      assert.equal(answer, null, 'direct edit/load request must remain with command owner');
    } else {
      assert.ok(answer && typeof answer.text === 'string', 'help question must receive an answer');
      assert.ok(c.cite.some(id => answer.cites.includes(id)), `expected topic/UI citation ${c.cite.join('/')} but got ${answer.cites.join(',')}`);
      assert.match(answer.text, c.need, 'answer lacks useful guidance for the specific question');
      if (c.forbid) assert.doesNotMatch(answer.text, c.forbid, 'answer contains misleading neighboring guidance');
    }
    outcomes.push({ id: c.id, owner: c.owner, kind: classified && classified.kind, topics: (classified && classified.topics || []).map(x => x.id), cites: answer && answer.cites || [], status: 'pass' });
  } catch (e) {
    failures.push(`${c.id}: ${e.message}`);
    outcomes.push({ id: c.id, owner: c.owner, kind: classified && classified.kind, topics: (classified && classified.topics || []).map(x => x.id), cites: answer && answer.cites || [], status: 'fail', reason: e.message, answer: answer && answer.text });
  }
}

console.log((failures.length ? 'FAIL' : 'PASS') + ` W4 independent semantic review: ${cases.length - failures.length}/${cases.length}`);
console.log(JSON.stringify(outcomes, null, 2));
if (failures.length) { console.error(failures.join('\n')); process.exitCode = 1; }
