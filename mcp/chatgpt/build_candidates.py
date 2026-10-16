"""Create reviewable shared-file candidates; never writes Claude's sources."""
import difflib
import hashlib
import json
import sys
from pathlib import Path
from relay_scope_edits import backend_edits, frontend_edits, index_edits
from report_scope_edits import edits as report_edits
from mcp_measurement_edits import edits as mcp_measurement_edits
from native_region_colour_edits import canvas_edits as native_region_canvas_edits
from owner_promotions import filter_edits as promotion_edits, filter_inventory_edits, function_text

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent / 'candidates'
DEST.mkdir(exist_ok=True)
records = []
prepared = []
adoption_audit = []


def candidate(relative, edits):
    source = ROOT / relative
    source_bytes = source.read_bytes()
    original = source_bytes.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
    text = original
    # Claude integrated the first offline candidates as CX1 during this session.
    # Preserve that implementation (including its kill switch) instead of reverting it.
    integrated = (relative == 'js/spb-offline-answer.js' and
                  "question: S.text || '', fromAnswer: true" in original and 'CX1' in original)
    integrated = integrated or (relative == 'js/spb-offline-builder.js' and
                  all(mark in original for mark in ('var cx1 = !!(x.fromAnswer && !W.SPB_CX1_OFF)',
                      'if (cx1) st.what = null', 'connect-helper', 'choose WHAT to change before running')))
    if integrated:
        edits = []
    # Claude promoted the first conversation/routing pass as CX2. Preserve the
    # production implementation and kill switches; stage only the new car lookup.
    if 'CX2' in original and relative in ('server_routes/mcp_bridge_routes.py', 'js/spb-pro-ai.js', 'js/spb-ai-connect.js'):
        markers = {
            'server_routes/mcp_bridge_routes.py': ('def mcp_conversation()', 'def _listening(helper=None)', '_PROVIDER_CLIENTS'),
            'js/spb-pro-ai.js': ('var observationOnly =', 'var lease = observationOnly ? null'),
            'js/spb-ai-connect.js': ('function listeningFor(j)', 'requestedHelper', 'Connect Claude or ChatGPT instead'),
        }
        if all(mark in original for mark in markers[relative]):
            edits, integrated = [], True
    if relative == 'mcp/server/index.js' and 'const CX2 = ' in original:
        edits = [
            ("require('./assistant-context.cjs')", "require('../chatgpt/assistant-context.cjs')", 1),
            ("const READ_ONLY = new Set(['spb_assistant_context'", "const CAR_KNOWLEDGE = require('../chatgpt/car-knowledge/lookup.cjs');\nconst READ_ONLY = new Set(['spb_car_knowledge', 'spb_assistant_context'", 1),
            ('[ASSISTANT_CONTEXT.TOOL] : [], GENERATED)', '[ASSISTANT_CONTEXT.TOOL] : [], [CAR_KNOWLEDGE.TOOL], GENERATED)', 1),
            ('async function callTool(name, args) {', """async function callTool(name, args) {
  if (name === 'spb_car_knowledge') {
    try { return {content:[{type:'text',text:JSON.stringify(CAR_KNOWLEDGE.lookup(args || {}))}]}; }
    catch(e) { return {isError:true,content:[{type:'text',text:String(e.message||e)}]}; }
  }""", 1),
        ]
    if relative == 'js/spb-offline-answer.js':
        route_anchor = '    function route(text, env) {'
        if 'SPB_W17D-BEGIN' in original and '    function routeCx3Base(text, env) {' not in original:
            route_anchor += '\n        if (W17_DEPTH || w17Off()) return route15(text, env);'
        edits = edits + [
            (route_anchor, route_anchor.replace('    function route(text, env) {', '    function route(text, env) {\n        if (W.SpbConversationScope) W.SpbConversationScope.observe();\n        var layerChoice = W.SpbLayerTargets && W.SpbLayerTargets.choose(text, (env||{}).chips, (env||{}).layers);\n        if (layerChoice) return route(layerChoice, Object.assign({}, env, {chips:null}));'), 1),
            ('        if (W.SpbConversationScope) W.SpbConversationScope.observe();', '        if (W.SpbConversationScope) W.SpbConversationScope.observe();\n        var advice = W.SpbDesignIntent && W.SpbDesignIntent.answer(text); if (advice) return advice;', 1),
            ('        var advice = W.SpbDesignIntent && W.SpbDesignIntent.answer(text); if (advice) return advice;', '''        var advice = W.SpbDesignIntent && W.SpbDesignIntent.answer(text); if (advice) {
            var factualRead = !W.SPB_CARKB_OFF && W.SpbCarReferenceAnswer && W.SpbCarReferenceAnswer.readOnlyQuestion(text);
            if (factualRead) return factualRead;
            return advice;
        }
        var protectedLayerPlan = W.SpbPreservedColours && W.SpbProEdit ? W.SpbPreservedColours.layerPlan(text, env || {}, W.SpbProEdit.plan, function(s){return String(s||'').toLowerCase().replace(/\\s+/g,' ').trim();}) : null;
        if (protectedLayerPlan) {
            if (protectedLayerPlan.prohibited_edit) return asked('protected-layer-scope', protectedLayerPlan.text, []);
            var protectedSteps = B().fromText(text, env).steps;
            if (!protectedSteps.length) return asked('protected-layer-scope', 'Read the current layers and specify the layer change again.', []);
            var protectedResult = stepsResult(protectedSteps, {via:'protected-layer-scope'}); protectedResult.kept9 = protectedLayerPlan.preserved_layers; return protectedResult;
        }''', 1),
            ('    function build(list, screens) {', '    function build(list, screens) {\n        if (W.SpbCarReferenceAnswer) W.SpbCarReferenceAnswer.index(list);', 1),
            ('protectedResult.kept9 = protectedLayerPlan.preserved_layers; return protectedResult;\n        }', '''protectedResult.kept9 = protectedLayerPlan.preserved_layers; return protectedResult;
        }
        if (W.SpbLayerTargets && W.SpbProEdit && /^(?:please\\s+)?(?:make|turn|paint|recolou?r|change|apply)\\b/i.test(String(text||'').trim())) {
            var exactScope = W.SpbProEdit.layerScope(text, (env||{}).layers);
            if (exactScope && exactScope.ask) return asked('exact-layer-scope', exactScope.ask.text, exactScope.ask.chips || []);
            if (exactScope && exactScope.layers) {
                var exactPlan = W.SpbProEdit.plan(text, env||{});
                if (exactPlan.kind === 'ask') return asked('exact-layer-scope', exactPlan.text || 'Choose the layer and change.', []);
                if (exactPlan.kind === 'ops' && exactPlan.ops.length === 1 && exactPlan.ops[0].target.layers) {
                    var exactSteps = B().fromText(text, env).steps;
                    if (!(exactPlan.unknown || []).length && exactSteps.length && exactSteps.every(function(s){return !s.unknown && !s.ask;})) {
                        var exactResult = stepsResult(exactSteps, {via:'exact-layer-scope'});
                        exactResult.preserved_colour_words = (exactPlan.preserved_colour_words || []).slice();
                        return exactResult;
                    }
                }
            }
        }''', 1),
            ('    function answerOf(hit, text) {', '    function answerOf(hit, text) {\n        if (!W.SPB_CARKB_OFF && W.SpbCarReferenceAnswer && hit.doc.a.car_reference) { var carAnswer = W.SpbCarReferenceAnswer.answer(hit.doc.a, text); if (carAnswer) return carAnswer; }', 1),
            ('        var out = routeW14(text, env);', "        var carRef = !W.SPB_CARKB_OFF && W.SpbCarReferenceAnswer && kind(text) === 'question' ? W.SpbCarReferenceAnswer.contextQuestion(text) : null;\n        var out = carRef || routeW14(text, env);", 1),
            ("        var out = carRef || routeW14(text, env);", "        var remembered = W.SpbDesignBrief && kind(text) === 'question' ? W.SpbDesignBrief.recall(text) : null;\n        var out = remembered ? {cls:'ANSWER',hits:[{id:'assistant.saved_design_brief',title:'Saved design discussion',score:0}],answer:{id:'assistant.saved_design_brief',project_discussion:true,title:'Saved design discussion',text:remembered.text,summary:remembered.text,how:[],actions:[],related:[],faq:null,shot:null}} : (carRef || routeW14(text, env));", 1),
            ("        h += '<div class=\"spb-ob-row\"><button type=\"button\" class=\"spb-ob-link\" data-ob=\"aread\"", "        if (!A.project_discussion && !A.live_context && A.id !== 'cars.reading_sheet') h += '<div class=\"spb-ob-row\"><button type=\"button\" class=\"spb-ob-link\" data-ob=\"aread\"", 1),
            ("        if (A.how && A.how.length", "        if (!W.SPB_CARKB_OFF && W.SpbCarReferenceAnswer && A.sources) h += W.SpbCarReferenceAnswer.linksHtml(A.sources);\n        if (A.how && A.how.length", 1),
        ]
    if relative == 'js/spb-offline-answer.js':
        edits += [(' : (carRef || routeW14(text, env));', ' : ((W.SpbEditorCapabilities && kind(text) === "question" ? W.SpbEditorCapabilities.answer(text) : null) || carRef || routeW14(text, env));', 1)]
    if relative == 'js/spb-offline-builder.js':
        edits = edits + [
            ('var s3r = S.ran ? s3Ran() : null, s3back =', 'var s3r = S.ran && S.ran.undone ? {verdict:"undo-ask",line:"Undone: the preview is back to its state before this Run."} : (S.ran ? s3Ran() : null), s3back =', 1),
            ('data-ob="undo" title="Put the car back', 'data-ob="undo"\' + (s3back ? \' disabled\' : \'\') + \' title="Put the car back', 1),
            ("else if (a === 'undo') { var B = bridge();", "else if (a === 'undo') { var lastReport = s3Ran(); if (S.ran && (S.ran.undone || (lastReport && /^(?:undo-ask|nothing-applied)$/.test(lastReport.verdict)))) return; var B = bridge();", 1),
            ('    W.SpbOfflineBuilder = {', '''    function undoChanged(entry) {
        var rep = s3Ran();
        if (!S.ran || !entry || !rep || rep.eid !== entry.id) return false;
        S.ran.undone = true; draw(); return true;
    }
    W.SpbOfflineBuilder = { _undoChanged: undoChanged,''', 1),
            ('        if (!ed) return { steps: steps };', '        if (!ed) return { steps: steps };\n        if (ed.prohibited_edit || (ed.protected_parts && ed.protected_parts.length)) return {steps:[],blocked:ed.text || "Clarify which area can change first."};', 1),
            ('        if (!r.steps.length) r = fromFlags(text, env);', '        if (r.blocked) { r.ed = ed; return r; }\n        if (!r.steps.length) r = fromFlags(text, env);', 1),
            ('function showAnswer(r, text) { S.s5frame = null;', "function showAnswer(r, text) { if (r && r.via === 'design-advice') { S.steps = []; S.ran = null; } S.s5frame = null;", 1),
            ("        else h += '<div class=\"spb-ob-mini\">", "        else if (!(S.answer && S.answer.via === 'design-advice')) h += '<div class=\"spb-ob-mini\">", 1),
            ('    function resumeAfterLayout(call) {', '    function resumeAfterLayout(call) {\n        var documentStamp = W.SpbConversationScope ? W.SpbConversationScope.stamp() : null;\n        function scopeCurrent() { return documentStamp === null || W.SpbConversationScope.current(documentStamp); }', 1),
            ('            if (++n > 150) return; var yes = null;', '            if (!scopeCurrent() || ++n > 150) return; var yes = null;', 1),
            ('setTimeout(function () { try { call(); } catch (e) {} }, 900);', 'setTimeout(function () { if (!scopeCurrent()) return; try { call(); } catch (e) {} }, 900);', 1),
            ('    W.SpbOfflineBuilder = {', '''    function sourceChanged() {
        S = { steps: [], text: '', flags: [], edit: null, term: null, termPin: false, msg: '', ran: null, typed: null, box: null, search: {}, mini: true, liveText: '' };
        if (HAS_DOM) draw();
    }
    W.SpbOfflineBuilder = { _sourceChanged: sourceChanged,''', 1),
        ]
    if relative == 'js/spb-pro-ai.js':
        edits = edits + [
            ('layers: layersInfo(), car: car, memory:', 'layers: layersInfo(), editor_capabilities: window.SpbEditorCapabilities ? SpbEditorCapabilities.read() : undefined, car: car, memory:', 1),
            ('out.push({ name: l.name, role: (CAR ?', 'out.push({ id: l.id, name: l.name, role: (CAR ?', 1),
            ('return { name: l.name, role: l.role, hidden: l.hidden || undefined };', 'return { id: l.id, name: l.name, group: l.group, role: l.role, hidden: l.hidden || undefined };', 1),
            ("var live = (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : [];", "var live = (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : [];\n        if (window.SpbLayerTargets && query.indexOf('/') !== -1) { var grouped = SpbLayerTargets.resolve(query, live); return grouped.ok ? {layer:grouped.row} : {error:grouped.reason}; }", 1),
            ('    function doUndo(entry) {', '    function doUndo(entry) {\n        var undoStamp = window.SpbConversationScope ? SpbConversationScope.stamp() : null;', 1),
            ("undone_by_button: true }, comment: 'undone right after the report'", "undone_by_button: !entry.undoneByCheck }, comment: entry.undoneByCheck ? 'rendered verifier took it back' : 'undone right after the report'", 1),
            ("RECENT.push('(buyer undid the last AI change)');", "RECENT.push(entry.undoneByCheck ? '(rendered verifier took back the last AI change)' : '(buyer undid the last AI change)'); try { if (window.SpbOfflineBuilder && SpbOfflineBuilder._undoChanged) SpbOfflineBuilder._undoChanged(entry); } catch (eOBU) {}", 1),
            ('Z.whenSettled(60000).then(function () { rshotGrab(); });', 'Z.whenSettled(60000).then(function () { if (undoStamp === null || SpbConversationScope.current(undoStamp)) rshotGrab(); });', 1),
            ('if (_advUsed && entry.request === _advUsed.req)', 'if (!entry.undoneByCheck && _advUsed && entry.request === _advUsed.req)', 1),
            ("var observationOnly = !window.SPB_CX2_OFF && (tool === 'status' || tool === 'get_state' || tool === 'zones' || tool === 'list_tools');", "var observationOnly = !window.SPB_CX2_OFF && /^(?:status|get_state|zones|list_tools|encyclopedia|get_car_map|preview|design_recipes|suggest_finishes|find_finishes|finish_details|compare_finishes|browse_catalog|find_patterns|find_spec_patterns|get_help|check_setup|describe_paint|look_at_paint|check)$/.test(tool);", 1),
            ('    function state() {', '    function state() {\n        if (window.SpbConversationScope) SpbConversationScope.observe();', 1),
            ('    function makeTools(queue, sig, mode, mcpContext) {', '    function makeTools(queue, sig, mode, mcpContext) {\n        var documentStamp = window.SpbConversationScope ? SpbConversationScope.stamp() : null;\n        if (documentStamp !== null && queue) queue._documentStamp = documentStamp;', 1),
            ('        return TOOLS;', '''        if (documentStamp !== null) TOOLS.forEach(function (t) { var h = t.handler; t.handler = function (a) {
            if (!SpbConversationScope.current(documentStamp)) return {error:'The open paint changed. Read the current paint and send a fresh request.'};
            return h(a);
        }; });
        return TOOLS;''', 1),
            ('    function applyQueue(queue, label, noUndo, elementIdentity, mcpContext) {', '''    function applyQueue(queue, label, noUndo, elementIdentity, mcpContext) {
        if (window.SpbConversationScope && queue && queue._documentStamp != null && !SpbConversationScope.current(queue._documentStamp)) return {results:[],lines:[],failed:['The paint changed; the previous document queue was not applied.'],layerUndo:0,maskUndo:[]};''', 1),
            ('    function ask(text, o) {', '''    function ask(text, o) {
        if (window.SpbConversationScope) SpbConversationScope.observe();
        o = Object.assign({}, o || {});
        o.documentStamp = window.SpbConversationScope ? SpbConversationScope.stamp() : null;
        if (o.documentStamp !== null && !SpbConversationScope.current(o.documentStamp)) return Promise.resolve({error:{message:'The conversation could not reset for this paint. Reopen the editor before continuing.'}});
        return Promise.resolve(askForDocument(text, o)).then(function (r) {
            if (o.documentStamp !== null && !SpbConversationScope.current(o.documentStamp)) { _busy = false; return {documentStamp:o.documentStamp,error:{message:'The paint changed while I was working. Please send your request again.'},queue:[]}; }
            if (r && o.documentStamp !== null) r.documentStamp = o.documentStamp;
            return r;
        });
    }
    function askForDocument(text, o) {''', 1),
            ('    function askCore(text, o) {', '''    function askCore(text, o) {
        if (window.SpbConversationScope && o && o.documentStamp != null && !SpbConversationScope.current(o.documentStamp)) { _busy = false; return Promise.resolve({error:{message:'The paint changed before the request started.'}}); }''', 1),
            ('            if (!r.error) { HIST.push', '            if (!r.error && !(window.SpbConversationScope && o && o.documentStamp != null && !SpbConversationScope.current(o.documentStamp))) { HIST.push', 1),
            ('    function runTurn2(text, o) {', '''    function runTurn2(text, o) {
        if (window.SpbConversationScope && o && o.documentStamp != null && !SpbConversationScope.current(o.documentStamp)) { _busy = false; _ctl = null; return Promise.resolve({error:{message:'The paint changed before planning.'}}); }''', 1),
            ('    function finishCore(r, text, kind, entryOpts) {', '''    function finishCore(r, text, kind, entryOpts) {
        if (window.SpbConversationScope && r && r.documentStamp != null && !SpbConversationScope.current(r.documentStamp)) { _busy = false; _log.push({role:'note',text:'The paint changed while I was working. Please send your request again.'}); render(); return Promise.resolve(); }''', 1),
            ('    function testReset() {', '''    // Document isolation: preserve buyer notes and confirmed car-map knowledge.
    function sourceChanged() {
        _cancelOpts = true; try { if (_ctl) _ctl.abort(); } catch (e) {}
        HIST.length = 0; RECENT.length = 0; _log = []; _last = null; _offlineLast = null;
        _advLast = null; _advRejected = []; _advUsed = null; _advDislikes = [];
        _r14 = null; _objAsk = null; _objAsks = {}; _cmpAsk = null; _pendingCard = null;
        _absent = {}; _skipParts = false; _noCheck = false; _specOnlyReq = false; _beforeImg = null; _reqText = '';
        _editReg = {}; _editRegSig = null; _editRegPendingBefore = {}; _elemNone = {}; _elemRunIdentity = null;
        _orig = null; _activeId = null; _rshots = []; _gen++; _snapGen = _gen;
        _ftLastScope = null; _visHiddenOk = false;
        window.__spbFrameHandoff = null;
        if (_panel) render();
    }
    function testReset() {''', 1),
            ('window.spbProAI = {', 'window.spbProAI = { _sourceChanged: sourceChanged,', 1),
            ("        if (window.SpbAiConnect) h += SpbAiConnect.cardHtml(_log.length > 0);", """        if (window.SpbAiConnect) h += SpbAiConnect.cardHtml(_log.length > 0);
        if (window.SpbDesignBrief && SpbDesignBrief.view().available) h += '<div class="spb-pai-note">This project includes a saved design discussion. <button type="button" class="spb-pai-act" data-act="recallbrief">Recall saved discussion</button> <button type="button" class="spb-pai-act" data-act="forgetbrief">Forget saved discussion</button></div>';""", 1),
            ("            else if (act === 'forgetmem')", "            else if (act === 'recallbrief') { var briefQuestion = 'What did we discuss in my saved design brief?'; if (window.SpbOfflineBuilder) SpbOfflineBuilder.markTyped(briefQuestion, 'saved-discussion'); send(briefQuestion); }\n            else if (act === 'forgetbrief') { if (window.SpbDesignBrief) SpbDesignBrief.forget(); _log.push({role:'note',text:'Forgot the discussion attached to this open project for future saves. Existing saved project files are unchanged.'}); render(); }\n            else if (act === 'forgetmem')", 1),
            ('return { zones: Z.zonesForModel(), selected_zone:', "return { design_options: window.SpbDesignIntent && window.SpbOfflineBuilder ? SpbDesignIntent.discussion(SpbOfflineBuilder.state().answer) : undefined, saved_design_brief: window.SpbDesignBrief ? SpbDesignBrief.view() : undefined, template_identity: window.SpbTemplateIdentity ? SpbTemplateIdentity.read() : undefined, zones: Z.zonesForModel(), selected_zone:", 1),
            ("result: { app: 'Shokker Paint Booth', zones:", "result: { app: 'Shokker Paint Booth', template_identity: window.SpbTemplateIdentity ? SpbTemplateIdentity.read() : undefined, zones:", 1),
            ('_push: function (e) {', '_push: function (e) { if (window.SpbDesignBrief) SpbDesignBrief.observe();', 1),
            ("else if (act === 'clear') { _log = [];", "else if (act === 'clear') { if (window.SpbOfflineBuilder && SpbOfflineBuilder._sourceChanged) SpbOfflineBuilder._sourceChanged(); _log = [];", 1),
            ('function memClear() { memSave({ buyer: [], cars: {} }); }', 'function memClear() { memSave({ buyer: [], cars: {} }); if (window.SpbDesignBrief) SpbDesignBrief.forget(); }', 1),
            ("            if (L) return '<div class=\"spb-pai-carline ok\">🏁 I recognise your car: <b>' + esc(L.name) + '</b>. I know where its hood, roof, sides and bumpers are.</div>';", "            var evidence = !window.SPB_CARKB_OFF && window.SpbCarReferenceAnswer && SpbCarReferenceAnswer.welcome ? SpbCarReferenceAnswer.welcome() : null;\n            if (evidence) return '<div class=\"spb-pai-carline\">🏁 ' + esc(evidence.text) + '</div>';\n            if (L) return '<div class=\"spb-pai-carline\">🏁 Suggested layout: <b>' + esc(L.name) + '</b>. Confirm the car and target area before placing changes.</div>';", 1),
            ("text: r.text || '', enc: r.enc || null, lines: []", "text: r.text || '', design_proposals: window.SpbDesignIntent ? SpbDesignIntent.discussion({answer:{design_proposals:r.design_proposals}}) : null, enc: r.enc || null, lines: []", 1),
            ('    function send(text, o) {', '''    function send(text, o) {
        if (window.SpbConversationScope) SpbConversationScope.observe();
        if (window.SpbDesignBrief) SpbDesignBrief.observe();
        // Advice is handled before option-pick / complaint / edit parsers.
        var adviceBuilder = window.SpbOfflineBuilder;
        var designAdvice = (!_busy && !(window.SpbAiConnect && SpbAiConnect.relaying()) && adviceBuilder && adviceBuilder.offlineMode() && window.SpbDesignIntent) ? (SpbDesignIntent.answer(text, adviceBuilder.state && adviceBuilder.state().answer) || (window.SpbDesignBrief && SpbDesignBrief.explain && SpbDesignBrief.explain(text))) : null;
        if (designAdvice && !window.SPB_CARKB_OFF && window.SpbCarReferenceAnswer && SpbCarReferenceAnswer.isReferenceQuestion(text)) designAdvice = null;
        if (designAdvice) {
            text = String(text || '').trim(); _log.push({role:'user',text:text});
            var adviceInput = _panel && _panel.querySelector('.spb-pai-input'); if (adviceInput) adviceInput.value = '';
            adviceBuilder.showAnswer(designAdvice, text);
            return finish({offline:true,design_proposals:SpbDesignIntent.discussion(designAdvice),text:'The '+(designAdvice.answer.title || 'Design advice')+' card below discusses your colours and finishes. Nothing has been changed or queued.',queue:[],calls:0,usage:{cost:0},model:'built-in',tools:[],builder:false,howto:false,asked:{options:[]},metaText:'✦ built-in guidance · no AI used'}, text, 'ask');
        }
        // CAR-KNOWLEDGE: a cold local index is loading, not evidence that an answer does not exist.
        var readyWait = (!window.SPB_CARKB_OFF && !_busy && String(text || '').trim() && !(window.SpbAiConnect && SpbAiConnect.relaying()) && window.SpbOfflineReady) ? SpbOfflineReady.wait(window.SpbOfflineAnswer) : null;
        if (readyWait) {
            var readyIdentity = elementRunIdentity(), readyQuestion = window.SpbOfflineAnswer && SpbOfflineAnswer.kind && SpbOfflineAnswer.kind(text) === 'question'; _cancelOpts = false; _busy = true; _progress = 'Loading paint knowledge…'; render();
            return readyWait.then(function () {
                _busy = false; _progress = '';
                if (_cancelOpts) { render(); return; }
                if ((window.SpbAiConnect && SpbAiConnect.relaying()) || (!readyQuestion && !elementRunCurrent(readyIdentity))) { _log.push({role:'note',text:'The helper or open paint changed while the reference loaded. Please send your request again.'}); render(); return; }
                return send(text, o);
            }, function (e) { _busy = false; _progress = ''; if (!_cancelOpts) _log.push({role:'note',text:e.message}); render(); });
        }''', 1)]
    if relative == 'server_routes/mcp_bridge_routes.py':
        edits += backend_edits()
    if relative == 'js/spb-ai-connect.js':
        edits += frontend_edits()
    if relative == 'mcp/server/index.js':
        edits += index_edits(original)
        old_geometry = 'The paint is ONE flat 2048x2048 sheet of the whole car cut open (two side panels, hood, roof, trunk, bumpers, spoiler). Place everything on NAMED PARTS (region {part:"left side"}), never on big grid boxes.'
        qualified_geometry = 'The paint is a 2D template sheet that may contain editable layers. Resolution, panel layout and available parts vary by the loaded document. Use exact current layer IDs for layer edits and only current verified named parts (region {part:"left side"}) for panel placement; never infer coordinates from a car name, catalog facts or big grid boxes.'
        oa3_geometry = 'The paint is ONE flat \' + (OA3 ? \'sheet (usually 2048x2048; the live size and which parts are verified come from spb_status)\' : \'2048x2048 sheet\') + \' of the whole car cut open (two side panels, hood, roof, trunk, bumpers, spoiler). Place everything on NAMED PARTS (region {part:"left side"}), never on big grid boxes.'
        # OA3 adopted a conditional live-size instruction. Preserve that owner's
        # kill switch while qualifying layered documents and geometry in the active branch.
        if oa3_geometry in original:
            edits += [(oa3_geometry, "' + (OA3 ? '" + qualified_geometry + "' : '" + old_geometry + "') + '", 1)]
        else:
            edits += [(old_geometry, qualified_geometry, 1)]
    edits, promoted = promotion_edits(relative, original, edits)
    integrated = integrated or promoted
    for before, after, count in edits:
        # Owner now stashes Undo before clear. Preserve it alongside the
        # existing builder-choice reset rather than rebuilding an old handler.
        if relative == 'js/spb-pro-ai.js' and before.startswith("else if (act === 'clear') {") and "else if (act === 'clear') { stashUndo(); _log = [];" in text:
            before = before.replace("else if (act === 'clear') {", "else if (act === 'clear') { stashUndo();")
            after = after.replace("else if (act === 'clear') {", "else if (act === 'clear') { stashUndo();")
        # Oct10: Claude adopted additional reviewed native-colour hooks.
        # Preserve exact already-installed transformations; never accept a
        # merely similar replacement or an empty deletion as adoption proof.
        if after and text.count(after) == count:
            continue
        if relative == 'js/spb-pro-ai.js' and before == "RECENT.push('(buyer undid the last AI change)');" and text.count('try { if (!window.SPB_CX3_OFF && window.SpbOfflineBuilder && SpbOfflineBuilder._undoChanged) SpbOfflineBuilder._undoChanged(entry); } catch (eOBU) {}') == 1:
            # Preserve the already-installed, kill-switched notification once.
            after = after.split(' try {')[0]
            # W27 adds an independent kit Undo. Scope this receipt correction
            # to the existing general Undo notification and leave kit ownership alone.
            suffix = ' try { if (!window.SPB_CX3_OFF && window.SpbOfflineBuilder && SpbOfflineBuilder._undoChanged)'
            before += suffix
            after += suffix
        if relative == 'js/spb-pro-ai.js' and before == 'out.push({ name: l.name, role: (CAR ?' and text.count('out.push({ id: l.id, colour_overlay: window.SpbNativeLayerColour ? SpbNativeLayerColour.overlay(l) : undefined, name: l.name, role: (CAR ?') == 1:
            continue
        if relative == 'js/spb-offline-answer.js' and before.startswith('        h += \'<div class="spb-ob-row"><button type="button" class="spb-ob-link" data-ob="aread"') and text.count('if (W.SPB_CX3_OFF || !(A.live_context || A.reference_context || A.project_discussion)) h +=') == 1:
            continue  # Owner live-answer article guard includes the broader reference context.
        if relative == 'js/spb-offline-builder.js':
            if before == '    W.SpbOfflineBuilder = {' and after.startswith('    function sourceChanged() {') and function_text(text, 'sourceChanged') == function_text(after, 'sourceChanged') and '_sourceChanged: sourceChanged' in text:
                continue
            if before == '    W.SpbOfflineBuilder = {' and after.startswith('    function undoChanged(entry) {') and '_undoChanged: undoChanged' in text and 'if (!S.ran || !entry || (S.ran.eid != null ? S.ran.eid !== entry.id : (!rep || rep.eid !== entry.id))) return false;' in function_text(text, 'undoChanged'):
                continue
            if before == 'function showAnswer(r, text) { S.s5frame = null;' and text.count("function showAnswer(r, text) { if (!W.SPB_CX3_OFF && r && (r.via === 'design-advice' || (r.answer && (r.answer.id === 'assistant.live_editor_capabilities' || r.answer.id === 'assistant.template_layers' || r.answer.id === 'assistant.layer_pixels')))) { S.steps = []; S.ran = null; } S.s5frame = null;") == 1:
                continue
            if before == 'data-ob="undo" title="Put the car back' and text.count('data-ob="undo"\' + (s3back || S.ran.noChange ? \' disabled\' : \'\') + \' title="Put the car back') == 1:
                continue  # Stronger owner no-change guard.
            if before == "else if (a === 'undo') { var B = bridge();" and text.count("else if (a === 'undo') { if (!S.ran || S.ran.noChange || S.ran.undone || S.ran.eid == null) return; var lastReport = s3Ran();") == 1:
                continue
        actual = text.count(before)
        if actual != count:
            raise RuntimeError(f'{relative}: expected {count} matches, found {actual}: {before[:90]!r}')
        text = text.replace(before, after)
    destination = DEST / source.name
    patch = ''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
                                        fromfile='a/' + relative, tofile='b/' + relative))
    prepared.append((destination, text, patch))
    records.append({'source': relative, 'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
                    'candidate_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'already_integrated': integrated})


helpers = '''# CHATGPT-SESSION 2026-10-09: provider-tagged messages cannot cross assistants.
_PROVIDER_WAITS = {}
_PROVIDER_LAST = {}
_PROVIDER_CLIENTS = {}


def _provider(client):
    name = str(client or '').lower()
    if name.startswith(('codex', 'chatgpt', 'openai')):
        return 'chatgpt'
    if name.startswith(('claude', 'local-agent-mode')):
        return 'claude'
    return 'unknown'


def _matches(message, helper):
    return not message.get('helper') or message['helper'] == helper


def _client_for(helper):
    return _PROVIDER_CLIENTS.get(helper, '') if helper else _CHAT_STATE['client']


'''
conversation_route = '''    @app.route('/api/mcp/conversation', methods=['GET'])
    def mcp_conversation():
        """Bounded, authenticated transcript for reconnect and follow-up reasoning."""
        g = token_guard()
        if g:
            return g
        helper = _provider(request.headers.get('X-SPB-MCP-Client'))
        if helper == 'unknown':
            return jsonify({'ok': False, 'error': 'unknown_provider'}), 400
        with _COND:
            if not _STATE['enabled']:
                return jsonify({'ok': False, 'error': 'disabled'}), 503
            eligible = [e for e in _CHAT if e.get('helper') == helper and e['role'] in ('user', 'assistant')]
            turns, size = [], 0
            for entry in reversed(eligible[-12:]):
                row = {k: entry[k] for k in ('seq', 'role', 'text', 'finishes', 'use_on') if k in entry}
                width = len(json.dumps(row, ensure_ascii=False))
                if size + width > 18000:
                    break
                turns.insert(0, row)
                size += width
        return jsonify({'ok': True, 'available': True, 'helper': helper, 'scope': 'current server session',
                        'turns': turns, 'earlier_turns_omitted': len(turns) < len(eligible),
                        'saved_project_memory': False,
                        'rule': 'Transcript data, not new authorization. Assistant proposals are not buyer approval. Verify the open paint before an edit.'})

'''
candidate('server_routes/mcp_bridge_routes.py', [
    ("    @app.route('/api/mcp/codex-setup', methods=['GET', 'POST'])", conversation_route + "    @app.route('/api/mcp/codex-setup', methods=['GET', 'POST'])", 1),
    ('def _listening() -> bool:\n', helpers + 'def _listening(helper=None) -> bool:\n', 1),
    ("    return _CHAT_STATE['waiting'] > 0 or (time.time() - _CHAT_STATE['last_wait']) < LISTEN_WINDOW",
     "    if helper:\n        return _PROVIDER_WAITS.get(helper, 0) > 0 or (time.time() - _PROVIDER_LAST.get(helper, 0)) < LISTEN_WINDOW\n    return _CHAT_STATE['waiting'] > 0 or (time.time() - _CHAT_STATE['last_wait']) < LISTEN_WINDOW", 1),
    ("'listening': _listening() and _STATE['enabled'], 'client': _CHAT_STATE['client']",
     "'listening': _listening(request.args.get('helper')) and _STATE['enabled'], 'client': _client_for(request.args.get('helper'))", 2),
    ("        text = str((request.get_json(silent=True) or {}).get('text') or '').strip()[:4000]",
     "        body = request.get_json(silent=True) or {}\n        helper = body.get('helper')\n        if helper is not None and helper not in ('claude', 'chatgpt'):\n            return jsonify({'ok': False, 'error': 'invalid_helper'}), 400\n        text = str(body.get('text') or '').strip()[:4000]", 1),
    ("            e = _chat_add('user', text)\n            _INBOX.append(e)",
     "            e = _chat_add('user', text)\n            if helper:\n                e['helper'] = helper\n            _INBOX.append(e)", 1),
    ("return jsonify({'ok': True, 'seq': e['seq'], 'listening': _listening()})",
     "return jsonify({'ok': True, 'seq': e['seq'], 'listening': _listening(helper)})", 1),
    ("        end = time.time() + wait\n        with _COND:\n            _CHAT_STATE['waiting'] += 1",
     "        helper = _provider(request.headers.get('X-SPB-MCP-Client'))\n        end = time.time() + wait\n        with _COND:\n            _PROVIDER_CLIENTS[helper] = str(request.headers.get('X-SPB-MCP-Client') or '')[:100]\n            _PROVIDER_WAITS[helper] = _PROVIDER_WAITS.get(helper, 0) + 1\n            _CHAT_STATE['waiting'] += 1", 1),
    ("msgs = [m for m in _INFLIGHT if not m.get('again')]",
     "msgs = [m for m in _INFLIGHT if not m.get('again') and m.get('delivered_provider', helper) == helper and _matches(m, helper)]", 1),
    ("while not _INBOX and time.time() < end and _STATE['enabled']:",
     "while not any(_matches(m, helper) for m in _INBOX) and time.time() < end and _STATE['enabled']:", 1),
    ("                    while _INBOX:\n                        m = dict(_INBOX.popleft())\n                        msgs.append(m)\n                        _INFLIGHT.append(m)",
     "                    for pending in list(_INBOX):\n                        if not _STATE['enabled'] or not _matches(pending, helper):\n                            continue\n                        _INBOX.remove(pending)\n                        m = dict(pending, delivered_provider=helper)\n                        msgs.append(m)\n                        _INFLIGHT.append(m)", 1),
    ("                    _chat_add('status', 'working')", "                    _chat_add('status', 'working')['helper'] = helper", 1),
    ("                _CHAT_STATE['waiting'] -= 1", "                _PROVIDER_WAITS[helper] -= 1\n                _PROVIDER_LAST[helper] = time.time()\n                _CHAT_STATE['waiting'] -= 1", 1),
    ("        body = request.get_json(silent=True) or {}\n        text = str(body.get('text') or '').strip()",
     "        if not _STATE['enabled']:\n            return jsonify({'ok': False, 'error': 'disabled', 'message': 'The AI connection is off.'}), 503\n        helper = _provider(request.headers.get('X-SPB-MCP-Client'))\n        body = request.get_json(silent=True) or {}\n        text = str(body.get('text') or '').strip()", 1),
    ("            e = _chat_add('assistant', text)", "            e = _chat_add('assistant', text)\n            e['helper'] = helper", 1),
    ("            _INFLIGHT.clear()   # APPCHAT-REDELIVER: answered",
     "            _INFLIGHT[:] = [m for m in _INFLIGHT if m.get('delivered_provider') != helper]  # acknowledge only this assistant", 1),
    ("            out = [e for e in _CHAT if e['seq'] > after]",
     "            selected = request.args.get('helper')\n            out = [e for e in _CHAT if e['seq'] > after and (not selected or _matches(e, selected))]", 1),
])

candidate('mcp/server/index.js', [
    ("const VERSION = '1.4.0';", "const ASSISTANT_CONTEXT = require('../chatgpt/assistant-context.cjs');\nconst CAR_KNOWLEDGE = require('../chatgpt/car-knowledge/lookup.cjs');\nconst VERSION = '1.4.0';", 1),
    ("const READ_ONLY = new Set(['spb_wait_for_message'", "const READ_ONLY = new Set(['spb_car_knowledge', 'spb_assistant_context', 'spb_wait_for_message'", 1),
    ('STATIC_TOOLS.concat(GENERATED)', 'STATIC_TOOLS.concat([ASSISTANT_CONTEXT.TOOL, CAR_KNOWLEDGE.TOOL], GENERATED)', 1),
    ('const INSTRUCTIONS = [', "const INSTRUCTIONS = [\n  'DESIGN CONVERSATION: at the start, after reconnect, or when the buyer refers to earlier options, call spb_assistant_context with their question. include_paint=true reads the current car/layers/zones when discussing this paint. Use its recent transcript, live capabilities and relevant SPB guidance; preserve customer constraints and explain design tradeoffs. Proposals and hypothetical questions are not edit approval. Get an actual preview before visual judgments. Older help cards may describe outdated tool limitations: check current tool schemas and actual results.',", 1),
    ("'RENDER: when a buyer request is finished, call spb_render once", "'RENDER: after an authorized paint change is finished (never for advice, comparisons, or questions), call spb_render once", 1),
    ("async function callTool(name, args) {", """async function callTool(name, args) {
  if (name === 'spb_car_knowledge') {
    try { return {content:[{type:'text',text:JSON.stringify(CAR_KNOWLEDGE.lookup(args || {}))}]}; }
    catch(e) { return {isError:true,content:[{type:'text',text:String(e.message||e)}]}; }
  }
  if (name === 'spb_assistant_context') {
    try {
      const packet = await ASSISTANT_CONTEXT.build(args || {}, {
        tools: allTools, call: callTool,
        history: async () => {
          const r = await httpJson('GET', '/api/mcp/conversation', null, 10000);
          if (r.status >= 400 || !r.json || r.json.ok === false) return { isError: true, content: [{type:'text', text:'Recent chat unavailable: ' + friendly(r)}] };
          return r.json;
        }
      });
      return {content:[{type:'text',text:JSON.stringify(packet)}]};
    } catch(e) { return {isError:true,content:[{type:'text',text:String(e.message||e)}]}; }
  }""", 1),
])

# Status/state are observations. Keep busy/stale checks, but do not give an
# external assistant a two-minute editing lease just for reading the paint.
candidate('js/spb-pro-ai.js', [
    ("    function mcpCall(tool, args) {\n        var lease = window.SpbAiLease;",
     "    function mcpCall(tool, args) {\n        var observationOnly = tool === 'status' || tool === 'get_state';\n        var lease = observationOnly ? null : window.SpbAiLease;", 1),
])

candidate('js/spb-ai-connect.js', [
    ("if (m === 'offline') return hasLog ? '' : '<div class=\"spb-aic small\">Answering:",
     "if (m === 'offline') return '<div class=\"spb-aic small\">Answering:", 1),
    ("    function api(path, opt) { return fetch(BASE + path, opt).then(function (r) { return r.json(); }); }",
     "    function api(path, opt) {\n        if (/^\\/api\\/mcp\\/(status|chat)(\\?|$)/.test(path) && relaying()) path += (path.indexOf('?') < 0 ? '?' : '&') + 'helper=' + mode();\n        return fetch(BASE + path, opt).then(function (r) { return r.json(); });\n    }\n    function listeningFor(j) {\n        var client = String((j && j.client) || '').toLowerCase();\n        return !!(j && j.listening && (mode() === 'chatgpt' ? /^(codex|chatgpt|openai)/.test(client) : /^(claude|local-agent-mode)/.test(client)));\n    }", 1),
    ("S.listening = !!(s && s.listening)", "S.listening = listeningFor(s)", 1),
    ("            api('/api/mcp/chat?after=' + S.seq + '&wait=25').then(function (j) {",
     "            var requestedHelper = mode();\n            api('/api/mcp/chat?after=' + S.seq + '&wait=25').then(function (j) {\n                if (requestedHelper !== mode()) { loop(); return; }", 1),
    ("S.listening = !!j.listening; S.client", "S.listening = listeningFor(j); S.client", 1),
    ("body: JSON.stringify({ text: text })", "body: JSON.stringify({ text: text, helper: mode() })", 1),
])

# The answer-card action has a catalogue choice but no resolved target/constraint
# frame. Keep it incomplete instead of silently turning a hood question into a
# whole-car operation. This deliberately reuses the builder's existing Run gate.
candidate('js/spb-offline-answer.js', [
    ('Bb.takeAction({ do: x.do, id: x.id, label: x.label })',
     "Bb.takeAction({ do: x.do, id: x.id, label: x.label, question: S.text || '', fromAnswer: true })", 1),
])
candidate('js/spb-offline-builder.js', [
    ("if (!S.steps.length) st.what = { k: 'body' };",
     "if (x.fromAnswer) st.what = null; else if (!S.steps.length) st.what = { k: 'body' };", 1),
    ("st.note = 'From the encyclopedia: ' + (x.label || x.id) + '.';",
     "st.note = x.fromAnswer ? 'From your question: ' + (x.question || S.text) + ' — choose WHAT to change before running.' : 'From the encyclopedia: ' + (x.label || x.id) + '.';", 1),
    ("(configured() ? '<button type=\"button\" class=\"spb-pai-act\" data-ob=\"askai\"",
     "(W.SPB_NO_OPENROUTER !== false && W.SpbAiConnect ? '<button type=\"button\" class=\"spb-pai-act\" data-ob=\"connect-helper\">Connect Claude or ChatGPT</button>' : configured() ? '<button type=\"button\" class=\"spb-pai-act\" data-ob=\"askai\"", 1),
    ("        else if (a === 'askai') return askAI();",
     "        else if (a === 'connect-helper') { if (W.SpbAiConnect) W.SpbAiConnect.setMode(''); return; }\n        else if (a === 'askai') return askAI();", 1),
])
candidate('docs/ai_knowledge/04_limits_and_app_map.md', [
    ('- Delete zones, open or save files, import a paint/PSD, export or deploy to iRacing, change the car folder or user id, render the final full-resolution paint. It can tell the buyer exactly where to click.',
     '- Check the connected MCP tool list for current capabilities. When `spb_render` is available it can render and save through the app; report the actual saved-file/live-link result, never assume delivery. `spb_reset_zones` can reset zones according to its keep list and authorization contract. Opening/importing files, changing the car folder/user id or exporting a particular format still require an explicitly supported tool; otherwise explain the current manual controls.', 1),
    ('- Draw or paint by hand (brush, lasso, layer pixels), add text/logos, move or edit layer artwork. (Tools in the toolbar do those.)',
     '- Freehand brush/lasso/layer-pixel editing and arbitrary text/logo creation are not implied by the MCP connection. `spb_add_graphic`, when available, draws only its supported named graphic types on known parts. `spb_edit_layer` changes visibility, opacity and blend; it is not a general artwork editor. Use the actual tool schema or explain the relevant toolbar workflow.', 1),
])
candidate('docs/ai_knowledge/05_design_and_taste.md', [
    ('The paint is a flat texture: it cannot glow in the dark, cannot show text or pictures unless they already exist as layers, cannot change the car\'s shape, windows or wheels beyond what the sheet paints, and iRacing\'s lighting decides how chrome and flake look on track.',
     'The paint is a flat texture and can contain text or pictures. What the assistant can insert or edit depends on the connected tools: supported graphic types may be drawn, while arbitrary artwork/text requires an appropriate tool or a manual workflow. A paint file cannot create physical geometry or guaranteed emissive glow, cannot alter windows or wheels beyond their mapped surfaces, and iRacing\'s lighting decides how chrome and flake look on track.', 1),
])
candidate('paint-booth-3-canvas.js', [
    *native_region_canvas_edits((ROOT / 'paint-booth-3-canvas.js').read_text(encoding='utf-8')),
    ("    const _isHelperLayer = function (l) {\n        return /^\\s*(mask|wire)\\b/i.test(String(l.name || ''));\n    };", "    // SPB-93 private59910: red-only AI recolour painted157486 opaque Mask pixels.\n    // Visible guides own their displayed pixels too; hiding them invalidates the\n    // normal visibility cache and exposes the source underneath. Preserve the\n    // explicit brush excludeLayerId exception; never infer exclusion from a name.", 1),
    ('!!layer.img && !_isHelperLayer(layer) && !(excludeLayerId && layer.id === excludeLayerId);', '!!layer.img && !(excludeLayerId && layer.id === excludeLayerId);', 1),
    ('            const info = details || {};\n            return {\n                ok: !!ok,', '''            const info = details || {};
            if (ok && typeof window !== 'undefined' && window.SpbConversationScope) window.SpbConversationScope.sourceCommitted();
            if (ok && typeof window !== 'undefined' && window.SpbDesignBrief) window.SpbDesignBrief.sourceCommitted();
            if (ok && typeof window !== 'undefined' && window.SpbConversationScope && window.spbProAI) window.spbProAI.refresh();
            return {
                ok: !!ok,''', 1),
])
candidate('js/features/spb-projects.js', [
    ("return _fetchJson(API + '/save/commit/'", "return await _fetchJson(API + '/save/commit/'", 1),
    ('                sourceState: transaction.captureDocumentState(),', '                sourceState: transaction.captureDocumentState(),\n                templateReferenceState: window.SpbTemplateIdentity ? SpbTemplateIdentity.captureSession() : null,', 1),
    ('        return {\n            ok: errors.length === 0,\n            error: errors.join(\'; \'),', '        if (window.SpbTemplateIdentity) { if (!errors.length) SpbTemplateIdentity.restoreSession(snapshot.templateReferenceState); else SpbTemplateIdentity._sourceChanged(); }\n        return {\n            ok: errors.length === 0,\n            error: errors.join(\'; \'),', 1),
    ('        var zoneCount = ((remapped.config || {}).zones || []).length;', '        if (window.SpbTemplateIdentity) SpbTemplateIdentity.sourceVerified(project, out.sourceStatus);\n        var zoneCount = ((remapped.config || {}).zones || []).length;', 1),
    ("        var canvas = document.getElementById('paintCanvas');\n        return {\n            _spb_project: true,", "        var canvas = document.getElementById('paintCanvas');\n        var designProjectId = _newProjectId();\n        return {\n            _spb_project: true,", 1),
    ('            projectId: _newProjectId(),', '            projectId: designProjectId,\n            assistantBrief: window.SpbDesignBrief ? SpbDesignBrief.capture(designProjectId) : null,', 1),
    ('                sourceState: transaction.captureDocumentState(),', '                sourceState: transaction.captureDocumentState(),\n                designBriefState: window.SpbDesignBrief ? SpbDesignBrief.captureSession() : null,', 1),
    ('        return {\n            ok: errors.length === 0,\n            error: errors.join(\'; \'),', '        if (window.SpbDesignBrief) { if (!errors.length && snapshot.designBriefState) SpbDesignBrief.restoreSession(snapshot.designBriefState); else SpbDesignBrief.forget(); }\n        return {\n            ok: errors.length === 0,\n            error: errors.join(\'; \'),', 1),
    ('        var zoneCount = ((remapped.config || {}).zones || []).length;', "        var briefRestored = window.SpbDesignBrief ? SpbDesignBrief.restore(project.assistantBrief, project.projectId, !gate.legacyUnverified) : false;\n        var zoneCount = ((remapped.config || {}).zones || []).length;", 1),
    ("' zone(s), ' + layerCount + ' Layer state(s), source verified.' + matInfo + suffix,", "' zone(s), ' + layerCount + ' Layer state(s), source verified.' + (briefRestored ? ' Design discussion restored.' : '') + matInfo + suffix,", 1),
    ("' KB) — all live Layer pixels included');", "' KB) — all live Layer pixels included' + (payload.assistantBrief ? '; design discussion included' : ''));", 1),
])
candidate('server_routes/v5_entrypoint_security.py', [
    ('''            target = os.path.join(
                os.path.expanduser("~"),
                "Documents",
                "Shokker Paint Booth",
                "SPB Projects",
            )
            operation = "project-storage"''', '''            # Resolve the same directory as project_routes, including private test hosts.
            from server_routes.project_routes import _default_projects_dir
            target = _default_projects_dir()
            operation = "project-storage"''', 1),
])
candidate('js/spb-pbn.js', [
    ('var r = B.fromText(t, en), st = (r && r.steps) || [], ex = exceptOf(t);', 'var r = B.fromText(t, en), st = (r && r.steps) || [], ex = exceptOf(t);\n            if (r && r.blocked) { out = {blocked:r.blocked}; RDM[key] = out; return out; }', 1),
    ('        if (RDR) h +=', '        if (RDR && RDR.blocked) { CUR = null; d.innerHTML = h + \'<div class="spb-pbn-msg">\' + esc(RDR.blocked) + \'</div></div>\'; return; }\n        if (RDR) h +=', 1),
    ("        d.hidden = !!off;", "        if (W.SpbDesignIntent && W.SpbDesignIntent.classify(S.text).mode === 'advice') { CUR = null; off = true; }\n        d.hidden = !!off;", 1),
    ('        d.hidden = !!off;', '        var layerAsk = W.SpbLayerTargets && B && B.envNow ? W.SpbLayerTargets.scope(S.text, (B.envNow() || {}).layers) : null;\n        if (layerAsk && layerAsk.ask && layerAsk.ask.layer_target_question) { CUR = null; off = true; }\n        d.hidden = !!off;', 1),
    ('    W.SpbPbn = {', '''    function sourceChanged() {
        clearTimeout(S._dt); clearTimeout(S._rt);
        var open = S.open;
        S = { text: '', picks: [], open: open, listAll: false, sig: '', msg: '', routeOff: null };
        RDM = {}; RDN = 0; CUR = null;
        draw();
    }
    W.SpbPbn = { _sourceChanged: sourceChanged,''', 1),
])
candidate('js/spb-pro-edit.js', [
    ('    function layerScope(text, layers) {', '    function layerScope(text, layers) {\n        var qualified = window.SpbLayerTargets && SpbLayerTargets.scope(text, layers); if (qualified) return qualified;', 1),
    ('return { layers: [hit[0].name], word: hit[0].name, rest: rest };', '''var pickedLayer = window.SpbLayerTargets ? (hit.length === 1 ? SpbLayerTargets.select(hit[0], ls) : {ok:false,reason:'Several layers match. Choose the full group and layer.'}) : (hit.length === 1 ? {ok:true,selector:hit[0].name,label:hit[0].name} : {ok:false,reason:'Several layers match. Choose the full group and layer.'});
        if (!pickedLayer.ok) return {ask:{kind:'ask',text:pickedLayer.reason,chips:[]}};
        return { layers: [pickedLayer.selector], word: pickedLayer.label, rest: rest };''', 1),
    ('            (parts || [null]).forEach(function (pt) {', '''            if (region && region.layers && window.SpbLayerTargets) {
                var exactLayers = region.layers.map(function(ref){return SpbLayerTargets.resolve(ref, layers);});
                if (exactLayers.some(function(x){return !x.ok;})) { ask={text:'Choose the exact group and layer before applying this change.',chips:[]}; missing.push({why:'ambiguous-layer'}); return; }
                region.layers = exactLayers.map(function(x){return x.selector;});
            }
            (parts || [null]).forEach(function (pt) {''', 1),
    ('var sc = /\\blayer\\b/i.test(text) ? layerScope(text, env.layers) : null;', 'var protectedLayers = window.SpbPreservedColours ? SpbPreservedColours.layerPlan(raw0, env, plan, norm) : null;\n        if (protectedLayers) return protectedLayers;\n        var sc = layerScope(raw0, env.layers);', 1),
    ('var pl = planCore(sc ? sc.rest : text, sc ? Object.assign({}, env, { _layerScope: sc.layers }) : env);', 'var keptColours = window.SpbPreservedColours ? SpbPreservedColours.plan(sc ? sc.rest : raw0, env, planCore, parseClause, norm) : null;\n        var pl = keptColours || planCore(sc ? sc.rest : text, sc ? Object.assign({}, env, { _layerScope: sc.layers }) : env);', 1),
])
candidate('js/spb-pro-zone-kit.js', [
    ("try { var s = String(x).toLowerCase(); return _psdLayers.filter(function (l) { return l && l.img && (l.id === x || String(l.name).toLowerCase() === s); })[0] || _psdLayers.filter(function (l) { return l && l.img && String(l.name).toLowerCase().indexOf(s) !== -1; })[0] || null; } catch (e) { return null; }", "try { var rows = _psdLayers.filter(function(l){return l && l.img;}), s = String(x).toLowerCase(); var ids = rows.filter(function(l){return l.id != null && (l.id === x || (typeof x === 'string' && String(l.id) === x));}); if (ids.length) return ids.length === 1 ? ids[0] : null; if (window.SpbLayerTargets && s.indexOf('/') !== -1) { var grouped = SpbLayerTargets.resolve(x, rows); return grouped.ok ? grouped.row : null; } var named = rows.filter(function(l){return String(l.name).toLowerCase() === s;}); if (named.length) return named.length === 1 ? named[0] : null; var fuzzy = rows.filter(function(l){return String(l.name).toLowerCase().indexOf(s) !== -1;}); return fuzzy.length === 1 ? fuzzy[0] : null; } catch(e) { return null; }", 1),
])
candidate('js/spb-intent-report.js', report_edits((ROOT / 'js/spb-intent-report.js').read_text(encoding='utf-8')))
candidate('js/spb-mcp-frames.js', [
    ("line = line.replace(/\\s*Your [^.]*?(?:is|are) untouched\\./i, '');", "line = line.replace(/\\s*Your [^.]*?(?:is|are) untouched\\./i, '').replace(/\\s*The preview check detected small differences in protected artwork; preservation is unverified\\. Review the result or use Undo\\./i, '');", 1),
    ("' Only ' + m.decal_px + ' px at the edges of your numbers / logos changed.'", "' The preview check estimates ' + m.decal_px + ' px of differences in protected artwork; preservation is unverified. Review the result or use Undo.'", 1),
    ('scope: { parts: arr(rep.parts),', 'coverage: rep.coverage_cells ? {unit:rep.coverage_unit,cells:rep.coverage_cells,changed_paint_cells:rep.surface_paint,pct:Math.round(100 * (rep.surface_paint || 0) / rep.coverage_cells),basis:"Measured 256x256 preview grid; not native pixel verification"} : undefined,\n            scope: { colour_target: rep.colour_target || undefined, parts: arr(rep.parts),', 1),
] + mcp_measurement_edits())


candidate('js/spb-pro-carmap.js', [
    ("        var n = norm(l.name), g = norm(l.groupName || '');", "        var n = norm(l.name), g = norm(l.groupName || '');\n        var labelled = window.SpbTemplateLayers && SpbTemplateLayers.classify(l);\n        if (labelled && (labelled.kind === 'spec' || labelled.kind === 'alpha')) return labelled.role;", 1),
    ('var sg = signature(); if (ROLES_SIG === sg && ROLES_OUT)', "var rs = sourceDescriptor();\n        var sg = signature() + '|roles:' + JSON.stringify(layersArr().map(function(l){return l && [l.id, l.groupName || ''];})) + '|' + rs.path + ':' + rs.generation + '|' + !!window.SpbTemplateLayers; if (ROLES_SIG === sg && ROLES_OUT)", 1),
])

# A duplicate-name clarification must not be converted to generic colour flags.
# Apply to the already-prepared builder candidate, preserving all source-owner hooks.
for index, (destination, text, patch) in enumerate(prepared):
    if destination.name == 'spb-offline-builder.js':
        from builder_input_edits import edits as builder_input_edits
        for before, after, count in builder_input_edits():
            owner_after = after.replace("var live = p.querySelector('.spb-pai-input');", "var live = W.SPB_CX3_OFF ? inp : p.querySelector('.spb-pai-input');")
            if text.count(after) == count or text.count(owner_after) == count:
                continue
            if text.count(before) != count:
                raise RuntimeError('Builder input anchor changed')
            text = text.replace(before, after, count)
        anchor = '        if (ed.prohibited_edit || (ed.protected_parts && ed.protected_parts.length)) return null;'
        if text.count(anchor) != 1:
            raise RuntimeError('Ambiguity guard anchor changed')
        if text.count('if (!W.SPB_CX3_OFF && ed.layer_target_question) return null;') != 1:
            text = text.replace(anchor, '        if (ed.layer_target_question) return null;\n' + anchor, 1)
        original = (ROOT / 'js/spb-offline-builder.js').read_text(encoding='utf-8').replace('\r\n', '\n')
        patch = ''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True), fromfile='js/spb-offline-builder.js', tofile='private/spb-offline-builder.js'))
        prepared[index] = (destination, text, patch)
        next(row for row in records if row['source'] == 'js/spb-offline-builder.js')['candidate_sha256'] = hashlib.sha256(text.encode('utf-8')).hexdigest()

