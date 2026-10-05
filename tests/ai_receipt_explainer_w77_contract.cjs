'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const base = path.join(root, '_easy_claude_work/ai14h_w77_review');
const candidate = process.argv[2] || path.join(base, 'candidate/js/spb-pro-ai.js');
const modulePath = process.argv[3] || path.join(base, 'candidate/js/spb-ai-receipt-explainer.js');
const frozen = path.join(base, 'frozen_runtime3');
const pro = fs.readFileSync(candidate, 'utf8');
const explainer = fs.readFileSync(modulePath, 'utf8');
const expected = {
  controller: 'EEE47A9E461290F97893A721742CBEAC4F1FBB148B37CDFB8696CF9107520574',
  lease: 'DE276372A763310EC051DB141FCB1D601E11DBF193843E2B21A405226F782134',
  operation: '47587A1A53A35CE7E58825BAC864BD75C2421D26C19791957F57BB199A7000C6'
};
function hash(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex').toUpperCase(); }
assert.equal(hash(fs.readFileSync(path.join(frozen, 'spb-pro-ai.js'))), expected.controller, 'Runtime3 controller freeze');
assert.equal(hash(fs.readFileSync(path.join(frozen, 'spb-ai-lease.js'))), expected.lease, 'W36 lease freeze');
assert.equal(hash(fs.readFileSync(path.join(frozen, 'spb-ai-operation.js'))), expected.operation, 'operation manager freeze');
function extract(src, name) {
  const start = src.indexOf(`function ${name}(`); assert(start >= 0, `actual ${name} source exists`);
  let i = src.indexOf('{', start), depth = 0, q = null, esc = false, line = false, block = false;
  for (; i < src.length; i++) { const c = src[i], n = src[i + 1];
    if (line) { if (c === '\n') line = false; continue; }
    if (block) { if (c === '*' && n === '/') { block = false; i++; } continue; }
    if (q) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === q) q = null; continue; }
    if (c === '/' && n === '/') { line = true; i++; continue; }
    if (c === '/' && n === '*') { block = true; i++; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '{') depth++; else if (c === '}' && --depth === 0) return src.slice(start, i + 1);
  }
  throw Error(`unterminated ${name}`);
}
const doc = { generation: 1, committedGeneration: 1, path: 'C:/paint/car.psd', fingerprint: 'file-sha256:abc', canvas: null, width: 64, height: 64, layers: null, image: null, sourceLoading: false, sourceCommitted: true };
const w = { console, Promise, Date, Math, JSON, Object, String, Number, RegExp, Array, Error,
  document: {}, _spbLayerRev: 1, _getZoneConfigHashUncached: () => doc.zoneRevision,
  paintCanvas: { width: 64, height: 64 }, _psdLayers: [{ id: 'layer1' }], paintImageData: null,
  SPBSourceLoadTransaction: {
    getGeneration: () => doc.generation, getCommittedGeneration: () => doc.committedGeneration,
    getCommittedPath: () => doc.path, getCommittedFingerprint: () => doc.fingerprint,
    isLoading: () => doc.sourceLoading, isCommitted: () => doc.sourceCommitted
  }, _busy: false, _skipParts: true, zones: [], _spbLayerRev: 1, queueMutations: 0, providerCalls: 0, finished: [], sentAsk: []
};
w.window = w; vm.createContext(w);
vm.runInContext(fs.readFileSync(path.join(frozen, 'spb-ai-lease.js'), 'utf8'), w, { filename: 'frozen-w36-lease.js' });
vm.runInContext(fs.readFileSync(path.join(frozen, 'spb-ai-operation.js'), 'utf8'), w, { filename: 'frozen-operation-manager.js' });
vm.runInContext(explainer, w, { filename: 'candidate-w77-explainer.js' });
const sendStart = pro.indexOf('function send(text, o)');
const sendEnd = pro.indexOf('    function mergeMaskUndo', sendStart);
assert(sendStart >= 0 && sendEnd > sendStart, 'actual send route boundaries exist');
const actual = (pro.includes('function normalizeOfflineInstruction(') ? ['normalizeOfflineInstruction'] : []).concat(['operationDocument','operationRevision','operationManager','operationTicket','operationEntryDocumentCurrent','operationStart','operationBind','operationCurrent','operationPublish','operationResultCurrent','finishCore']).map(n => extract(pro, n)).join('\n') + '\n' + pro.slice(sendStart, sendEnd);
const stubs = `
var _aiOperation=null,_operationRevisionFailureSerial=0,_log=[],_progress='',_progAI=false,_progT0=0,_progK=0,_progEnd=0,_pendingCard=null,_offlineLast=null,_advLast=null,_advUsed=null,_reqText='',_specOnlyReq=false,_extra={cost:0,calls:0,models:{}},_serial=0,_envMemo=null,_orig=null,_activeId=null,_elemRunIdentity=null,_shm=null,AI=null,paintCanvas=window.paintCanvas,_psdLayers=window._psdLayers,paintImageData=window.paintImageData,_noCheck=false,_cancelOpts=false,_operationRevisionFailureSerial=0;
function operationRefreshDocument(){} function offlineInstructionPreflight(){return null;} function finish(r,text){window.finished.push({r:r,text:text});var answer={role:'ai',request:text,text:r.text||'',lines:[],notes:[],kind:'ask'};operationManager().bind(answer,operationManager().start());_log.push(answer);return r;}
function render(){} function elemCurrentCard(){return null;} function elementPaintSig(){return '';} function elementRunIdentity(){return {};} function elemReplyAction(){return null;} function rshotGrab(){} function complaintChip(){return false;} function complaintOf(){return null;} function kitAsk(){return null;} function advisorIntent(){return null;} var TEACH_RE=/^never-match$/; function teachAll(){return {};} function selfHelpClaim(t){return /^how do i /i.test(t)?{text:'Ordinary guidance remains on self-help.',intent:'guide',topic:'ordinary'}:null;} function selfHelpResult(r){return {offline:true,text:r.text,queue:[],tools:['self_help']};}
function elemOwnsText(){return false;} function supportClass(){return null;} var CHECK_AGAIN_RE=/^never-match$/; var QUESTION_RE=/^(?:how|what|why|can|could|would|is|are|do|does)\b/i; var CLAIM_RE=/\b(?:Done|Updated)\b/i; function supportSend(){return false;} function editPlan(){return null;} function offlineMaterialPlan(){return null;} var D={summarise:function(){return [];},offlinePartCoverage:function(){return null;},offlineIdeas:function(){return null;},lookRequest:function(){return null;},offlineSpec:function(){return null;},offlinePart:function(){return null;},offlineElement:function(){return null;},offlinePlan:function(){return null;},refine:function(){return null;}}; var START_OVER_RE=/^never-match$/; var NUM_FIX_RE=/^never-match$/; function offlineCannot(){return false;} function layerVisRequest(){return false;} function offlineHowtoPeek(){return false;} function offlineScopeReply(){return {text:'ordinary no-config fallback'};} function ask(t){window.sentAsk.push(t);return Promise.resolve({offline:true,queue:[]});} function applyRecipe(){} function noteAction(){} var CAR=null; var _panel=null; var _forceNoClaim=false; var RECENT=[],HIST=[];
function operationCanceled(){return {cancelled:true,queue:[]};} function operationRelease(){} function operationTicketCollection(){return null;} function operationResultCurrent(r){return operationCurrent(operationTicket(r));} function operationTools(t){return t;} function operationTicketCurrent(){return true;} function cost(){return 'local';} function turnTally(){return{};} function mergeTally(){return{};} function parseNext(){} function undoDepth(){return 0;} function undoTrim(){} function undoSeal(){} function portableOp(q){return q;} function maskBudgetNote(){return null;} function diagnose(){return [];} function applyQueue(q){window.queueMutations+=(q||[]).length;if(window.applyResult){var x=window.applyResult;window.applyResult=null;return x;}return {lines:(q||[]).map(x=>x.line||'Roof: colour #d40000'),failed:[],maskUndo:[],layerUndo:0,undoSnap:null,zPushed:[],lPushed:[],results:[]};} function postCheck(e){return Promise.resolve(e);} function rshotWatch(){} function checkNumbersLater(){} function operationAfter(){} function friendlyError(e){return String(e&&e.message||e);}
function makeAppliedReceipt(line){var t=operationStart(),r=operationBind({offline:true,text:'Done — the roof changed.',queue:[{kind:'edit',line:line}],usage:{cost:0},calls:0,tools:['edit_zone']},t);return finishCore(r,'Change the roof','ask',{});}
`;
vm.runInContext(stubs + '\n' + actual + '\nwindow.routeSend=send; window.currentReceipt=operationEntryDocumentCurrent; window.makeTicket=function(){return operationManager().start();}; window.bindTicket=function(v,t){return operationManager().bind(v,t);}; window.makeAppliedReceipt=makeAppliedReceipt;', w, { filename: 'actual-runtime3-send-route.js' });
w.AI = { cached: () => ({ configured: true }) };
w.SpbSelfHelp = { redirect: () => null, runDoIt: () => null, noteAction: () => {} };
function addReceipt(spec) {
  const ticket = w.makeTicket();
  const entry = Object.assign({ role: 'ai', request: 'previous edit', text: 'Done.', lines: [], notes: [], kind: 'ask' }, spec);
  w.bindTicket(entry, ticket); w._log.push(entry); return entry;
}
function reset(docGeneration = 1) { doc.generation = docGeneration; doc.committedGeneration = docGeneration; doc.sourceLoading = false; doc.sourceCommitted = true; w._log = []; w.finished = []; w.sentAsk = []; w.queueMutations = 0; w.providerCalls = 0; w.applyResult = null; w._busy = false; }
async function route(q) { w.routeSend(q); await Promise.resolve(); return w.finished[w.finished.length - 1] || null; }

