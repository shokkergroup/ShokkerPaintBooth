/* ============================================================================
   SPB CHAT STUDIO  (SPB-CHAT 2026-10-01)
   The easy way in (replaces Easy Mode, which is parked): the AI / offline copilot docked on the left, a big live preview on the right.
   Same engine, same paint, same zones as Pro: this is only a different front door. "Full editor" (or the PRO button) closes it.
   window.SpbChatStudio = { open, close, toggle, isOpen }          ES5 only
   COPILOT-PAGE 2026-10-04 (owner: "I'd still like to see the SOURCE, LIVE PREVIEW, and the 4 boxes showing Combined, Red, Green, and Blue channels. AND if there's
   layers it should have the layer bar down the right ... Ability to lock to layer"): a view strip under the big car that MIRRORS the Full Editor (no second render
   pipeline), a layer bar on the right built from _psdLayers + SpbProCar.roles(), and Lock-to-layer (a chip in the copilot; typed requests get "in the <layer> layer, ").
   ========================================================================== */
(function () {
    'use strict';
    var KEY = 'spb_chat_studio', _el = null, _open = false, _view = 'paint', _timer = null, _lastSrc = '', _lastChips = '', _lastBusy = false;
    function $(id) { return document.getElementById(id); }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    function lsGet(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
    function lsSet(k, v) { try { window.localStorage.setItem(k, v); } catch (e) {} }

    function build() {
        if (_el) return _el;
        _el = document.createElement('div'); _el.id = 'spbChatStudio'; _el.hidden = true;
        _el.innerHTML =
            '<div class="spb-cs-top">' +
              '<div class="spb-cs-brand">SHOKKER <b>PAINT BOOTH</b><span>Chat studio</span></div>' +
              '<div class="spb-cs-car" id="spbCsCar"></div>' +
              '<div class="spb-cs-tabs" role="tablist" aria-label="What to show">' +
                '<button type="button" class="spb-cs-tab on" data-cs-view="paint" role="tab">Paint</button>' +
                '<button type="button" class="spb-cs-tab" data-cs-view="spec" role="tab" title="The spec map: red = metal, teal = matte, black = gloss">Shine (spec)</button>' +
                '<button type="button" class="spb-cs-tab" data-cs-view="parts" role="tab" title="The car parts Shokker knows">Car parts</button>' +
              '</div>' +
              '<span class="spb-cs-sp"></span>' +
              '<button type="button" class="spb-cs-btn" onclick="window.SpbEncyclopedia&amp;&amp;window.SpbEncyclopedia.open()" title="SPB Encyclopedia: how everything in Shokker works (ENC_READER_FIX 2026-10-05: the top-bar button is covered in this window)">&#128214; Encyclopedia</button>' +
              '<button type="button" class="spb-cs-btn hot" data-cs-act="render" title="Render the paint and spec files (same as the RENDER button in the full editor)">Render &amp; save</button>' +
              '<button type="button" class="spb-cs-btn ghost" data-cs-act="full" title="Close the studio and use the full editor">Full editor &rarr;</button>' +
            '</div>' +
            '<div class="spb-cs-sub">' +
              '<button type="button" class="spb-cs-btn spark" data-cs-act="ideas" title="Four different complete designs for your car: tap the one you like">&#10022; Surprise me</button>' +
              '<button type="button" class="spb-cs-btn" data-cs-act="picture" title="Pick a sponsor logo, a photo or a flag: I design in its colours (or just drop the picture on the car)">&#128206; Colours from a picture</button><input type="file" id="spbCsFile" accept="image/*" hidden>' +
              '<button type="button" class="spb-cs-btn" data-cs-act="copyrecipe" title="Copy this design as text: paste it into the chat of anyone with Shokker Paint Booth (or on another of your cars) to apply it there">&#10697; Copy recipe</button>' +
              '<button type="button" class="spb-cs-btn" data-cs-act="pasterecipe" title="Apply a design recipe someone shared with you">&#128203; Paste recipe</button>' +
              '<button type="button" class="spb-cs-btn" data-cs-act="support" title="Talk to Shokker: something not rendering, or not showing in iRacing? I read your live settings and your iRacing folder and tell you which step is off (free, offline)">&#10067; Check my setup</button>' +
              '<button type="button" class="spb-cs-btn" data-cs-act="demo" id="spbCsDemoBtn" title="Watch a 60-second tour: Shokker designs a livery from plain words">&#9654; Watch a demo</button>' +
              '<span class="spb-cs-aigroup">' + '<span class="spb-cs-aihead" id="spbCsAiHead" hidden>AI</span><label class="spb-cs-brain" id="spbCsOfWrap" hidden title="ON: simple requests (colours, parts, looks, numbers, stripes, themes) are done by the built-in brain for free and instantly; only open-ended requests go to the AI. OFF: every request goes to the AI."><input type="checkbox" id="spbCsOf"> Free designer first</label>' +
              '<button type="button" class="spb-cs-modelchip" id="spbCsModelChip" data-cs-act="aigear" hidden title="The model that answers when Shokker\'s own designer cannot figure a request out. It is the Copilot model in the gear (MODEL): change it there. DeepSeek v4.1 Flash is recommended (a fraction of a cent per request).">Model</button>' +
              '<button type="button" class="spb-cs-btn ghost" data-cs-act="aihelp" id="spbCsAiHelpBtn" title="How do Claude and OpenAI connect to Shokker? Two ways, explained.">&#9432; How AI works</button>' + '</span>' +
              '<span class="spb-cs-sp"></span>' +
              '<button type="button" class="spb-cs-btn" data-cs-act="compare" title="Slide to compare before and after">&#8660; Compare</button>' +
              '<button type="button" class="spb-cs-btn" data-cs-act="undo" title="Undo the last thing the copilot changed">&#8630; Undo</button>' +
            '</div>' +
            '<div class="spb-cs-main"><div class="spb-cs-stage"><div class="spb-cs-frame" id="spbCsFrame"><img id="spbCsImg" alt="Live preview of your paint"><canvas id="spbCsBigCv" class="spb-cs-bigcv" hidden></canvas><div class="spb-cs-cmp" id="spbCsCmp" hidden><img id="spbCsBefore" alt="Before"><div class="spb-cs-cmp-line" id="spbCsCmpLine"><span>&#8660;</span></div><em class="spb-cs-cmp-l">BEFORE</em><em class="spb-cs-cmp-r">NOW</em></div><div class="spb-cs-toast" id="spbCsToast" hidden></div><div class="spb-cs-cap" id="spbCsCap" hidden></div><div class="spb-cs-wait" id="spbCsWait" hidden><span class="spb-cs-spin"></span><em>painting…</em></div><div class="spb-cs-empty" id="spbCsEmpty">Your car will appear here as soon as it is open and the first preview is painted.<br><button type="button" class="spb-cs-btn hot" data-cs-act="openfile">Open my car file (PSD or TGA)</button><button type="button" class="spb-cs-btn" data-cs-act="refresh">Paint a preview</button></div></div>' + stripHtml() + '</div>' + layersHtml() + '</div>' +
            '<div class="spb-cs-film-row"><span class="spb-cs-foot-lab">Versions</span><div class="spb-cs-film" id="spbCsFilm"><span class="spb-cs-chip dim">your first change will appear here: click any version to go back to it</span></div></div>' +
            '<div class="spb-cs-foot"><span class="spb-cs-foot-lab">Your design</span><div class="spb-cs-chips" id="spbCsChips"></div></div>';
        document.body.appendChild(_el);
        _el.addEventListener('click', function (ev) {
            var vb = ev.target && ev.target.closest ? ev.target.closest('[data-cs-ver]') : null; if (vb) { try { window.spbProAI.restoreVersion(vb.getAttribute('data-cs-ver')); } catch (e0) {} return; }
            var bg = ev.target && ev.target.closest ? ev.target.closest('[data-cs-big]') : null; if (bg) { setView(bg.getAttribute('data-cs-big')); return; }
            var ly = ev.target && ev.target.closest ? ev.target.closest('[data-cs-lay]') : null;
            if (ly) { var row = ly.closest('[data-cs-lid]'), lid = row ? row.getAttribute('data-cs-lid') : ''; if (ly.getAttribute('data-cs-lay') === 'eye') { try { if (typeof toggleLayerVisible === 'function') toggleLayerVisible(lid); } catch (eL) {} _lastLayers = ''; syncLayers(); } else setLock(lid); return; }
            var t = ev.target && ev.target.closest ? ev.target.closest('[data-cs-view],[data-cs-act]') : null; if (!t) return;
            if (t.hasAttribute('data-cs-view')) { setView(t.getAttribute('data-cs-view')); return; }
            var a = t.getAttribute('data-cs-act');
            if (a === 'full') close();
            else if (a === 'undo') { var ok = false; try { ok = window.spbProAI && window.spbProAI._undoLast && window.spbProAI._undoLast(); } catch (e) {} if (!ok) { try { if (typeof undoZoneChange === 'function') undoZoneChange(); } catch (e2) {} } }
            else if (a === 'render') { try { if (typeof safeDoRender === 'function') safeDoRender(); else { var b = $('btnRender'); if (b) b.click(); } } catch (e3) {} }
            else if (a === 'compare') toggleCompare();
            else if (a === 'picture') { var fi = $('spbCsFile'); if (fi) { fi.value = ''; fi.click(); } }
            else if (a === 'demo') { if (_demo) stopDemo(); else playDemo(); }
            else if (a === 'ideas') { try { window.spbProAI.send('Surprise me'); } catch (e5) {} }
            else if (a === 'aihelp') toggleAiHelp();
            else if (a === 'aihelpclose') toggleAiHelp(false);
            else if (a === 'aigear') openGear();
            else if (a === 'support') { try { window.spbProAI.send('Check my setup'); } catch (e7) {} }
            else if (a === 'openfile') openCarFile();
            else if (a === 'copyrecipe') { try { window.spbProAI.copyRecipe(); } catch (e6) {} }
            else if (a === 'pasterecipe') { try { navigator.clipboard.readText().then(function (tx) { if (tx && /spb_recipe/.test(tx)) window.spbProAI.send(tx); else { var i2 = document.querySelector('#spbProAI .spb-pai-input'); if (i2) { i2.focus(); i2.placeholder = 'Paste the recipe here, then press Send'; } } }, function () { var i3 = document.querySelector('#spbProAI .spb-pai-input'); if (i3) { i3.focus(); i3.placeholder = 'Paste the recipe here (Ctrl+V), then press Send'; } }); } catch (e7) {} }
            else if (a === 'refresh') { try { if (typeof triggerPreviewRender === 'function') triggerPreviewRender(); } catch (e4) {} }
            else if (a === 'unlock') setLock(null);
            else if (a === 'striptoggle') { var sp = $('spbCsStrip'), hid = !sp.classList.contains('min'); sp.classList.toggle('min', hid); lsSet('spb_cs_strip_min', hid ? '1' : '0'); }
        });
        // Lock-to-layer: rewrite the typed request BEFORE the copilot's own Enter / Send handler reads the box (capture phase runs first)
        document.addEventListener('keydown', function (ev) { var tg = ev.target; if ((ev.key === 'Enter' || ev.keyCode === 13) && !ev.shiftKey && !ev.isComposing && tg && tg.classList && tg.classList.contains('spb-pai-input') && tg.closest && tg.closest('#spbProAI')) beforeSend(tg); }, true);
        document.addEventListener('click', function (ev) { var b = ev.target && ev.target.closest ? ev.target.closest('#spbProAI [data-act="send"]') : null; if (b) beforeSend(document.querySelector('#spbProAI .spb-pai-input')); }, true);
        if (lsGet('spb_cs_strip_min') === '1') { var sp0 = _el.querySelector('#spbCsStrip'); if (sp0) sp0.classList.add('min'); }
        var ofBox = _el.querySelector('#spbCsOf'); if (ofBox) ofBox.addEventListener('change', function () { try { window.localStorage.setItem('spb_pro_ai_offline_first', ofBox.checked ? '1' : '0'); } catch (e) {} });
        var fileIn = _el.querySelector('#spbCsFile'); if (fileIn) fileIn.addEventListener('change', function () { if (fileIn.files && fileIn.files[0]) fromFile(fileIn.files[0]); });
        var fr = _el.querySelector('#spbCsFrame');
        if (fr) {
            ['dragenter', 'dragover'].forEach(function (n) { fr.addEventListener(n, function (e) { if (hasImage(e.dataTransfer)) { e.preventDefault(); fr.classList.add('drop'); } }); });
            ['dragleave', 'drop'].forEach(function (n) { fr.addEventListener(n, function () { fr.classList.remove('drop'); }); });
            fr.addEventListener('drop', function (e) { var f = firstImage(e.dataTransfer); if (f) { e.preventDefault(); fromFile(f); } });
        }
        document.addEventListener('paste', function (e) { if (!_open) return; var f = firstImage(e.clipboardData); if (f) { e.preventDefault(); fromFile(f); } });
        return _el;
    }
    // SPB-MCP 2026-10-04: native CHAT openfile called a missing function.
    // Reuse the transactional loaders; layered files must retain editable layers.
    function openCarFile() {
        if (typeof window.openFilePicker !== 'function') {
            if (typeof window.showToast === 'function') window.showToast('The car file picker is not ready. Open the full editor and try again.', true);
            return false;
        }
        window.openFilePicker({
            title: 'Open your car paint (PSD / TGA / PNG / JPEG)',
            filter: '.psd,.xcf,.ora,.tga,.png,.jpg,.jpeg,.bmp', mode: 'file',
            onSelect: function (filePath) {
                var layered = /\.(psd|xcf|ora)$/i.test(String(filePath || ''));
                var loader = layered ? window.importPSDFromPath : window.loadPaintByPath;
                if (typeof loader !== 'function') {
                    if (typeof window.showToast === 'function') window.showToast('The car paint loader is not ready. Open the full editor and try again.', true);
                    return false;
                }
                return loader(filePath);
            }
        });
        return true;
    }
    function hasImage(dt) { try { if (!dt) return false; var it = dt.items || []; for (var i = 0; i < it.length; i++) if (it[i].kind === 'file' && /^image\//.test(it[i].type)) return true; var fl = dt.files || []; for (var j = 0; j < fl.length; j++) if (/^image\//.test(fl[j].type)) return true; } catch (e) {} return false; }
    function firstImage(dt) { try { var fl = (dt && dt.files) || []; for (var i = 0; i < fl.length; i++) if (/^image\//.test(fl[i].type)) return fl[i]; var it = (dt && dt.items) || []; for (var j = 0; j < it.length; j++) if (it[j].kind === 'file' && /^image\//.test(it[j].type)) return it[j].getAsFile(); } catch (e) {} return null; }
    function fromFile(f) {
        try { var rd = new FileReader(); rd.onload = function () { try { window.spbProAI.pictureChoice(String(rd.result)); } catch (e) { try { window.spbProAI.ideasFromPicture(String(rd.result)); } catch (e1) {} } }; rd.readAsDataURL(f); } catch (e2) {}
    }

    // ------------------------------------------------------------------ DEMO PLAYER (also the sales video): types real requests into the copilot and lets it answer, with a caption for each step
    var _demo = false, _demoTimer = null, _demoLog = [];
    function dlog(m) { try { _demoLog.push(Math.round(Date.now() / 1000) % 100000 + ' ' + m); if (_demoLog.length > 60) _demoLog.shift(); } catch (e) {} }
    var DEMO_STEPS = [
        { say: 'Gulf style: powder blue with an orange stripe', cap: 'Say it in plain words. Shokker finds your car\u2019s hood, roof and sides and lays the whole livery out.' },
        { say: 'make the stripes thinner', cap: 'Then just keep talking: it adjusts the design like a conversation.' },
        { say: 'make the roof matte black', cap: 'Change one part without touching the rest. Your numbers and sponsors are never covered.' },
        { say: 'make the hood a mirror chrome shine, spec only', cap: 'Shine-only changes leave the paint colours exactly as they are.' },
        { say: 'Surprise me', cap: 'Not sure what you want? Four complete ideas, each tried on your car.', pick: 1 },
        { compare: true, cap: 'Slide to see before and after. Every step is saved in Versions: click any one to go back.' }
    ];
    function sleep(ms) { return new Promise(function (r) { _demoTimer = setTimeout(r, ms); }); }
    function whenIdle(maxMs) { var t0 = Date.now(); return new Promise(function (res) { (function poll() { var b = true; try { b = window.spbProAI.busy(); } catch (e) { b = false; } if (!_demo || (!b && Date.now() - t0 > 600) || Date.now() - t0 > (maxMs || 120000)) return res(); setTimeout(poll, 400); })(); }); }
    function caption(t) { var c = $('spbCsCap'); if (!c) return; if (t) { c.textContent = t; c.hidden = false; } else c.hidden = true; }
    function typeInto(inp, text) { return new Promise(function (res) { var i = 0; inp.focus(); inp.value = ''; (function step() { if (!_demo) return res(); if (i >= text.length) return res(); inp.value = text.slice(0, ++i); _demoTimer = setTimeout(step, 28 + Math.random() * 30); })(); }); }
    function setDemoBtn() { var b = $('spbCsDemoBtn'); if (b) { b.innerHTML = _demo ? '&#9632; Stop demo' : '&#9654; Watch a demo'; b.classList.toggle('on', _demo); } }
    function stopDemo(why) { if (_demo) dlog('stop ' + (why || '')); _demo = false; clearTimeout(_demoTimer); caption(''); setDemoBtn(); }
    function playDemo() {
        if (_demo) return; _demo = true; setDemoBtn();
        try { window.spbProAI.open(); } catch (e0) {}
        var chain = Promise.resolve();
        DEMO_STEPS.forEach(function (st, si) {
            chain = chain.then(function () {
                if (!_demo) return;
                dlog('step ' + si);
                caption(st.cap);
                if (st.compare) { if (!_cmp) toggleCompare(); return sleep(7000).then(function () { if (_cmp) toggleCompare(); }); }
                var inp = document.querySelector('#spbProAI .spb-pai-input'); if (!inp) return;
                return sleep(1200).then(function () { return typeInto(inp, st.say); }).then(function () { return sleep(500); }).then(function () {
                    if (!_demo) return; try { window.spbProAI.send(st.say); } catch (e1) {}
                    return whenIdle(150000);
                }).then(function () {
                    if (!_demo) return;
                    if (st.pick != null) { return sleep(2500).then(function () { var b = document.querySelectorAll('#spbProAI .spb-pai-card .spb-pai-act'); if (b.length) b[Math.min(st.pick, b.length - 1)].click(); return whenIdle(60000); }).then(function () { return sleep(2500); }); }
                    return sleep(3500);
                });
            });
        });
        chain.then(function () { if (_demo) { caption('That is the whole idea: say what you want, see it on your car. Now try it yourself.'); return sleep(6000); } }).then(function () { stopDemo('finished'); }, function (e) { dlog('error ' + (e && e.message)); stopDemo('error'); });
    }

    // ------------------------------------------------------------------ BRAIN picker (OpenRouter route): Fast / Sonnet 5.5 / Opus 5.5 / Fable 5.1, prices per million tokens from the live catalogue
    // ---- "How AI works": the two ways to use Claude / OpenAI with Shokker, in plain words (owner 2026-10-01: "I'm confused and this is my product")
    function aiHelpHtml() {
        return '<div class="spb-cs-aihelp-in"><div class="spb-cs-aihelp-h">Two ways to use Claude or OpenAI with Shokker</div>' +
            '<div class="spb-cs-aihelp-card"><b>\u2460 Right here, inside Shokker</b><p>Nothing else to open. You type in the chat on the left. Shokker\u2019s own designer does what it can <b>free and instantly</b>; only what it cannot figure out goes to the <b>Copilot model</b> you set in <b>\u2699 \u2192 MODEL</b>. We recommend <b>DeepSeek v4.1 Flash</b>: a fraction of a cent per request. It needs an <b>OpenRouter key</b> you paste once in <b>\u2699</b>.</p></div>' +
            '<div class="spb-cs-aihelp-card"><b>\u2461 From the Claude or ChatGPT app</b><p>You open <b>Claude</b> (or <b>ChatGPT/Codex</b>) and type there; it paints in Shokker for you using your own Claude / ChatGPT plan, <b>no key</b>. Turn it on in <b>\u2699 \u2192 \u2461 Chat from Claude or ChatGPT</b>, install Shokker in that app once, then tell it what to paint. The model is chosen inside that app, <i>not</i> in Shokker.</p></div>' +
            '<div class="spb-cs-aihelp-card"><b>Something not rendering or not in iRacing?</b><p>That is not an AI question: press <b>\u2753 Check my setup</b>. It is free, works offline and reads your real settings.</p></div>' +
            '<div class="spb-cs-aihelp-row"><button type="button" class="spb-cs-btn" data-cs-act="aigear">Open AI settings \u2699</button><button type="button" class="spb-cs-btn ghost" data-cs-act="aihelpclose">Close</button></div></div>';
    }
    function toggleAiHelp(force) {
        var box = $('spbCsAiHelp');
        if (!box) { box = document.createElement('div'); box.id = 'spbCsAiHelp'; box.className = 'spb-cs-aihelp'; box.hidden = true; var sub = _el && _el.querySelector('.spb-cs-sub'); if (!sub) return; sub.insertAdjacentElement('afterend', box); }
        var open = typeof force === 'boolean' ? force : box.hidden; box.hidden = !open; if (open) box.innerHTML = aiHelpHtml();
    }
    function openGear() { try { var g = document.querySelector('#spbProAI [data-act="gear"]'); var set = document.querySelector('#spbProAI .spb-pai-set'); if (g && set && set.hidden) g.click(); else if (set && !set.firstChild && g) g.click(); toggleAiHelp(false); } catch (e) {} }
    // One model, set in the gear (MODEL). The studio only SHOWS it (a chip) and keeps the "Free designer first" switch in step; there is deliberately no model picker here, so nobody lands on an expensive model by accident.
    var REC_MODEL = 'deepseek/deepseek-v4.1-flash';
    function syncBrain() {
        var st = null; try { st = window.SpbAI && window.SpbAI.cached(); } catch (e) {}
        var on = !!(st && st.configured), ow = $('spbCsOfWrap'), ob = $('spbCsOf'), ah = $('spbCsAiHead'), chip = $('spbCsModelChip');
        if (ah) ah.hidden = !on; if (ow) ow.hidden = !on;
        if (ob) { try { ob.checked = window.localStorage.getItem('spb_pro_ai_offline_first') !== '0'; } catch (eo) {} }
        if (chip) {
            chip.hidden = !on; if (!on) return;
            var m = st.provider === 'local' ? String(st.localModel || 'local model') : String(st.model || ''), short = m.replace(/^.*\//, '');
            var txt = 'Model: ' + short + (m === REC_MODEL ? ' \u2713' : ''); if (chip.textContent !== txt) chip.textContent = txt;
            chip.classList.toggle('warn', st.provider !== 'local' && m !== REC_MODEL);
        }
    }
    function setHint(t, bad) { var h = $('spbCsToast'); if (!h) return; h.textContent = t; h.classList.toggle('bad', !!bad); h.hidden = false; clearTimeout(setHint._t); setHint._t = setTimeout(function () { h.hidden = true; }, bad ? 15000 : 4000); }
    function setView(v) {
        _view = v; _lastSrc = ''; if (!_el) return;
        Array.prototype.forEach.call(_el.querySelectorAll('.spb-cs-tab'), function (b) { b.classList.toggle('on', b.getAttribute('data-cs-view') === v); });
        sync(true);
    }
    function carText() {
        try {
            var L = window.SpbProCar && window.SpbProCar.library && window.SpbProCar.library();
            if (L) return '🏁 ' + L.name;
            var n = ''; try { n = String((document.getElementById('outputDir') || {}).value || '').replace(/[\\\/]+$/, '').split(/[\\\/]/).pop() || ''; } catch (e) {}
            return n ? '🏁 ' + n : '🏁 your car';
        } catch (e2) { return '🏁 your car'; }
    }
    var _errShown = false;
    function sync(force) {
        if (!_open || !_el) return;
        var car = $('spbCsCar'); if (car) { var ct = carText(); if (car.textContent !== ct) car.textContent = ct; }
        try { syncBrain(); } catch (eb) {}
        var img = $('spbCsImg'), empty = $('spbCsEmpty'), src = '';
        if (_view === 'paint') { var p = $('livePreviewImg'); src = (p && p.naturalWidth > 32 && p.complete) ? p.src : ''; }
        else if (_view === 'spec') { var q = $('livePreviewSpecImg'); src = (q && q.naturalWidth > 32 && q.complete) ? q.src : ''; }
        else if (_view === 'parts') { try { var cv = window.SpbProCar && window.SpbProCar.hasParts() ? window.SpbProCar.pickerImage(900, null, null, { noIslands: true }) : null; src = cv ? cv.toDataURL('image/jpeg', 0.85) : ''; } catch (e3) {} if (!src && _view === 'parts') { src = ''; } }
        var bigCv = $('spbCsBigCv'), isBig = _view === 'source' || /^ch-/.test(_view), bigOk = false;
        try { syncStrip(force); } catch (es) {}
        if (isBig) { try { bigOk = syncBig(); } catch (eg) {} if (img && !img.hidden) { img.hidden = true; _lastSrc = ''; } }
        if (bigCv) bigCv.hidden = !(isBig && bigOk);
        if (isBig) { if (empty) { empty.hidden = bigOk; if (!bigOk) empty.firstChild.textContent = _view === 'source' ? 'Open your car file and its paint appears here.' : 'The channels appear after the first preview is painted.'; } }
        else if (img && (force || src !== _lastSrc)) { _lastSrc = src; if (src) img.src = src; img.hidden = !src; }
        if (empty && !isBig) { empty.hidden = !!(src); if (!src && _view !== 'parts') empty.firstChild.textContent = 'Your car will appear here as soon as it is open and the first preview is painted.'; }
        try { syncLayers(); syncLock(); } catch (el) {}
        if (empty && !src && _view === 'parts') empty.firstChild.textContent = 'I do not know this car\'s parts yet. Ask for something on a named part (for example "make the hood black") and I will ask you to show me.';
        var st = $('previewStatus'), state = st ? (st.dataset.state || '') : '', busy = (state === 'rendering' || state === 'stale' || state === 'loading' || state === 'retrying' || state === 'pending');
        var wait = $('spbCsWait'); if (wait && busy !== _lastBusy) { wait.hidden = !busy; _lastBusy = busy; }
        if (state === 'error') { if (!_errShown) { _errShown = true; setHint('The preview could not be painted. If you stacked several designs, say “undo” or “start over”: the render server can combine only about 16 painted zones at once.', true); } } else _errShown = false;
        wireCompare(); syncFilm();
        // zone chips: what the design is made of
        try {
            var zs = window.SpbProZone ? window.SpbProZone.zonesForModel() : [], sig = zs.map(function (z) { return z.i + z.name + (z.muted ? 'm' : '') + z.visible_pct; }).join('|');
            if (sig !== _lastChips) {
                _lastChips = sig; var h = '';
                zs.forEach(function (z) { if (z.muted) return; if (z.covers && /catch-all|everything not claimed/.test(z.covers) && !(z.visible_pct > 1)) return; if (!(z.visible_pct > 0.2) && !/^Everything/.test(z.name)) return; h += '<span class="spb-cs-chip" title="' + esc((z.covers || '') + ' | ' + (z.look || '')) + '"><b>' + esc(String(z.name).slice(0, 28)) + '</b>' + (z.visible_pct != null ? ' <i>' + z.visible_pct + '%</i>' : '') + '</span>'; });
                var c = $('spbCsChips'); if (c) c.innerHTML = h || '<span class="spb-cs-chip dim">nothing changed yet: tell me what you want on the left</span>';
            }
        } catch (e4) {}
    }
    // ------------------------------------------------------------------ COPILOT-PAGE 2026-10-04: the view strip (SOURCE / LIVE PREVIEW / COMBINED / R / G / B)
    // MIRRORS the Full Editor, never re-renders: SOURCE = #paintCanvas (the loaded paint), LIVE PREVIEW = #livePreviewImg.src, the four channel boxes are drawn from
    // #livePreviewSpecImg by window.spbRenderSpecProofSet (paint-booth-2-state-zones.js), the one renderer behind the editor's #specChannelDock. Refreshed on that
    // image's load event (the editor's render-complete hook) plus the 700 ms studio tick. Click a box = show it big in the frame.
    var STRIP = [['source', 'Source', 'The paint as you loaded it (PSD / TGA)'], ['paint', 'Live preview', 'The rendered result'], ['spec', 'Combined', 'The spec map, all channels together'],
        ['ch-r', 'Red \u00b7 metal', 'Red channel = metallic (0 none, 255 full metal)'], ['ch-g', 'Green \u00b7 rough', 'Green channel = roughness (0 mirror, 255 matte)'], ['ch-b', 'Blue \u00b7 coat', 'Blue channel = clearcoat (16 max gloss, 255 dull)']];
    function stripHtml() {
        return '<div class="spb-cs-strip" id="spbCsStrip"><div class="spb-cs-cells">' + STRIP.map(function (s) {
            var media = s[0] === 'paint' ? '<img alt="" id="spbCsMiniLive" hidden>' : '<canvas width="160" height="160" id="spbCsMini-' + s[0] + '"></canvas>';
            return '<button type="button" class="spb-cs-cell c-' + s[0] + '" data-cs-big="' + s[0] + '" title="' + esc(s[2]) + ' \u2014 click to show it big">' + media + '<span>' + s[1] + '</span></button>';
        }).join('') + '</div><button type="button" class="spb-cs-strip-tg" data-cs-act="striptoggle" title="Show / hide the Source, Live preview and channel boxes"><span class="a">&#9662;</span><span class="b">&#9652; Source &middot; Live &middot; Channels</span></button></div>';
    }
    var _stripSpec = '', _stripLive = '', _stripTick = 0, _bigKey = '', _specHooked = false;
    function srcCanvas() { var pc = $('paintCanvas'); return (pc && pc.width > 32 && pc.height > 32) ? pc : null; }
    function drawSource(cv, n) {
        var pc = srcCanvas(); if (!cv || !pc) return false;
        if (cv.width !== n) { cv.width = n; cv.height = n; }
        var ctx = cv.getContext('2d'), s = Math.min(n / pc.width, n / pc.height), w = pc.width * s, h = pc.height * s;
        ctx.clearRect(0, 0, n, n); try { ctx.drawImage(pc, (n - w) / 2, (n - h) / 2, w, h); } catch (e) { return false; } return true;
    }
    function specReady() { var q = $('livePreviewSpecImg'); return (q && q.complete && q.naturalWidth > 32) ? q : null; }
    function syncStrip(force) {
        if (!_el) return;
        var live = $('livePreviewImg'), ls = (live && live.complete && live.naturalWidth > 32) ? live.src : '', ml = $('spbCsMiniLive');
        if (ml && (force || ls !== _stripLive)) { _stripLive = ls; if (ls) ml.src = ls; ml.hidden = !ls; }
        var spec = specReady(), ss = spec ? spec.src : '';
        if (!_specHooked) { var q = $('livePreviewSpecImg'); if (q) { _specHooked = true; q.addEventListener('load', function () { if (_open) setTimeout(function () { syncStrip(false); if (_view === 'spec' || /^ch-/.test(_view)) sync(false); }, 30); }); } }
        if (ss && (force || ss !== _stripSpec) && typeof window.spbRenderSpecProofSet === 'function') {
            _stripSpec = ss; _bigKey = '';
            try { window.spbRenderSpecProofSet(spec, { all: $('spbCsMini-spec'), r: $('spbCsMini-ch-r'), g: $('spbCsMini-ch-g'), b: $('spbCsMini-ch-b') }, 160); } catch (e) {}
        }
        var hasSrc = (force || (_stripTick++ % 3) === 0) ? drawSource($('spbCsMini-source'), 160) : !!srcCanvas();
        Array.prototype.forEach.call(_el.querySelectorAll('.spb-cs-cell'), function (c) {
            var k = c.getAttribute('data-cs-big'), has = k === 'source' ? hasSrc : (k === 'paint' ? !!ls : !!ss);
            c.classList.toggle('on', k === _view); c.classList.toggle('empty', !has);
        });
    }
    // the big frame for the views the editor has no <img> for: SOURCE (redrawn from #paintCanvas) and a single channel (spbRenderSpecProofSet at 1024)
    function syncBig() {
        var cv = $('spbCsBigCv'); if (!cv) return false;
        if (_view === 'source') { if (_stripTick % 2 === 0 || cv.width !== 1024) return drawSource(cv, 1024); return !!srcCanvas(); }
        var ch = { 'ch-r': 'r', 'ch-g': 'g', 'ch-b': 'b' }[_view], spec = specReady(); if (!ch || !spec) return false;
        var key = _view + '|' + spec.src.length + '|' + spec.src.slice(-48);
        if (key !== _bigKey && typeof window.spbRenderSpecProofSet === 'function') { var tg = {}; tg[ch] = cv; try { if (window.spbRenderSpecProofSet(spec, tg, 1024)) _bigKey = key; } catch (e) { return false; } }
        return _bigKey === key;
    }

    // ------------------------------------------------------------------ COPILOT-PAGE 2026-10-04: the layer bar (right) + Lock to layer
    // Rows come from the editor's own _psdLayers (top of the stack first, like renderLayerPanel), roles from SpbProCar.roles() (the role detection the edit brain uses),
    // the eye calls the editor's toggleLayerVisible(), thumbnails come from the editor's SPBLayerThumbnail.draw(). Nothing about layers is decided here.
    var ROLE_CHIP = { 'numbers': 'Numbers', 'sponsors': 'Sponsors', 'decals / logos': 'Logos', 'tape / stripes': 'Tape', 'body paint': 'Body', 'other art': 'Art' };
    var _lastLayers = '', _lock = null, _sug = null, _thumbs = (typeof Map === 'function') ? new Map() : null, _lastSent = '';
    function layersHtml() {
        return '<aside class="spb-cs-layers" id="spbCsLayers" hidden aria-label="Layers"><div class="spb-cs-lhead"><span>Layers <i id="spbCsLCount"></i></span></div>' +
            '<div class="spb-cs-lwork" id="spbCsLWork" hidden></div>' +
            '<div class="spb-cs-lhint">Lock a layer and every request works only inside it.</div><div class="spb-cs-llist" id="spbCsLList"></div></aside>';
    }
    function layersArr() { try { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : []; } catch (e) { return []; } }
    function roleChip(role) { var r = String(role || ''); if (/^template/.test(r)) return 'Template'; return ROLE_CHIP[r] || ''; }
    function syncLayers() {
        var bar = $('spbCsLayers'), list = $('spbCsLList'); if (!bar || !list) return;
        var ls = layersArr().filter(function (l) { return l && l.id != null; });
        if (_lock && !ls.some(function (l) { return String(l.id) === _lock.id; })) { _lock = null; syncLock(); }
        var sig = ls.map(function (l) { return l.id + ':' + l.name + ':' + (l.visible === false ? 0 : 1) + ':' + (l.img ? 1 : 0); }).join('|') + '#' + (_lock ? _lock.id : '');
        if (sig === _lastLayers) return; _lastLayers = sig;
        bar.hidden = !ls.length; document.body.classList.toggle('spb-cs-has-layers', !!ls.length);
        if (!ls.length) { list.innerHTML = ''; return; }
        var rm = {}; try { (window.SpbProCar && window.SpbProCar.roles ? window.SpbProCar.roles() : []).forEach(function (r) { rm[r.id] = r.role; }); } catch (e) {}
        var cnt = $('spbCsLCount'); if (cnt) cnt.textContent = ls.length;
        var h = '';
        for (var i = ls.length - 1; i >= 0; i--) {
            var l = ls[i], vis = l.visible !== false, lk = !!(_lock && _lock.id === String(l.id)), rc = roleChip(rm[l.id]);
            h += '<div class="spb-cs-lrow' + (vis ? '' : ' off') + (lk ? ' locked' : '') + '" data-cs-lid="' + esc(l.id) + '">' +
                '<button type="button" class="spb-cs-leye" data-cs-lay="eye" aria-pressed="' + vis + '" title="' + (vis ? 'Hide' : 'Show') + ' this layer (same as the eye in the full editor)">' + (vis ? '&#128065;' : '&middot;') + '</button>' +
                '<canvas class="spb-cs-lthumb" width="28" height="28" data-cs-lt="' + esc(l.id) + '"></canvas>' +
                '<span class="spb-cs-lmeta"><span class="spb-cs-lname" title="' + esc(l.name) + '">' + esc(l.name || 'Layer') + '</span>' + (rc ? '<span class="spb-cs-lrole r-' + rc.toLowerCase() + '">' + rc + '</span>' : '') + '</span>' +
                '<button type="button" class="spb-cs-llock" data-cs-lay="lock" title="' + (lk ? 'Unlock: requests work on the whole car again' : 'Lock the copilot to this layer: every request you type works only inside it') + '">' + (lk ? '&#128274; Locked' : 'Lock') + '</button></div>';
        }
        list.innerHTML = h;
        if (_thumbs && window.SPBLayerThumbnail && typeof window.SPBLayerThumbnail.draw === 'function') {
            ls.forEach(function (l) { var cv = list.querySelector('canvas[data-cs-lt="' + String(l.id).replace(/["\\]/g, '') + '"]'); if (!cv || !l.img) return; var key = ''; try { key = (typeof _layerThumbKey === 'function' ? _layerThumbKey(l) : '') + '|cs28'; } catch (e) {} try { window.SPBLayerThumbnail.draw(l, cv, _thumbs, 28, key); } catch (e2) {} });
        }
    }
    function setLock(id) {
        if (id == null || id === '') { _lock = null; }
        else {
            var l = layersArr().filter(function (x) { return x && String(x.id) === String(id); })[0];
            if (!l) return; _lock = (_lock && _lock.id === String(l.id)) ? null : { id: String(l.id), name: String(l.name || '').trim() };
        }
        _sug = null; _lastLayers = ''; syncLayers(); syncLock();
        if (_lock) { try { var inp = document.querySelector('#spbProAI .spb-pai-input'); if (inp && !inp.disabled) inp.focus(); } catch (e) {} }
    }
    var NO_PREFIX = /^\s*(undo|redo|start over|reset|help|yes|no|ok(ay)?|cancel|stop|thanks?( you)?|surprise me|check my setup|use:? .*|\d+)\s*[.!?]?\s*$/i;
    function lockPrefix(t) {
        t = String(t || ''); if (!_lock || !_lock.name || !t.trim()) return t;
        if (/^\s*\{/.test(t) || NO_PREFIX.test(t)) return t;
        var low = t.toLowerCase(), nm = _lock.name.toLowerCase();
        if (low.indexOf(nm + ' layer') !== -1 || low.indexOf('in the ' + nm) !== -1) return t;
        return 'in the ' + _lock.name + ' layer, ' + t.trim();
    }
    // "the chip is also offered as a suggestion when the user names a layer": a layer name, or "<word> layer", in an unlocked request
    function namedLayer(t) {
        var low = ' ' + String(t || '').toLowerCase().replace(/[^a-z0-9#]+/g, ' ') + ' ', best = null;
        layersArr().forEach(function (l) {
            var n = String((l && l.name) || '').toLowerCase().replace(/[^a-z0-9#]+/g, ' ').trim(); if (n.length < 3 || /^layer \d+$/.test(n)) return;
            if (low.indexOf(' ' + n + ' layer ') !== -1 || (n.split(' ').length > 1 && low.indexOf(' ' + n + ' ') !== -1)) { if (!best || n.length > best.n.length) best = { id: String(l.id), name: String(l.name).trim(), n: n }; }
        });
        return best;
    }
    function beforeSend(inp) {
        if (!_open || !inp) return;
        var t = String(inp.value || ''); if (!t.trim()) return;
        try { if (window.spbProAI && window.spbProAI.busy && window.spbProAI.busy()) return; } catch (e) {}
        if (_lock) { var p = lockPrefix(t); if (p !== t) inp.value = p; _lastSent = p; return; }
        _lastSent = t; var nl = namedLayer(t), ok = nl && (!window.spbProAI || !window.spbProAI.lockWorthy || window.spbProAI.lockWorthy(t)); _sug = ok ? nl : null; syncLock();          // ROUTER-FIX 2026-10-04 item 5: the lock chip only for an instruction about that layer (spbProAI.lockWorthy = false for complaints / questions / help asks); resetting _sug on every send makes it vanish after the next message
    }
    function syncLock() {
        var P = $('spbProAI'), chip = $('spbCsLockChip');
        if (P && (!chip || chip.parentNode !== P)) {
            if (!chip) {
                chip = document.createElement('div'); chip.id = 'spbCsLockChip'; chip.className = 'spb-cs-lockchip'; chip.hidden = true;
                chip.addEventListener('click', function (ev) { var b = ev.target && ev.target.closest ? ev.target.closest('[data-cs-lk]') : null; if (!b) return; var k = b.getAttribute('data-cs-lk'); if (k === 'clear') setLock(null); else if (k === 'take' && _sug) setLock(_sug.id); else if (k === 'nosug') { _sug = null; syncLock(); } });
            }
            var bar = P.querySelector('.spb-pai-bar'); if (bar) P.insertBefore(chip, bar); else P.appendChild(chip);
        }
        var html = '', cls = '';
        if (_lock) { html = '<span class="spb-cs-lk-ic">&#128274;</span><span class="spb-cs-lk-t">Working in: <b>' + esc(_lock.name) + '</b> <i>every request stays inside this layer</i></span><button type="button" class="spb-cs-lk-x" data-cs-lk="clear" title="Stop working in this layer">&times;</button>'; cls = 'on'; }
        else if (_sug) { html = '<span class="spb-cs-lk-t">Keep working in the <b>' + esc(_sug.name) + '</b> layer?</span><button type="button" class="spb-cs-btn" data-cs-lk="take">&#128274; Lock to it</button><button type="button" class="spb-cs-lk-x" data-cs-lk="nosug" title="No thanks">&times;</button>'; cls = 'sug'; }
        if (chip) { if (chip._h !== html) { chip._h = html; chip.innerHTML = html; } chip.className = 'spb-cs-lockchip ' + cls; chip.hidden = !html; }
        var w = $('spbCsLWork'); if (w) { var wh = _lock ? 'Working in: <b>' + esc(_lock.name) + '</b><button type="button" class="spb-cs-lk-x" data-cs-act="unlock" title="Stop working in this layer">&times;</button>' : ''; if (w._h !== wh) { w._h = wh; w.innerHTML = wh; } w.hidden = !_lock; }
    }

    // ---- before / after slider
    var _cmp = false, _cmpX = 0.5;
    function toggleCompare() {
        _cmp = !_cmp; var c = $('spbCsCmp'); if (!c) return;
        if (_cmp) { var vs = versions(), act = -1, i; for (i = 0; i < vs.length; i++) if (vs[i].active) act = i; var before = (act > 0 ? vs[act - 1] : vs[0]); if (!before || !before.img) { _cmp = false; return; } $('spbCsBefore').src = before.img; }
        c.hidden = !_cmp; setCmp(_cmpX);
        var b = _el.querySelector('[data-cs-act="compare"]'); if (b) b.classList.toggle('on', _cmp);
    }
    function setCmp(x) {
        _cmpX = Math.max(0.03, Math.min(0.97, x)); var c = $('spbCsCmp'), line = $('spbCsCmpLine'), bf = $('spbCsBefore'); if (!c) return;
        if (bf) bf.style.clipPath = 'inset(0 ' + ((1 - _cmpX) * 100) + '% 0 0)'; if (line) line.style.left = (_cmpX * 100) + '%';
    }
    function wireCompare() {
        var c = $('spbCsCmp'); if (!c || c._wired) return; c._wired = true; var drag = false;
        function at(ev) { var r = c.getBoundingClientRect(); setCmp((ev.clientX - r.left) / r.width); }
        c.addEventListener('mousedown', function (ev) { drag = true; at(ev); ev.preventDefault(); });
        window.addEventListener('mousemove', function (ev) { if (drag) at(ev); });
        window.addEventListener('mouseup', function () { drag = false; });
    }
    function versions() { try { return window.spbProAI && window.spbProAI.versions ? window.spbProAI.versions() : []; } catch (e) { return []; } }
    var _lastFilm = '';
    function syncFilm() {
        var vs = versions(), sig = vs.map(function (v) { return v.id + (v.active ? '*' : '') + (v.thumb ? 't' : ''); }).join('|'); if (sig === _lastFilm) return; _lastFilm = sig;
        var f = $('spbCsFilm'); if (!f) return;
        if (vs.length < 2) { f.innerHTML = '<span class="spb-cs-chip dim">your first change will appear here: click any version to go back to it</span>'; return; }
        f.innerHTML = vs.map(function (v, i) { return '<button type="button" class="spb-cs-ver' + (v.active ? ' on' : '') + '" data-cs-ver="' + esc(v.id) + '" title="' + esc(v.label) + '">' + (v.thumb ? '<img alt="" src="' + v.thumb + '">' : '<span class="spb-cs-ver-ph"></span>') + '<span>' + esc(i === 0 ? 'Original' : (i + '. ' + v.label)) + '</span></button>'; }).join('');
        var on = f.querySelector('.spb-cs-ver.on'); if (on && on.scrollIntoView) { try { on.scrollIntoView({ block: 'nearest', inline: 'nearest' }); } catch (e) {} }
    }
    function pill() {
        var b = $('spbModeChatBtn'), pro = $('spbModeProBtn');
        if (b) { b.classList.toggle('on', _open); b.setAttribute('aria-pressed', _open ? 'true' : 'false'); }
        if (pro) { pro.classList.toggle('on', !_open); pro.setAttribute('aria-pressed', _open ? 'false' : 'true'); }
    }
    function open() {
        build(); if (_open) return; _open = true; _el.hidden = false; document.body.classList.add('spb-chat-studio'); lsSet(KEY, '1');
        try { if (window.spbEasy && window.spbEasy._internals && window.spbEasy._internals().isActive()) window.spbEasy.exit(); } catch (e) {}
        try { if (window.spbProAI) window.spbProAI.open(); } catch (e2) {}
        try { if (window.SpbProCar) window.SpbProCar.ensure(false).then(function () { try { if (window.spbProAI) window.spbProAI.refresh(); } catch (e5) {} }); } catch (e6) {}
        try { if (typeof triggerPreviewRender === 'function' && !($('livePreviewImg') && $('livePreviewImg').naturalWidth > 32)) triggerPreviewRender(); } catch (e3) {}
        sync(true); pill(); if (_timer) clearInterval(_timer); _timer = setInterval(function () { sync(false); }, 700);
        try { window.dispatchEvent(new CustomEvent('spb:chat-studio', { detail: { open: true } })); } catch (e4) {}
    }
    function close() { stopDemo();
        if (!_open) return; _open = false; if (_el) _el.hidden = true; document.body.classList.remove('spb-chat-studio'); lsSet(KEY, '0');
        if (_timer) { clearInterval(_timer); _timer = null; }
        try { var P = $('spbProAI'); if (P) { P.style.removeProperty('left'); } } catch (e) {}
        pill(); try { window.dispatchEvent(new CustomEvent('spb:chat-studio', { detail: { open: false } })); } catch (e2) {}
    }
    function toggle() { if (_open) close(); else open(); }
    function boot() {
        if (!document.body) { setTimeout(boot, 400); return; }
        pill();
        var first = !!window.__spbFirstRun, saved = lsGet(KEY);
        window.addEventListener('spb:first-run', function () { setTimeout(open, 400); });
        if (first || saved === '1') setTimeout(open, 1200);
    }
    window.SpbChatStudio = { demoLog: function () { return _demoLog.slice(); }, open: open, close: close, toggle: toggle, isOpen: function () { return _open; }, view: setView,
        currentView: function () { return _view; }, lock: function (id) { setLock(id == null ? null : id); return _lock ? _lock.name : null; }, locked: function () { return _lock ? { id: _lock.id, name: _lock.name } : null; }, prefix: lockPrefix, lastSent: function () { return _lastSent; } };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 1800); }); else setTimeout(boot, 1800);
})();
