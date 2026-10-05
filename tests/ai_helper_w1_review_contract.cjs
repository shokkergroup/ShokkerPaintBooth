'use strict';

// Independent lifecycle review: exercise the real element module across reloads,
// with shared localStorage and a stale server read, plus the actual reply copy.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const elementSource = fs.readFileSync(path.join(root, 'js/spb-pro-elements.js'), 'utf8');
const modelSource = fs.readFileSync(path.join(root, 'js/spb-elements-model.js'), 'utf8');
const aiSource = fs.readFileSync(path.join(root, 'js/spb-pro-ai.js'), 'utf8');

function section(source, start, end) {
  const a = source.indexOf(start), b = source.indexOf(end, a + start.length);
  assert(a >= 0 && b > a, `production slice exists: ${start}`);
  return source.slice(a, b);
}

function makeStorage(initial) {
  return {
    value: JSON.stringify(initial || {}),
    getItem() { return this.value; },
    setItem(_key, value) { this.value = value; }
  };
}

function makeElementModule(storage, fetchImpl, carFolder = 'car-a') {
  const context = {
    console, Promise, Buffer, Uint8Array, Uint8ClampedArray, Float32Array,
    localStorage: storage,
    fetch: fetchImpl,
    SPB_ELEMENTS_MODEL: undefined,
    paintImageData: null,
    SpbProCar: { effFolder: () => carFolder },
    setTimeout, clearTimeout, performance: { now: () => Date.now() }
  };
  context.window = context;
  context.global = context;
  vm.createContext(context);
  vm.runInContext(modelSource, context, { filename: 'js/spb-elements-model.js' });
  vm.runInContext(elementSource, context, { filename: 'js/spb-pro-elements.js' });
  const width = 48, height = 40;
  const data = new Uint8ClampedArray(width * height * 4);
  for (let i = 0; i < width * height; i++) {
    data[i * 4] = 72; data[i * 4 + 1] = 83; data[i * 4 + 2] = 94; data[i * 4 + 3] = 255;
  }
  context.paintImageData = { width, height, data };
  return { context, elements: context.SpbProElements };
}

function deferred() {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return { promise, resolve };
}

async function testRejectedProposalSurvivesReload() {
  const staleBox = [0.08, 0.08, 0.2, 0.2];
  const newBox = [0.42, 0.4, 0.55, 0.58];
  const storage = makeStorage({ cara: { numbers: { boxes: [staleBox], how: 'teach' } } });
  const staleGet = deferred();
  const fetchFirst = (url, options) => {
    if (options && options.method === 'POST') return Promise.reject(new Error('offline during forget'));
    return Promise.resolve({ ok: true, json: () => staleGet.promise });
  };
  const first = makeElementModule(storage, fetchFirst);
  const before = await first.elements.analyse({ force: true });
  assert.deepEqual(Array.from(before.kinds.numbers.proposals[0].box), staleBox,
    'the pre-existing learned position is visible as a proposal');
  assert.equal(first.elements.forget('numbers'), true, 'rejecting the remembered proposal removes it locally');
  await Promise.resolve(); // let the best-effort rejected POST settle through its catch

  const staleResponse = {
    rows: [{ key: 'cara', kind: 'numbers', boxes: [staleBox], source: 'server' }]
  };
  const second = makeElementModule(storage, () => Promise.resolve({ ok: true, json: () => Promise.resolve(staleResponse) }));
  await second.elements.analyse({ force: true });
  await Promise.resolve();
  await Promise.resolve();
  const afterStaleFetch = await second.elements.analyse({ force: true });
  assert.deepEqual(Array.from(afterStaleFetch.kinds.numbers.proposals || []), [],
    'a stale server row cannot resurrect a locally rejected proposal after reload');

  assert.equal(second.elements.remember('numbers', [newBox], 'teach'), true,
    'an explicit new teach can replace the rejection');
  const afterNewTeach = await second.elements.analyse({ force: true });
  assert.deepEqual(Array.from(afterNewTeach.kinds.numbers.proposals[0].box), newBox,
    'the explicit new teach appears as the replacement proposal');
}

function testProposalCopyIsTruthful() {
  const elemReply = section(aiSource, '    function elemReply(text, kind, mode) {', '    function elemCardHtml(m) {');
  const context = {
    window: { SpbProElements: { overlay: () => 'current-paint-overlay', thumb: () => 'current-paint-thumb',
      kinds: () => ({ numbers: { learned: true } }) } },
    ELEM_WORD: { numbers: 'numbers' }, ELEM_TINT: { numbers: 'pink' },
    logMiss() {}, elementPaintSig: () => 'sig-current', elementRunIdentity: () => 'identity-current'
  };
  vm.createContext(context);
  vm.runInContext(`${elemReply}\nthis.reply = elemReply('paint these numbers', 'numbers', 'confirm');`, context);
  assert.match(context.reply.text, /remember(?:ed)? suggestions?/i,
    'the card says remembered locations are suggestions');
  assert.match(context.reply.text, /check this paint separately|not .*used .*this paint/i,
    'the card says cross-paint suggestions were not used to mark this paint');
  assert.doesNotMatch(context.reply.text, /added the places .*other paints/i,
    'the old copy no longer implies cross-paint proposals tinted the current paint');
}

(async () => {
  await testRejectedProposalSurvivesReload();
  testProposalCopyIsTruthful();
  console.log('PASS independent AI helper W1 review: rejected proposal lifecycle and confirmation copy');
})().catch(err => { console.error(err); process.exitCode = 1; });