from native_layer_colour_edits import edits as native_layer_colour_edits
from builder_receipt_edits import edits as builder_receipt_edits
from layer_inventory_edits import edits as layer_inventory_edits
from layer_inspection_edits import edits as layer_inspection_edits
from editor_capability_edits import edits as editor_capability_edits
from document_bridge_edits import edits as document_bridge_edits
from delivery_ack_edits import edits as delivery_ack_edits
from frame_layer_edits import edits as frame_layer_edits
from artwork_core_edits import edits as artwork_core_edits
from chat_layout_edits import edits as chat_layout_edits
from element_resize_edits import edits as element_resize_edits
from project_save_ready_edits import edits as project_save_ready_edits
from layer_colour_followup_edits import edits as layer_colour_followup_edits
from panel_location_edits import edits as panel_location_edits
from reference_followup_edits import edits as reference_followup_edits
from named_zone_material_edits import edits as named_zone_material_edits
from named_pattern_refinement_edits import edits as named_pattern_refinement_edits
from mcp_render_dialog_edits import edits as mcp_render_dialog_edits
from composer_pending_edits import edits as composer_pending_edits
from composer_draft_edits import edits as composer_draft_edits
from relay_status_edits import edits as relay_status_edits
from relay_notice_edits import edits as relay_notice_edits
from answer_lifecycle_edits import edits as answer_lifecycle_edits
from natural_reference_edits import edits as natural_reference_edits
from source_loading_composer_edits import edits as source_loading_composer_edits
from legacy_geometry_edits import edits as legacy_geometry_edits
from named_part_edits import edits as named_part_edits
from source_bound_execution_edits import edits as source_bound_execution_edits
from relay_delivery_edits import edits as relay_delivery_edits
from named_layer_material_edits import edits as named_layer_material_edits
from answer_links_edits import edits as answer_links_edits
from relay_transport_edits import edits as relay_transport_edits
from reference_suggestion_edits import edits as reference_suggestion_edits
from material_answer_lifecycle_edits import edits as material_answer_lifecycle_edits
from discussion_boundary_edits import classifier_edits, index_edits as discussion_boundary_index_edits
from fresh_install_edits import index_candidate as fresh_install_index_candidate
from bridge_recovery_edits import edits as bridge_recovery_edits
candidate('js/spb-mcp-bridge.js', bridge_recovery_edits())
candidate('js/spb-convo-state.js', [])
candidate('mcp/server/design-intent.cjs', classifier_edits((ROOT / 'mcp/server/design-intent.cjs').read_text(encoding='utf-8').replace('\r\n', '\n')))
candidate('js/spb-design-intent.js', classifier_edits((ROOT / 'js/spb-design-intent.js').read_text(encoding='utf-8').replace('\r\n', '\n')))
candidate('js/ui/spb-nuq-fix.js', chat_layout_edits())
for frame_source in ('js/spb-intent-model.js', 'js/spb-intent-frame.js', 'js/spb-intent-plan.js'):
    candidate(frame_source, [])
