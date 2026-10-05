'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const controls = require('../_easy_claude_work/ai14h_material_grammar_w111_successor/candidate/spb-ai-material-controls.js');

const root = path.resolve(__dirname, '..');
const candidatePath = path.join(root, '_easy_claude_work/ai14h_material_grammar_w111_successor/candidate/spb-ai-material-controls.js');
const basePath = path.join(root, '_easy_claude_work/ai14h_generation3_runtime12/js/spb-ai-material-controls.js');
const oraclePath = path.join(root, '_easy_claude_work/ai14h_material_grammar_w111_successor/fresh-oracle.json');
const candidateBytes = fs.readFileSync(candidatePath);
const baseBytes = fs.readFileSync(basePath);
const oracleBytes = fs.readFileSync(oraclePath);
const oracle = JSON.parse(oracleBytes);
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
assert.equal(sha(baseBytes), '8febce88b5e1e1f6e5d571037374a8c5a662b1f3d62c323b73b3ea1e5072544b', 'Runtime12 base pin');
assert.equal(sha(oracleBytes), '1f3a5511cab1be5c6c508264ceb48b19178d5d2a59d78f7be16f7d53c7bfE335'.toLowerCase(), 'frozen fresh oracle pin');
assert.equal(oracle.cases.length, 17);
assert.equal(oracle.frozenBeforeCandidateEdit, true);

// Prove the private module differs from frozen Runtime12 only by the one
// anchored target-first clearcoat normalizer line.
const oldText = baseBytes.toString('utf8'), newText = candidateBytes.toString('utf8');
const oldLines = oldText.split(/\r?\n/), newLines = newText.split(/\r?\n/);
assert.equal(newLines.length, oldLines.length, 'candidate line count');
const differences = oldLines.map((line,i)=>line===newLines[i]?-1:i).filter(i=>i>=0);
assert.equal(differences.length, 1, 'candidate has exactly one changed source line');
const changedLine = newLines[differences[0]];
assert.match(changedLine, /\^on the \('\s*\+ parts \+ '\),\?\\\\s\+\(raise\|increase\|lower\|decrease\)/, 'changed line remains anchored to one exact target-first phrase');
assert.match(changedLine, /channel.*\(\?:by\\\\s\+\)\?\(\[\+\]\?\[0-9\]\+\).*points/, 'changed line requires a clearcoat channel and integer points');

const expected = {
  'natural-on-roof-by-points': ['edit', 'roof', 'clearcoat', 20],
  'natural-no-comma': ['edit', 'roof', 'clearcoat', 20],
  'shift-roof-up-control': ['edit', 'roof', 'clearcoat', 20],
  'natural-hood-down': ['edit', 'hood', 'clearcoat', -7],
  'raise-channel-on-roof': ['edit', 'roof', 'clearcoat', 11],
  'channel-amount-first': ['clarify'],
  'left-side-exact-target': ['edit', 'left side', 'clearcoat', 15],
  'question-no-plan': ['delegate'],
  'prohibited-no-plan': ['delegate'],
  'or-target-clarify': ['clarify'],
  'mixed-channel-clarify': ['clarify'],
  'percent-reject': ['clarify'],
  'absolute-target-reject': ['clarify'],
  'missing-unit-reject': ['clarify'],
  'negative-amount-reject': ['clarify'],
  'unknown-target-reject': ['clarify'],
  'extra-paint-action-reject': ['clarify']
};

