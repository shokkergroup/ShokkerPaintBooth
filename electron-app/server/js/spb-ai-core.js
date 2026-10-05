/* ============================================================================
   SPB AI CORE — optional OpenRouter copilot plumbing, shared by Easy and (later) Pro   (SPB-AI 2026-09-30)
   Tool-agnostic: it talks to THIS app's local server (/api/ai/*), which holds the buyer's OpenRouter key.
   The page never sees the key. Nothing here runs unless the buyer turned AI on.

     SpbAI.status() / saveSettings(patch) / models() / credits() / test()
     SpbAI.run({ system, prior, user, tools, maxSteps, onEvent, signal }) -> Promise<result>
        tools: [{ name, description, parameters (JSON schema), handler(args) -> object|Promise, terminal:bool }]
        handler may return { __stop: true, ... } to end the loop (ask_user).
        result: { text, calls, tools:[names], asked, usage:{prompt,completion,cost}, model, error }
     SpbAI.settingsPanel(onChange) -> HTMLElement  (key box, model picker, mode, daily cap, test button)
   ES5 only (old Electron).
   ========================================================================== */
(function () {
    'use strict';
    function BASE() { return window.SPB_AI_BASE || ''; }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }

    function api(method, path, body, signal) {
        var opt = { method: method, headers: { 'Content-Type': 'application/json' }, cache: 'no-store' };
        if (body !== undefined) opt.body = JSON.stringify(body);
        if (signal) opt.signal = signal;
        return fetch(BASE() + path, opt).then(function (r) {
            return r.text().then(function (t) {
                var j = null; try { j = JSON.parse(t); } catch (e) { j = { ok: false, error: 'bad_response', message: 'The server answered with something unexpected.' }; }
                if (j && j.ok === undefined) j.ok = r.ok;
                return j;
            });
        }).catch(function (e) {
            if (e && e.name === 'AbortError') return { ok: false, error: 'aborted', message: 'Cancelled.' };
            return { ok: false, error: 'offline', message: 'Could not reach the Shokker server.' };
        });
    }

    var _status = null, _models = null, _listeners = [], REC_MODEL = 'deepseek/deepseek-v4.1-flash';
    function status(force) {
        if (_status && !force) return Promise.resolve(_status);
        return api('GET', '/api/ai/status').then(function (s) { if (s && s.ok) { _status = s; notify(); } return s; });
    }
    function notify() { _listeners.forEach(function (fn) { try { fn(_status); } catch (e) {} }); }
    function onStatus(fn) { if (_listeners.indexOf(fn) === -1) _listeners.push(fn); }
    function saveSettings(patch) { return api('POST', '/api/ai/settings', patch).then(function (s) { if (s && s.ok) { _status = s; notify(); } return s; }); }
    function models(force) {
        if (_models && !force) return Promise.resolve({ ok: true, models: _models });
        return api('GET', '/api/ai/models' + (force ? '?refresh=1' : '')).then(function (r) { if (r && r.ok) _models = r.models; return r; });
    }
    function credits() { return api('GET', '/api/ai/credits'); }
    function test() { return api('POST', '/api/ai/test', {}).then(function (r) { status(true); return r; }); }
    function chat(body, signal) { return api('POST', '/api/ai/chat', body, signal); }

    // ------------------------------------------------------------------ the tool loop
    function run(o) {
        // Anthropic models (Sonnet / Opus / Fable) reject a top-level anyOf / oneOf / allOf in a tool schema with HTTP 400 (found 2026-10-01: the edit_zone "zone | zone_id | zone_name" rule made every Claude model fail on the OpenRouter route while cheap models accepted it); the handler already validates the targeting
        function cleanParams(p) { if (!p) return { type: 'object', properties: {} }; var c = {}; Object.keys(p).forEach(function (k) { if (k !== 'anyOf' && k !== 'oneOf' && k !== 'allOf' && k !== 'not') c[k] = p[k]; }); return c; }
        var tools = o.tools || [], byName = {}, schemas = [], i;
        for (i = 0; i < tools.length; i++) { byName[tools[i].name] = tools[i]; schemas.push({ type: 'function', function: { name: tools[i].name, description: tools[i].description, parameters: cleanParams(tools[i].parameters) } }); }
        var msgs = [{ role: 'system', content: o.system }].concat(o.prior || []).concat([{ role: 'user', content: o.userContent || o.user }]);
        if (o.debug) window.__spbAITranscript = msgs;                       // same array, mutated in place: inspect everything the model saw/did
        var maxSteps = o.maxSteps || 6, usage = { prompt: 0, completion: 0, cost: 0 }, calls = 0, used = [], model = null, asked = null, nudged = false;
        var INTENT = /\b(i['’]ll|i will|i['’]m going to|let me|i am going to|going to (make|change|apply|tone|pull|swap|switch))\b/i;
        function ev(type, data) { try { if (o.onEvent) o.onEvent(type, data || {}); } catch (e) {} }
        function fail(r) { return { text: '', calls: calls, tools: used, asked: null, usage: usage, model: model, transcript: msgs, error: r || { error: 'unknown', message: 'Something went wrong.' } }; }
        var hinted = false, reviewed = false;
        // Out of rounds: never end in silence. One last call WITHOUT tools: say what was done, what could not be done and why.
        function wrapUp() {
            ev('wrapup', {});
            msgs.push({ role: 'user', content: 'You are out of rounds. Reply now in 2-3 short plain sentences: what you changed, what you could NOT do and why, and what you suggest next. Do not call any tool.' });
            return chat({ messages: msgs, max_tokens: 400, temperature: 0.3, model: o.model, vision: o.vision ? true : undefined, reasoning: o.reasoning }, o.signal).then(function (r) {
                var text = '';
                if (r && r.ok) { calls++; model = r.model || model; if (r.usage) { usage.prompt += r.usage.prompt || 0; usage.completion += r.usage.completion || 0; usage.cost += r.usage.cost || 0; } text = String((r.message && r.message.content) || '').trim(); }
                return { text: text, calls: calls, tools: used, asked: null, usage: usage, model: model, capped: true };
            });
        }
        function step(n) {
            if (n >= maxSteps) return wrapUp();
            if (!hinted && maxSteps >= 6 && n >= maxSteps - 3) { hinted = true; msgs.push({ role: 'user', content: '(About 3 rounds left. Stop researching: call the change tools now with your best choices, several at once, then reply.)' }); }
            ev('thinking', { step: n });
            return chat({ messages: msgs, tools: schemas, max_tokens: o.maxTokens || 900, temperature: o.temperature == null ? 0.3 : o.temperature, model: o.model, vision: o.vision ? true : undefined, reasoning: o.reasoning, tool_choice: (o.forceText && n > 0) ? 'none' : 'auto' }, o.signal).then(function (r) {
                if (!r || !r.ok) return fail(r);
                calls++; model = r.model || model;
                if (r.usage) { usage.prompt += r.usage.prompt || 0; usage.completion += r.usage.completion || 0; usage.cost += r.usage.cost || 0; }
                var m = r.message || {}, tcs = (m.tool_calls || []).filter(function (c) { return c && c.function && c.function.name; });
                msgs.push({ role: 'assistant', content: m.content || '', tool_calls: tcs.length ? tcs : undefined });
                if (!tcs.length) {
                    // a model that SAYS it will change things but calls no tool: one firm nudge, then accept whatever comes back
                    if (o.nudge && !nudged && !used.length && INTENT.test(m.content || '')) { nudged = true; msgs.push({ role: 'user', content: 'Go ahead and do that now by calling the tools (style / adjust / apply_look). Do not describe it again.' }); return step(n + 1); }
                    return { text: (m.content || '').trim(), calls: calls, tools: used, asked: asked, usage: usage, model: model };
                }
                var stop = null, allTerminal = true;
                return tcs.reduce(function (p, c) {
                    return p.then(function () {
                        var t = byName[c.function.name], args = {}, res;
                        used.push(c.function.name);
                        if (!t) { res = { error: 'unknown tool ' + c.function.name }; allTerminal = false; }
                        else {
                            try { args = c.function.arguments ? JSON.parse(c.function.arguments) : {}; } catch (e) { args = null; }
                            if (args === null) { res = { error: 'arguments were not valid JSON' }; }
                            else { if (!t.terminal) allTerminal = false; try { res = t.handler(args); } catch (e2) { res = { error: String(e2 && e2.message || e2) }; } }
                        }
                        ev('tool', { name: c.function.name, args: args });
                        return Promise.resolve(res).then(function (rv) {
                            if (rv && rv.__stop) { stop = rv; }
                            msgs.push({ role: 'tool', tool_call_id: c.id, content: JSON.stringify(rv && rv.__stop ? { ok: true, note: 'waiting for the buyer' } : rv).slice(0, 6000) });
                        });
                    });
                }, Promise.resolve()).then(function () {
                    if (stop) return { text: (m.content || '').trim(), calls: calls, tools: used, asked: stop, usage: usage, model: model };
                    // [SPB-AI 2026-09-30] o.review: after the model queued its changes, ONE more round with tools still on: "is every part of the request covered?
                    // fix what is missing, otherwise write the real summary". Text that arrived WITH the tool calls is an announcement ("Now I'll build it"), not a summary.
                    if (o.review && allTerminal && !reviewed) { reviewed = true; msgs.push({ role: 'user', content: o.review }); return step(n + 1); }
                    if (o.review && allTerminal && reviewed) { msgs.push({ role: 'user', content: 'Now write your final reply to the buyer following the reply rules. Do not call any tool.' }); o.forceText = true; return step(n + 1); }
                    if (allTerminal && (m.content || '').trim()) return { text: m.content.trim(), calls: calls, tools: used, asked: null, usage: usage, model: model };   // said it AND did it: no extra round trip
                    if (allTerminal) { o.forceText = true; }
                    return step(n + 1);
                });
            });
        }
        return step(0);
    }

    // ------------------------------------------------------------------ settings panel (shared look)
    function settingsPanel(onChange) {
        var el = document.createElement('div'); el.className = 'spb-ai-panel';
        function fmt$(v) { return '$' + (Number(v) || 0).toFixed(4); }
        function draw(s, note) {
            s = s || _status || {};
            var keyRow = s.configured
                ? '<div class="spb-ai-row"><span class="spb-ai-lab">Key</span><span class="spb-ai-keyok">' + esc(s.keyMasked) + ' <small>' + (s.keyFromEnv ? '(from this computer’s environment)' : (s.storage === 'dpapi' ? '(saved, encrypted for your Windows account)' : '(saved on this computer)')) + '</small></span>' + (s.keyFromEnv ? '' : '<button type="button" class="spb-ai-btn" data-ai="removekey">Remove</button>') + '</div>'
                : '<div class="spb-ai-row"><span class="spb-ai-lab">Key</span><input type="password" class="spb-ai-input" id="spbAiKey" placeholder="Paste your OpenRouter key (sk-or-…)" autocomplete="off" spellcheck="false"><button type="button" class="spb-ai-btn hot" data-ai="savekey">Save</button></div>' +
                  '<div class="spb-ai-note">Get one free at <b>openrouter.ai/keys</b> — add a few dollars of credit and set a spending limit on the key. It stays on this computer; only the model provider you choose ever sees your requests.</div>';
            el.innerHTML = '<div class="spb-ai-head"><b>\u2460 AI inside Shokker</b><small>you chat in this panel \u00b7 uses your OpenRouter key \u00b7 optional</small></div><div class="spb-ai-note">Shokker\u2019s own designer does what it can <b>free</b>; only what it cannot figure out goes to the <b>MODEL</b> below (the Copilot model). <b>deepseek/deepseek-v4.1-flash</b> is recommended: the cheapest that works well.</div>' + keyRow +
                (s.configured ? '<div class="spb-ai-row"><span class="spb-ai-lab">Model</span><select class="spb-ai-input" id="spbAiModel"><option value="' + esc(s.model) + '">' + esc(s.model) + '</option></select><button type="button" class="spb-ai-btn" data-ai="loadmodels" title="Load the live model list with prices">Choose…</button></div>' +
                    (s.provider !== 'local' && s.model && s.model !== REC_MODEL ? '<div class="spb-ai-note warn">\u26a0 You are on <b>' + esc(s.model) + '</b>, which usually costs more than the recommended <b>' + REC_MODEL + '</b>. <button type="button" class="spb-ai-btn" data-ai="userec">Use the recommended model</button></div>' : (s.provider !== 'local' ? '<div class="spb-ai-note">\u2713 This is the recommended low-cost model.</div>' : '')) +
                    '<div class="spb-ai-row"><span class="spb-ai-lab">Repairs</span><input type="text" class="spb-ai-input" id="spbAiEsc" placeholder="Repair turns use a different model (optional)" value="' + esc(s.escalateModel || '') + '" spellcheck="false"><button type="button" class="spb-ai-btn" data-ai="escsave">Save</button></div>' +
                    '<div class="spb-ai-note">Repair turns use a different model (optional). Leave empty to use your model for everything. Picture checks run on your model if it can see pictures; otherwise the app checks the result itself.</div>' +
                    '<div class="spb-ai-row"><span class="spb-ai-lab">When</span><select class="spb-ai-input" id="spbAiMode"><option value="auto">Auto — use AI only when the built-in parser isn’t sure</option><option value="always">Always — send every request to the AI</option><option value="off">Off</option></select></div>' +
                    '<div class="spb-ai-row"><span class="spb-ai-lab">Daily cap</span><input type="number" min="0.05" step="0.25" class="spb-ai-input short" id="spbAiCap" value="' + esc(s.dailyCap) + '"><span class="spb-ai-mut">$ per day, checked here before every request</span></div>' +
                    '<div class="spb-ai-row"><span class="spb-ai-lab">Today</span><span class="spb-ai-mut">' + fmt$(s.today && s.today.cost) + ' · ' + ((s.today && s.today.calls) || 0) + ' requests</span><button type="button" class="spb-ai-btn" data-ai="test">Test connection</button><button type="button" class="spb-ai-btn" data-ai="credits">Check credit</button></div>' : '') +
                '<details class="spb-ai-local"' + (s.provider === 'local' ? ' open' : '') + '><summary>Private option: a model running on this PC (Ollama / LM Studio)</summary>' +
                    '<div class="spb-ai-note">Nothing leaves your computer and there is no cost, but small local models are slower and less clever. Install Ollama (ollama.com), run <b>ollama pull qwen2.5:7b</b> (or any model that supports tools), then enter its name here.</div>' +
                    '<div class="spb-ai-row"><span class="spb-ai-lab">Use it</span><label><input type="checkbox" id="spbAiLocalOn"' + (s.provider === 'local' ? ' checked' : '') + '> Run the copilot on this PC instead of OpenRouter</label></div>' +
                    '<div class="spb-ai-row"><span class="spb-ai-lab">Address</span><input type="text" class="spb-ai-input" id="spbAiLocalBase" value="' + esc(s.localBase || 'http://127.0.0.1:11434/v1') + '"></div>' +
                    '<div class="spb-ai-row"><span class="spb-ai-lab">Model</span><input type="text" class="spb-ai-input" id="spbAiLocalModel" placeholder="e.g. qwen2.5:7b" value="' + esc(s.localModel || '') + '"><button type="button" class="spb-ai-btn" data-ai="localsave">Save &amp; test</button></div></details>' +
                '<div class="spb-ai-out" id="spbAiOut">' + (note ? esc(note) : '') + '</div>';
            var sel = el.querySelector('#spbAiMode'); if (sel) sel.value = s.mode || 'auto';
        }
        function out(t, bad) { var o = el.querySelector('#spbAiOut'); if (o) { o.textContent = t; o.className = 'spb-ai-out' + (bad ? ' bad' : ''); } }
        status(true).then(function (s) { draw(s); });
        // one truth: when the model / key / mode changes anywhere (this panel, or anything else that saves the model), redraw from the cached status (no network, never while you are typing in it)
        onStatus(function (s) { if (!el.isConnected) return; var ae = document.activeElement; if (ae && el.contains(ae) && /^(INPUT|SELECT|TEXTAREA)$/.test(ae.tagName)) return; draw(s || _status); });
        el.addEventListener('click', function (ev) {
            var b = ev.target && ev.target.closest ? ev.target.closest('[data-ai]') : null; if (!b) return;
            var act = b.getAttribute('data-ai');
            if (act === 'savekey') { var v = (el.querySelector('#spbAiKey') || {}).value || ''; out('Saving…'); saveSettings({ key: v }).then(function (r) { if (r.ok) { draw(r, 'Saved. Press “Test connection” to try it.'); if (onChange) onChange(r); } else out(r.message || 'Could not save that key.', true); }); }
            else if (act === 'localsave') {
                var lb = (el.querySelector('#spbAiLocalBase') || {}).value || '', lm = (el.querySelector('#spbAiLocalModel') || {}).value || '', on = !!(el.querySelector('#spbAiLocalOn') || {}).checked;
                out('Saving…'); saveSettings({ localBase: lb, localModel: lm, provider: on ? 'local' : 'openrouter' }).then(function (r) { if (!r.ok) return out(r.message || 'Could not save.', true); draw(r); if (onChange) onChange(r); if (!on) return out('Saved. Local mode is off.'); out('Testing the local model…'); test().then(function (t) { if (t.ok) out('Working — ' + t.model + ' answered in ' + t.ms + ' ms on this PC.'); else out(t.message || 'That did not work.', true); }); });
            }
            else if (act === 'escsave') { var ev2 = ((el.querySelector('#spbAiEsc') || {}).value || '').trim(); saveSettings({ escalateModel: ev2 || 'off' }).then(function (r) { if (r && r.ok) out(r.escalateModel ? 'Repair turns will use ' + r.escalateModel + '.' : 'Repair turns use your model.'); else out((r && r.message) || 'Could not save.', true); if (onChange) onChange(r); }); }
            else if (act === 'userec') { saveSettings({ model: REC_MODEL }).then(function (r) { if (r && r.ok) out('Model set to ' + r.model + '.'); if (onChange) onChange(r); }); }
            else if (act === 'removekey') { saveSettings({ key: '' }).then(function (r) { draw(r, 'Key removed.'); if (onChange) onChange(r); }); }
            else if (act === 'test') { out('Testing…'); test().then(function (r) { if (r.ok) { out('Working — ' + r.model + ' answered in ' + r.ms + ' ms (cost ' + fmt$(r.cost) + ').'); draw(_status, 'Working — ' + r.model + ' answered in ' + r.ms + ' ms.'); } else out(r.message || 'That did not work.', true); }); }
            else if (act === 'credits') { out('Checking…'); credits().then(function (r) { if (r.ok) out('OpenRouter says: ' + (r.limit == null ? 'no spending limit' : ('$' + Number(r.remaining).toFixed(2) + ' left of this key’s $' + Number(r.limit).toFixed(2) + ' limit')) + '; used $' + Number(r.usage || 0).toFixed(4) + ' in total.'); else out(r.message || 'Could not check.', true); }); }
            else if (act === 'loadmodels') {
                out('Loading models…');
                models(true).then(function (r) {
                    if (!r.ok) return out(r.message || 'Could not load models.', true);
                    var s = _status || {}, sel = el.querySelector('#spbAiModel'); if (!sel) return;
                    var rec = ['deepseek/deepseek-v4.1-flash', 'z-ai/glm-5.3-flash', 'qwen/qwen3.7-flash', 'openai/gpt-oss-120b'];
                    var rows = r.models.slice(0, 400);
                    sel.innerHTML = rows.map(function (m) { return '<option value="' + esc(m.id) + '">' + esc(m.id) + ' — ' + (m.free ? 'free' : '$' + m.in + ' in / $' + m.out + ' out per M') + (m.vision ? ' · sees images' : '') + '</option>'; }).join('');
                    sel.value = s.model; if (sel.value !== s.model) { sel.insertAdjacentHTML('afterbegin', '<option value="' + esc(s.model) + '">' + esc(s.model) + '</option>'); sel.value = s.model; }
                    out(rows.length + ' models that can use tools, cheapest first. Pick one — cheap ones vary in quality.');
                });
            }
        });
        el.addEventListener('change', function (ev) {
            var t = ev.target;
            if (t.id === 'spbAiModel') saveSettings({ model: t.value }).then(function (r) { if (r.ok) out('Model set to ' + r.model + '.'); if (onChange) onChange(r); });
            else if (t.id === 'spbAiMode') saveSettings({ mode: t.value }).then(function (r) { if (onChange) onChange(r); out(r.mode === 'off' ? 'AI is off — the built-in parser handles everything.' : (r.mode === 'always' ? 'Every request goes to the AI.' : 'The AI helps only when the parser isn’t sure.')); });
            else if (t.id === 'spbAiCap') saveSettings({ dailyCap: Number(t.value) }).then(function (r) { if (onChange) onChange(r); out('Daily cap set to $' + Number(r.dailyCap).toFixed(2) + '.'); });
        });
        return el;
    }

    window.SpbAI = { status: status, onStatus: onStatus, saveSettings: saveSettings, models: models, credits: credits, test: test, chat: chat, run: run, settingsPanel: settingsPanel, cached: function () { return _status; } };
})();
