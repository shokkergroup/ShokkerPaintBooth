'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const vm = require('node:vm');
const base = '_easy_claude_work/ai14h_w72_candidate';
const freeze = JSON.parse(fs.readFileSync(`${base}/source-freeze.json`, 'utf8'));
function sha(p) { return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex'); }
for (const [name, expected] of Object.entries(freeze.hashes)) assert.equal(sha(`${base}/${name}`), expected, `frozen input changed: ${name}`);
const canvasSrc = fs.readFileSync(`${base}/canvas/paint-booth-3-canvas.js`, 'utf8');
const proSrc = fs.readFileSync(`${base}/js/spb-pro-ai.js`, 'utf8');
function extractFunction(source, signature) {
  const start = source.indexOf(signature); assert(start >= 0, `missing ${signature}`);
  const brace = source.indexOf('{', start); let depth = 0, quote = null, escaped = false, lineComment = false, blockComment = false;
  for (let i = brace; i < source.length; i++) {
    const c = source[i], n = source[i+1];
    if (lineComment) { if (c === '\n') lineComment = false; continue; }
    if (blockComment) { if (c === '*' && n === '/') { blockComment = false; i++; } continue; }
    if (quote) { if (escaped) escaped = false; else if (c === '\\') escaped = true; else if (c === quote) quote = null; continue; }
    if (c === '/' && n === '/') { lineComment = true; i++; continue; }
    if (c === '/' && n === '*') { blockComment = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { quote = c; continue; }
    if (c === '{') depth++;
    else if (c === '}' && --depth === 0) return source.slice(start, i+1);
  }
  throw new Error(`unterminated ${signature}`);
}
function contextWith(code, values={}) { const ctx=vm.createContext({Object,String,RegExp,JSON,Array,Number,Math,Error,...values}); vm.runInContext(code,ctx); return ctx; }

// The actual candidate helper chooses self-describing layered source identity.
const layeredFingerprint = extractFunction(canvasSrc, 'function _spbLayeredSourceFingerprint(');
const c = contextWith(`${layeredFingerprint}; this.f = _spbLayeredSourceFingerprint;`);
const shaA = 'a'.repeat(64), shaB = 'b'.repeat(64), comp = 'c'.repeat(64);
assert.equal(c.f({sourceBytesSha256:shaA}, comp), `file-sha256:${shaA}`);
assert.equal(c.f({sourceBytesSha256:shaB}, comp), `file-sha256:${shaB}`);
assert.notEqual(c.f({sourceBytesSha256:shaA}, comp), c.f({sourceBytesSha256:shaB}, comp), 'same composite with different source bytes must not share committed identity');
assert.equal(c.f({}, undefined), '', 'old backend begins with unset identity until composite digest exists');
assert.equal(c.f({}, comp), `composite-sha256:${comp}`, 'old backend gets explicitly weak composite identity');
assert.throws(() => c.f({sourceBytesSha256:''}, comp), /invalid source byte fingerprint/, 'present empty digest fails closed');
assert.throws(() => c.f({sourceBytesSha256:'A'.repeat(64)}, comp), /invalid source byte fingerprint/, 'uppercase is rejected; wire contract is lower-hex');
assert.throws(() => c.f({sourceBytesSha256:'z'.repeat(64)}, comp), /invalid source byte fingerprint/);
assert.equal(c.f({}, 'fnv1a32-12345678-123'), 'composite-fnv1a32:fnv1a32-12345678-123', 'legacy weak digest remains loadable but algorithm-labeled');
assert.equal(c.f({sourceBytesSha256:shaA}, 'not-a-composite-digest'), `file-sha256:${shaA}`, 'valid raw digest does not depend on preview digest');

// Execute the actual durable memory gate through the real init callback supplied
// by ensurePartMemoryRuntime; unrelated app globals are only construction stubs.
const gateFn = extractFunction(proSrc, 'function durablePartMemorySourceIdentityCurrent(');
const ensureFn = extractFunction(proSrc, 'function ensurePartMemoryRuntime(');
let kind = 'layered', currentFingerprint = `composite-sha256:${comp}`, capturedHooks = null, sourceReads = 0;
const windowObj = {
  SPBSourceLoadTransaction: { getCommittedKind: () => kind },
  SpbAIPartMemoryProject: { createRuntime: (_memory, hooks) => { capturedHooks=hooks; return { ready:true }; } },
  SpbAIPartMemory: {}
};
const mctx = contextWith(`var _partMemoryRuntime=null; var window=${'windowValue'}; var CAR={}; var currentFingerprint='composite-sha256:${comp}'; var sourceReads=0;\nfunction scopedPartSourceNow(){sourceReads++;return {path:'C:/car.psd',fingerprint:currentFingerprint,generation:9};}\nfunction editKey(){} function partMemoryHash(){} function partMemoryOwnerCount(){} function partOwnerCurrent(){} function partMemoryRich(){} function partMemorySource(){} function carSig(){return 'car';}\n${gateFn}\n${ensureFn}\nthis.ensure=ensurePartMemoryRuntime;`, { windowValue:windowObj });
mctx.ensure();
assert.equal(capturedHooks.isCommitted('C:/car.psd', currentFingerprint, 9), false, 'weak layered fallback cannot be captured/hydrated durably');
assert.equal(mctx.sourceReads, 0, 'durable weak-source gate stops before full owner proof');
mctx.currentFingerprint = `file-sha256:${shaA}`;
assert.equal(capturedHooks.isCommitted('C:/car.psd', mctx.currentFingerprint, 9), true, 'strong layered byte identity remains usable');
mctx.currentFingerprint = `composite-fnv1a32:fnv1a32-12345678-123`;
assert.equal(capturedHooks.isCommitted('C:/car.psd', mctx.currentFingerprint, 9), false, 'legacy no-WebCrypto layered fingerprint remains weak');
kind = 'file'; mctx.currentFingerprint = `preview-sha256:${comp}`;
assert.equal(capturedHooks.isCommitted('C:/car.psd', mctx.currentFingerprint, 9), true, 'other committed source kinds preserve existing persistence policy');

// The actual edit-queue guard now recognizes unresolved saved provenance too.
const editKeyFn = extractFunction(proSrc, 'function editKey(');
const partRegionKeyFn = extractFunction(proSrc, 'function partRegionKey(');
const priorFn = extractFunction(proSrc, 'function hasPriorPartIdentity(');
const priorCtx = contextWith(`${partRegionKeyFn}\n${editKeyFn}\n${priorFn}\nthis.key=editKey({part:'roof'}); this.has=hasPriorPartIdentity;`);
const roofKey = priorCtx.key;
assert.equal(priorCtx.has([{_aiPartProv:{r:'{"part":"roof"}'}}], roofKey), true, 'live owner remains recognized');
assert.equal(priorCtx.has([{_spbAIPartMemoryPending:{provenance:{r:'{"part":"roof"}'}}}], roofKey), true, 'inert saved roof remains a blocker to source-color duplicate creation');
assert.equal(priorCtx.has([{_spbAIPartMemoryPending:{provenance:{r:'{"part":"hood"}'}}}], roofKey), false, 'different pending selector does not block');
assert.equal(priorCtx.has([{_spbAIPartMemoryPending:{provenance:{r:'{'}}}], roofKey), false, 'malformed inert metadata is ignored safely');
assert.equal(priorCtx.has([null, {}], roofKey), false);
assert.match(proSrc, /var priorPart = hasPriorPartIdentity\(zones, key\);/, 'actual queue branch consumes pending-aware predicate');

// Drive the actual queueEditZones source, not only its predicate: pending saved
// roof provenance blocks an unsafe add(source), while unrelated pending scope
// still permits the requested new zone.
const queueFn = extractFunction(proSrc, 'function queueEditZones(');
function queueWithPending(pendingRegion) {
  const qctx = contextWith(`${partRegionKeyFn}\n${editKeyFn}\n${priorFn}\n${queueFn}\n` +
    `var zones=[{id:'saved-1',name:'Unresolved saved roof',muted:false,_spbAIPartMemoryPending:{provenance:{r:${JSON.stringify(JSON.stringify(pendingRegion))}}}}];` +
    `var _editReg={},_editRegSig='car',_editRegPendingBefore={}; var addCalls=0; var CAR={}; var window={};` +
    `function carSig(){return 'car';} function scopedPartProofAt(){return null;} function scopedPartProofMatches(){return false;} function friendlyZoneError(e){return String(e);} function editPlural(){return false;}` +
    `function add(spec){addCalls++;return {region_check:{share_pct:40}};} function edit(){return {}}` +
    `this.run=function(){return queueEditZones({zones:[{name:'requested roof',region:{part:'roof'},color:'source',_meta:{label:'roof'}}]},add,edit,{});}; this.calls=function(){return addCalls;};`);
  return {result:qctx.run(), calls:qctx.calls()};
}
const pendingRoofQueue = queueWithPending({part:'roof'});
assert.equal(pendingRoofQueue.calls, 0, 'saved unresolved source-color roof must not be added over original paint');
assert.equal(pendingRoofQueue.result.errs.length, 1);
assert.match(pendingRoofQueue.result.errs[0], /cannot safely keep the existing part colour/);
const pendingHoodQueue = queueWithPending({part:'hood'});
assert.equal(pendingHoodQueue.calls, 1, 'pending unrelated hood does not block adding source-colored roof');
assert.equal(pendingHoodQueue.result.errs.length, 0);

console.log(JSON.stringify({status:'PASS',cases:21,groups:{fingerprintSelection:10,durableGateThroughActualInitHook:4,pendingOwnerPredicate:5,actualQueuePendingControls:2},note:'fingerprint and gate helpers plus actual init hook and actual queueEditZones were extracted from candidate source; no full app/cold-load was run'}, null, 2));


