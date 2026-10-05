const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Fresh semantic oracle authored before inspecting the W2 helper source.
// Ownership correction after the first execution: the polite "Could you
// lower ...?" wording is an edit request, not a how-to question.
// Help cases require relevant answer content and reject misleading neighbors.
const CASES = [
  { id: 'H01', owner: 'action', q: "Could you lower my sponsor layer's opacity to about fifty percent?", state: 'psd' },
  { id: 'H02', owner: 'help', q: 'How do I make the race number art taller and wider?', cite: ['hdi.move_logo'], need: /resize|transform|scale|larger|size/i, forbid: /recolour the numbers|make the numbers purple/i, state: 'psd' },
  { id: 'H03', owner: 'help', q: 'Where can I search for the Sponsors layer in a PSD with hundreds of rows?', cite: ['hdi.find_layer'], need: /search|find|filter/i, forbid: /open layered|load a layered psd|choose your psd/i, state: 'psd' },
  { id: 'H04', owner: 'help', q: 'How do I shrink the carbon weave so its squares look finer?', cite: ['hdi.pattern_finer', 'zone_base_scale', 'zone_pattern_scale'], need: /scale|smaller|fine|size/i, forbid: /put a finish on a zone/i, state: 'flat' },
  { id: 'H05', owner: 'help', q: 'How can I clear the current flames pattern off this zone?', cite: ['hdi.remove_pattern'], need: /remove|clear|none|off/i, forbid: /pick a pattern|add a pattern/i, state: 'flat' },
  { id: 'H06', owner: 'help', q: 'What does flat paint mean compared with a layered PSD?', cite: ['hdi.what_are_layers'], need: /one picture|single image|separate layers|layered psd/i, forbid: /click.{0,30}(merge|flatten)|merge or flatten/i, state: 'flat' },
  { id: 'H07', owner: 'help', q: 'Can I turn the car around in this preview and look at its side panels?', cite: ['hdi.not_in_shokker'], need: /not available|not in shokker/i, forbid: /rotate a pattern|teach shokker where the car|zoom and move around/i, state: 'flat' },
  { id: 'H08', owner: 'help', q: 'Does Shokker have a 3D car viewer where I can orbit the livery?', cite: ['hdi.not_in_shokker'], need: /not available|not in shokker/i, forbid: /rotate a pattern|teach shokker where the car/i, state: 'flat' },
  { id: 'H09', owner: 'help', q: 'Can I rotate the pattern so it runs vertically?', cite: ['hdi.rotate_pattern', 'zone.pattern_rotation'], need: /rotate|rotation/i, forbid: /3d view is not available/i, state: 'flat' },
  { id: 'H10', owner: 'help', q: 'Where do I make the flat paint preview larger without changing the artwork?', cite: ['hdi.preview_bigger'], need: /preview/i, forbid: /3d view is not available/i, state: 'flat' },
  { id: 'H11', owner: 'help', q: 'The finish looks weak after I save and view it in iRacing. What should I check?', cite: ['hdi.look_differs'], need: /iracing|sim|sun|shadow|spec|render/i, forbid: /custom gradient|add a new logo/i, state: 'flat' },
  { id: 'H12', owner: 'help', q: 'Can I inspect the whole car in 3D here, or is this only a flat paint view?', cite: ['hdi.not_in_shokker'], need: /not available|not in shokker/i, forbid: /zoom and move around|see the spec map/i, state: 'flat' },
  { id: 'H13', owner: 'help', q: 'How do I reopen a saved SHOKK project and keep its zones?', cite: ['hdi.save_project'], need: /save \/ open|shokk|zones/i, forbid: /load a flat paint only/i, state: 'psd' },
  { id: 'H14', owner: 'help', q: 'How do I make red fade gradually into blue across the paint?', cite: ['hdi.gradient'], need: /gradient|colour stops|color stops/i, forbid: /looks the same in iracing/i, state: 'flat' },
  { id: 'H15', owner: 'help', q: 'Why do my paint colors look washed out once the car loads in the sim?', cite: ['hdi.look_differs'], need: /iracing|sim|sun|shadow|preview/i, forbid: /custom gradient/i, state: 'flat' },
  { id: 'H16', owner: 'help', q: 'How do I add shine while leaving the body color alone?', cite: ['hdi.spec_only_shine'], need: /shine|spec|reflect/i, forbid: /change only one colour|custom gradient/i, state: 'flat' },
  { id: 'C01', owner: 'action', q: 'Full vehicle chrome, but do not touch the left side.', state: 'flat' },
  { id: 'C02', owner: 'action', q: 'Please make the sponsor layer half transparent.', state: 'psd' },
  { id: 'C03', owner: 'action', q: 'Could you stretch the number artwork larger for me?', state: 'psd' },
  { id: 'C04', owner: 'action', q: 'The Sponsors layer is too hard to see. Tone it down a little.', state: 'psd' },
  { id: 'C05', owner: 'action', q: 'No, keep the body red and only turn the door silver.', state: 'flat' },
  { id: 'C06', owner: 'action', q: 'That last change is wrong; make only the hood matte instead.', state: 'flat' },
  { id: 'C07', owner: 'action', q: 'Everything is too shiny; lower clearcoat on the roof only.', state: 'flat' },
  { id: 'C08', owner: 'action', q: 'Could you move the sponsor logo onto the rear quarter?', state: 'psd' }
];