function proveEdit(text, part, delta, id) {
  const parsed = controls.parse(text);
  assert.equal(parsed.kind, 'edit', id + ' parser kind');
  assert.equal(parsed.part, part, id + ' exact part');
  assert.equal(parsed.channel, 'clearcoat', id + ' exact channel');
  assert.equal(parsed.delta, delta, id + ' signed point delta');
  const zone = {id:'zone-'+id, name:'Existing '+part, specShiftR:13, specShiftG:27, specShiftB:31,
    base:'base::f_soft_gloss', baseColor:'#123456', pattern:{id:'existing'}, regionMask:new Uint8Array([1,0,1])};
  const before = { ...zone, pattern:JSON.stringify(zone.pattern), regionMask:Array.from(zone.regionMask) };
  const built = controls.buildEdit(zone, parsed);
  assert.equal(built.kind, 'edit', id + ' builder kind');
  assert.equal(built.zone_id, zone.id, id + ' existing zone identity');
  assert.deepEqual(built.spec_shift, {metal:13, rough:27, clearcoat:Math.max(-127,Math.min(127,31+delta))}, id + ' clearcoat-only delta');
  assert.deepEqual({ ...zone, pattern:JSON.stringify(zone.pattern), regionMask:Array.from(zone.regionMask) }, before, id + ' pure builder');
}

const rows = [];
for (const c of oracle.cases) {
  const p = controls.parse(c.request), exp = expected[c.id];
  assert(exp, 'expectation exists for ' + c.id);
  assert.equal(p.kind, exp[0], c.id + ' kind: ' + JSON.stringify(p));
  if (exp[0] === 'edit') {
    assert.equal(p.part, exp[1], c.id + ' part');
    assert.equal(p.channel, exp[2], c.id + ' channel');
    assert.equal(p.delta, exp[3], c.id + ' delta');
    proveEdit(c.request, exp[1], exp[3], c.id);
  } else {
    assert.notEqual(p.kind, 'edit', c.id + ' must not become an executable edit');
  }
  rows.push({id:c.id, pass:true, parsed:p.kind, part:p.part||null, channel:p.channel||null, delta:p.delta==null?null:p.delta, reason:p.reason||null});
}

// Preserve the prior W110 alternate-word-order and malformed-input controls.
const w110 = [
  ['On the roof, raise the clearcoat channel 20 points.','edit','roof','clearcoat',20],
  ['Shift roof clearcoat up by 20 points','edit','roof','clearcoat',20],
  ['Shift roof clearcoat channel down by 20 points','edit','roof','clearcoat',-20],
  ['On the roof, raise clearcoat channel -20 points','clarify'],
  ['Shift roof clearcoat up by 20%','clarify'],
  ['On the roof, raise clearcoat channel 20 points and decrease roughness by 5 points','clarify'],
  ['On the engine bay, raise the clearcoat channel 20 points','clarify'],
  ['Shift roof clearcoat up by 20 points and lower roughness by 5 points','clarify'],
  ['Increase clearcoat channel on the roof by 6 points','edit','roof','clearcoat',6],
  ['Increase roof clearcoat channel by 6 points','edit','roof','clearcoat',6]
];
for (let i=0;i<w110.length;i++) {
  const [text,kind,part,channel,delta]=w110[i], p=controls.parse(text), id='W110-'+String(i+1).padStart(2,'0');
  assert.equal(p.kind,kind,id+' kind');
  if(kind==='edit') { assert.equal(p.part,part,id+' part');assert.equal(p.channel,channel,id+' channel');assert.equal(p.delta,delta,id+' delta');proveEdit(text,part,delta,id); }
  else assert.notEqual(p.kind,'edit',id+' refusal');
  rows.push({id,pass:true,parsed:p.kind});
}

console.log(JSON.stringify({status:'PASS_PRIVATE_MATERIAL_GRAMMAR',pins:{baseSha256:sha(baseBytes),candidateSha256:sha(candidateBytes),oracleSha256:sha(oracleBytes)},counts:{fresh:oracle.cases.length,freshPassed:oracle.cases.length,w110: w110.length,w110Passed:w110.length,providerCalls:0,nativeCalls:0,serverCalls:0,applyCalls:0},rows,limits:['Tests the actual pinned module parse/buildEdit APIs. Builder behavior is checked with controlled existing-zone fixtures; no controller dispatch, current-session proof, native app, provider, backend, or pixels were exercised.']},null,2));