for index, (destination, text, patch) in enumerate(prepared):
    row = next(r for r in records if Path(r['source']).name == destination.name)
    source_original = (ROOT / row['source']).read_text(encoding='utf-8').replace('\r\n', '\n')
    inventory_edits = filter_inventory_edits(row['source'], source_original, layer_inventory_edits(row['source']))
    inventory_edits += panel_location_edits(row['source'])
    changed = project_save_ready_edits(row['source']) + element_resize_edits(row['source']) + native_layer_colour_edits(row['source'], text) + layer_colour_followup_edits(row['source']) + builder_receipt_edits(row['source'], text) + inventory_edits + layer_inspection_edits(row['source'], text) + editor_capability_edits(row['source']) + document_bridge_edits(row['source']) + delivery_ack_edits(row['source']) + frame_layer_edits(row['source']) + artwork_core_edits(row['source'])
    changed += reference_followup_edits(row['source'])
    changed += named_zone_material_edits(row['source'])
    changed += named_pattern_refinement_edits(row['source'])
    changed += mcp_render_dialog_edits(row['source'])
    changed += composer_pending_edits(row['source'])
    changed += composer_draft_edits(row['source'])
    changed += relay_status_edits(row['source'])
    changed += relay_notice_edits(row['source'])
    changed += answer_lifecycle_edits(row['source'])
    changed += natural_reference_edits(row['source'])
    changed += material_answer_lifecycle_edits(row['source'])
    changed += discussion_boundary_index_edits(row['source'])
    changed += source_loading_composer_edits(row['source'])
    changed += legacy_geometry_edits(row['source'])
    changed += named_part_edits(row['source'], text)
    changed += source_bound_execution_edits(row['source'])
    changed += relay_delivery_edits(row['source'])
    changed += named_layer_material_edits(row['source'])
    changed += answer_links_edits(row['source'])
    changed += relay_transport_edits(row['source'])
    changed += reference_suggestion_edits(row['source'])
    for before, after, count in changed:
        # Reviewed CX3 successor variants preserve the owner's kill switches
        # and stronger MCP setter/sibling guards. Add only missing receipts.
        if row['source'] == 'js/spb-pro-ai.js':
            if before == '            lch++;\n        });' and text.count(after.replace('if (fullL ||', 'if (!window.SPB_CX3_OFF && (fullL ||').replace("JSON.stringify(al[b.id].fx)) {", "JSON.stringify(al[b.id].fx))) {").replace('if (b.img &&', 'if (!window.SPB_CX3_OFF && b.img &&')) == count:
                continue
            if before == "        if (ed.kind === 'describe') {" and text.count(after.replace('var nativeColour = window.', 'var nativeColour = !window.SPB_CX3_OFF && window.')) == count:
                continue
            if before == '                  var curVis = l.visible !== false' and text.count("                  if (a.source_colour != null || a.replace_tolerance != null) return {error:'Source-colour replacement is not available in this build; use colour and colour_opacity.'};") == 1:
                before = "                  if (a.source_colour != null || a.replace_tolerance != null) return {error:'Source-colour replacement is not available in this build; use colour and colour_opacity.'};\n" + before
                after = after[after.index('                  if (a.source_colour != null) {'):]
            equivalents = {
                "(a.b || 'source-over') === (b.b || 'source-over');": "(a.b || 'source-over') === (b.b || 'source-over') && (window.SPB_CX3_OFF || (a.img === b.img && JSON.stringify(a.fx) === JSON.stringify(b.fx)));",
                'if (l.visible === b.v && l.opacity === b.o && l.blendMode === b.b) return;': 'if (l.visible === b.v && l.opacity === b.o && l.blendMode === b.b && (window.SPB_CX3_OFF || (l.img === b.img && JSON.stringify(l.effects) === JSON.stringify(b.fx)))) return;',
            }
            if before in equivalents and text.count(equivalents[before]) == count:
                continue
            if before == '_log.push(entry); _last = entry; try { if (window.SpbConvo' and text.count(after.replace('if (entryOpts.builderRunReceipt', 'if (!window.SPB_CX3_OFF && entryOpts.builderRunReceipt')) == count:
                continue
            if before == "blend: { type: 'string' } }, required: ['layer']" and "colour_opacity: {type:'number'} }, required: ['layer']" in text:
                before = "blend: { type: 'string' }, colour: {type:'string'}, colour_opacity: {type:'number'} }, required: ['layer']"
            if before.startswith("var op = { kind: 'layer', layer: l.id,") and before not in text:
                before = "var op = { kind: 'layer', layer: l.id, name: l.name, visible: a.visible, opacity: a.opacity, blend: a.blend, colour: nativePatch && nativePatch.colour, colourOpacity: nativePatch && nativePatch.colourOpacity };"
            if before == "                        if (bits.length) lines.push('Layer ' + o.name" and text.count("var colourResult = window.SpbNativeLayerColour ? SpbNativeLayerColour.apply(o,l) : {error:'Native layer colour controls are not ready.'};") == 1:
                before = "var colourResult = window.SpbNativeLayerColour ? SpbNativeLayerColour.apply(o,l) : {error:'Native layer colour controls are not ready.'};"
                after = before + '\n                            if (window.SpbNativeLayerColour) colourOutcomes.push(SpbNativeLayerColour.outcome(o,colourResult));'
            if before == "                    lines.push('Layer ' + o.name + ': ' + (bits.join(', ') || 'unchanged'));" and before not in text:
                for result in ('nativeResult',):
                    native_line = "var " + result + " = window.SpbNativeLayerColour ? SpbNativeLayerColour.apply(o,l) : {error:'Native layer colour controls are not ready.'};"
                    if text.count(native_line) != 1:
                        raise RuntimeError('Owner native-colour branch changed: ' + result)
                    text = text.replace(native_line, native_line + '\n                        if (window.SpbNativeLayerColour) colourOutcomes.push(SpbNativeLayerColour.outcome(o,' + result + '));', 1)
                continue
        if row['source'] == 'js/spb-offline-answer.js' and before == '        h += \'<div class="spb-ob-tsum">\' + esc(A.text) + \'</div>\';' and text.count(after.replace('((A.id', '(!W.SPB_CX3_OFF && (A.id')) == count:
            continue
        if row['source'] == 'js/spb-offline-builder.js' and before == "if (r && r.via === 'design-advice')" and text.count("if (!W.SPB_CX3_OFF && r && (r.via === 'design-advice' || (r.answer && (r.answer.id === 'assistant.live_editor_capabilities' || r.answer.id === 'assistant.template_layers' || r.answer.id === 'assistant.layer_pixels'))))") == 1:
            continue
        if after and text.count(after) == count:
            continue
        if row['source'] == 'js/spb-pro-ai.js' and before == '{ id: l.id, v: l.visible, o: l.opacity, b: l.blendMode }' and text.count('{ id: l.id, v: l.visible, o: l.opacity, b: l.blendMode, img: window.SPB_CX3_OFF ? undefined : l.img, fx: (window.SPB_CX3_OFF || l.effects === undefined) ? undefined : JSON.parse(JSON.stringify(l.effects)) }') == 1:
            continue
        if text.count(before) != count:
            if '--audit-adoption' in sys.argv:
                adoption_audit.append({'source':row['source'],'before':before,'after':after,'expected':count,'found':text.count(before)})
                continue
            raise RuntimeError('Native colour anchor changed: ' + row['source'] + ' count=' + str(text.count(before)) + ' ' + repr(before[:110]))
        text = text.replace(before, after, count)
    if row['source'] == 'mcp/server/index.js':
        text = fresh_install_index_candidate(text)
    if changed or row['source'] == 'mcp/server/index.js':
        original = (ROOT / row['source']).read_text(encoding='utf-8').replace('\r\n', '\n')
        patch = ''.join(difflib.unified_diff(original.splitlines(True), text.splitlines(True), fromfile=row['source'], tofile='private/' + destination.name))
        prepared[index] = (destination, text, patch)
        row['candidate_sha256'] = hashlib.sha256(text.encode('utf-8')).hexdigest()


if '--audit-adoption' in sys.argv:
    print(json.dumps(adoption_audit, indent=2))
    sys.exit(1 if adoption_audit else 0)  # Read-only: never publish during an audit.

for row in records:
    if hashlib.sha256((ROOT / row['source']).read_bytes()).hexdigest() != row['source_sha256']:
        raise RuntimeError('Source changed while building: ' + row['source'])
# Publish only after every anchor/source check passed; a failed rebase cannot
# replace half of the running private candidate set.
for destination, text, patch in prepared:
    destination.write_bytes(text.encode('utf-8'))
    destination.with_suffix(destination.suffix + '.patch').write_bytes(patch.encode('utf-8'))
(DEST / 'sources.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
print(f'Prepared {len(records)} candidates; exact patches ready, shared sources unchanged.')