(async () => {
  const mod = w.SpbAiReceiptExplainer;
  const positive = ['Explain my last change', 'What did you change?', 'Can you explain the most recent edit?', 'What happened with my last change?', 'Can you tell me what you changed last?', 'Explain the last attempt.'];
  const negative = ['How do I change roof colour?', 'Make the roof blue and explain my last change', 'How do I make roof satin, and explain my last change?', 'Explain the last edit then change the hood', 'Did the last edit work?'];
  positive.forEach(q => assert.equal(mod.claim(q), true, q));
  negative.forEach(q => assert.equal(mod.claim(q), false, q));

  reset();
  await w.makeAppliedReceipt('Roof: colour #d40000; finish base::gloss');
  let ent = w._log[w._log.length - 1];
  assert.deepEqual(Array.from(ent.lines), ['Roof: colour #d40000; finish base::gloss'], 'actual finishCore records successful apply lines');
  const appliedQueueCount = w.queueMutations; assert.equal(appliedQueueCount, 1, 'the fixture uses one controlled apply effect to create a real finishCore receipt');
  assert.equal(w.currentReceipt(ent), true);
  let out = await route('Explain my last change');
  assert.match(out.r.text, /Roof: colour #d40000; finish base::gloss/);
  assert.equal(out.r.queue.length, 0); assert.equal(out.r.calls, 0); assert.equal(w.providerCalls, 0); assert.equal(w.queueMutations, appliedQueueCount, 'the read-only explanation adds no queue/apply mutation');

  reset(); w.applyResult = {lines:['Hood: colour #ffcc00','Roof: finish base::f_clear_satin'],failed:[],maskUndo:[],layerUndo:0,undoSnap:null,zPushed:[],lPushed:[],results:[]}; await w.makeAppliedReceipt('two successful changes');
  out = await route('What did you change?'); assert.match(out.r.text, /Hood: colour #ffcc00.*Roof: finish base::f_clear_satin/);
  assert.equal(out.r.queue.length, 0);

  reset(); w.applyResult = {lines:['Left side: colour #d40000'],failed:['Right side: selector missing'],maskUndo:[],layerUndo:0,undoSnap:null,zPushed:[],lPushed:[],results:[]}; await w.makeAppliedReceipt('partial two-part change');
  out = await route('What happened with my last change?'); assert.match(out.r.text, /part of the last edit was applied/); assert.match(out.r.text, /Left side/); assert.match(out.r.text, /Right side: selector missing/);

  reset(); w.applyResult = {lines:[],failed:['roof selector was unavailable'],maskUndo:[],layerUndo:0,undoSnap:null,zPushed:[],lPushed:[],results:[]}; await w.makeAppliedReceipt('failed roof attempt');
  out = await route('Explain the last attempt'); assert.match(out.r.text, /did not apply/); assert.match(out.r.text, /No paint change was applied/); assert.doesNotMatch(out.r.text, /Done\b/);

  reset(); await w.makeAppliedReceipt('Roof: colour #d40000'); w._log[w._log.length-1].undone=true;
  out = await route('Explain my last change'); assert.match(out.r.text, /was undone or replaced/); assert.doesNotMatch(out.r.text, /Roof: colour/);

  reset(); await w.makeAppliedReceipt('Roof: colour #d40000'); w._log[w._log.length-1].superseded=true;
  out = await route('What did you change?'); assert.match(out.r.text, /was undone or replaced/);

  reset(); w.applyResult = {lines:[],failed:[],maskUndo:[],layerUndo:0,undoSnap:null,zPushed:[],lPushed:[],results:[]}; await w.makeAppliedReceipt('unused line'); w._log[w._log.length-1].text='Done — the car is blue.';
  out = await route('What did you change?'); assert.match(out.r.text, /current, verified apply receipt/); assert.doesNotMatch(out.r.text, /blue/);

  reset(); await w.makeAppliedReceipt('Prior source: roof blue');
  doc.generation = 2; doc.committedGeneration = 2;
  out = await route('What did you change?'); assert.match(out.r.text, /current, verified apply receipt/); assert.doesNotMatch(out.r.text, /Prior source/);

  reset(); doc.generation = 3; doc.committedGeneration = 3; doc.path = 'C:/paint/car.psd';
  const oldCanvas = w.paintCanvas; await w.makeAppliedReceipt('Roof: old render'); w.paintCanvas = { width: 64, height: 64 }; vm.runInContext('paintCanvas=window.paintCanvas', w);
  out = await route('Explain my last change'); assert.match(out.r.text, /current, verified apply receipt/); assert.notEqual(w.paintCanvas, oldCanvas);
  w.paintCanvas = oldCanvas; vm.runInContext('paintCanvas=window.paintCanvas', w);

  reset(); doc.zoneRevision = 'zone-revision-1'; await w.makeAppliedReceipt('Roof: colour #d40000'); doc.zoneRevision = 'zone-revision-2';
  out = await route('What did you change?'); assert.match(out.r.text, /current, verified apply receipt/); assert.doesNotMatch(out.r.text, /Roof: colour/);

  reset(); await w.makeAppliedReceipt('Roof: colour #d40000');
  const before = w.finished.length, priorQueueCount = w.queueMutations; w.routeSend('Make the roof blue and explain my last change');
  assert.equal(w.finished.length, before, 'mixed action/explanation does not get consumed by receipt path');
  assert.deepEqual(w.sentAsk, ['Make the roof blue and explain my last change']);
  assert.equal(w.queueMutations, priorQueueCount); assert.equal(w.providerCalls, 0);

  reset(); w.routeSend('How do I change roof colour?');
  assert.equal(w.finished.length, 1); assert.equal(w.finished[0].r.text, 'Ordinary guidance remains on self-help.');
  assert.equal(w.finished[0].r.queue.length, 0); assert.equal(w.sentAsk.length, 0);

  console.log('PASS W77 offline receipt route: 6 positive/5 negative phrase checks, applied/partial/failed/undone/superseded/draft/stale/source-replaced/manual-revision receipts, mixed-action and guidance controls.');
})().catch(e => { console.error(e.stack || e); process.exitCode = 1; });