const root = path.resolve(__dirname, '..');
const world = { console };
let providerCalls = 0;
world.fetch = () => { providerCalls++; throw new Error('provider call in offline self-help'); };
world.XMLHttpRequest = function () { providerCalls++; throw new Error('provider call in offline self-help'); };
vm.createContext(world);
world.window = world;
world.document = {};
for (const file of ['js/spb-ai-knowledge.js', 'js/spb-self-help.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), world, { filename: file });
}

function makeState(kind) {
  const psd = kind === 'psd';
  const s = {
    paint: psd ? 'psd' : (kind === 'none' ? 'none' : 'flat'),
    layers: psd ? [
      { id: 'paint', name: 'Body', role: 'paint', hidden: false },
      { id: 'sponsors', name: 'Sponsors', role: 'decal', hidden: false },
      { id: 'numbers', name: 'Numbers', role: 'decal', hidden: false }
    ] : (kind === 'none' ? [] : [{ id: 'paint', name: 'Body', role: 'paint', hidden: false }]),
    zones: kind === 'none' ? [] : [{
      i: 0, name: 'Body', muted: false, base: 'Gloss', finish: 'Gloss', colourMode: 'finish', colour: null,
      pattern: 'Flames', patternMode: 'overlay', patternOpacity: 100, spec: 1, catchAll: false,
      selects: true, layers: [], intensity: 100
    }],
    selected: kind === 'none' ? -1 : 0,
    carMap: { known: true, missing: [] },
    mode: 'pro',
    last: null
  };
  return deepFreeze(s);
}
function deepFreeze(x) {
  Object.freeze(x);
  Object.keys(x).forEach((k) => { if (x[k] && typeof x[k] === 'object' && !Object.isFrozen(x[k])) deepFreeze(x[k]); });
  return x;
}

const failures = [];
for (const c of CASES) {
  const state = makeState(c.state);
  const before = JSON.stringify(state);
  const a = world.SpbSelfHelp.handle(c.q, state);
  try {
    assert.equal(JSON.stringify(state), before, `${c.id} mutated the supplied app state`);
    if (c.owner === 'action') {
      assert.equal(a, null, `${c.id} belongs to the action/advisor owner, got ${JSON.stringify(a && { intent: a.intent, topic: a.topic, cites: a.cites, text: a.text })}`);
    } else {
      assert.ok(a && typeof a.text === 'string', `${c.id} should receive offline guidance`);
      assert.ok(c.cite.some((id) => a.cites.includes(id)), `${c.id} should cite the intended help topic ${c.cite.join('/')}, got ${a.cites.join(',')}`);
      assert.match(a.text, c.need, `${c.id} answer lacks the requested guidance`);
      assert.doesNotMatch(a.text, c.forbid, `${c.id} answer gives misleading neighboring guidance`);
    }
  } catch (e) {
    failures.push(`${c.id} (${c.owner}): ${e.message}`);
  }
}
if (providerCalls !== 0) failures.push(`unexpected provider calls: ${providerCalls}`);
if (failures.length) {
  console.error(`Semantic self-help review: ${failures.length}/${CASES.length} failures\n${failures.join('\n')}`);
  process.exitCode = 1;
} else {
  console.log('Semantic self-help review: 15 contextual-help tasks and 9 action/correction boundaries passed.');
}
