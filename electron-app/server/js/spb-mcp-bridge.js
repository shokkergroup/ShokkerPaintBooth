/* ============================================================================
   SPB MCP BRIDGE (page side)  (SPB-AI 2026-09-30)
   Lets Claude or Codex, using the buyer's own assistant plan, drive Shokker Paint Booth through the local MCP server in /mcp.
   This file long-polls the local server (/api/mcp/poll), runs each call with window.spbProAI.mcpCall (the same code the in-app copilot uses) and posts the result back.
   OFF by default: the buyer turns it on in the AI panel settings.  ES5 only.
   ========================================================================== */
(function () {
    'use strict';
    var BASE = window.SPB_AI_BASE || '', enabled = false, running = false, last = null, listeners = [], stats = { calls: 0, lastTool: '', connected: false };
    // MCPSCEN 2026-10-05: ONE page owns the bridge (see mcp_bridge_routes.mcp_poll). This page claims it when it opens or when the buyer switches the bridge on;
    // a page superseded by a newer window stops polling and only takes over again once the owner has gone quiet.
    var PAGE = 'p' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36), claimNext = true;
    function api(path, opt) { return fetch(BASE + path, opt).then(function (r) { return r.json(); }); }
    function emit() { listeners.forEach(function (f) { try { f(stats, enabled); } catch (e) {} }); }
    function post(id, res) {
        res = res || {};
        return fetch(BASE + '/api/mcp/result', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: id, ok: !!res.ok, result: res.ok ? Object.assign({}, res.result, res.images && res.images.length ? { images: res.images } : {}) : undefined, error: res.ok ? undefined : String(res.error || 'failed') }) }).catch(function () {});
    }
    function handle(call) {
        stats.calls++; stats.lastTool = call.tool; stats.connected = true; emit();
        var P = window.spbProAI, run;
        try { run = (P && P.mcpCall) ? P.mcpCall(call.tool, call.args || {}) : Promise.resolve({ ok: false, error: 'the Shokker AI panel is not loaded (open Pro mode)' }); } catch (e) { run = Promise.resolve({ ok: false, error: String(e && e.message || e) }); }
        return Promise.resolve(run).then(function (res) { return post(call.id, res); }, function (e) { return post(call.id, { ok: false, error: String(e && e.message || e) }); });
    }
    function loop() {
        if (!enabled || !running) { running = false; return; }
        var q = '/api/mcp/poll?wait=25&page=' + PAGE + (claimNext ? '&claim=1' : ''); claimNext = false;
        fetch(BASE + q).then(function (r) { return r.json(); }).then(function (j) {
            if (j && j.superseded) { running = false; stats.connected = false; stats.superseded = true; emit(); return; }
            if (stats.superseded) { stats.superseded = false; emit(); }
            if (j && j.call) return handle(j.call).then(loop);
            if (j && j.enabled === false) { enabled = false; running = false; stats.connected = false; emit(); return; }
            loop();
        }).catch(function () { setTimeout(loop, 3000); });
    }
    function start() { if (running || !enabled) return; running = true; loop(); }
    function refresh() {
        return api('/api/mcp/status').then(function (s) { last = s; enabled = !!s.enabled; stats.connected = !!s.connected; stats.calls = s.calls || stats.calls; if (enabled) start(); emit(); return s; }, function () { return null; });
    }
    function setEnabled(on) { if (!on && window.SpbAiLease) window.SpbAiLease.release(); if (on) claimNext = true;
        return api('/api/mcp/enable', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: !!on }) }).then(function (s) { last = s; enabled = !!s.enabled; if (enabled) start(); emit(); return s; });
    }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    function copy(text, btn) { try { navigator.clipboard.writeText(text); if (btn) { var o = btn.textContent; btn.textContent = 'Copied'; setTimeout(function () { btn.textContent = o; }, 1500); } } catch (e) {} }
    // the settings block shown under the AI settings
    function panel() {
        var box = document.createElement('div'); box.className = 'spb-pai-mcp'; box.style.cssText = 'margin-top:12px;padding-top:10px;border-top:1px solid rgba(255,255,255,0.12);font-size:12px;line-height:1.45';
        function draw() {
            var dir = (last && last.mcpDir) || '(the "mcp" folder of the app)', node = dir.replace(/\\/g, '/') + '/server/index.js';
            var cmd = 'claude mcp add shokker-paint-booth -- node "' + node + '"', cfg = JSON.stringify({ mcpServers: { 'shokker-paint-booth': { command: 'node', args: [node] } } }, null, 2);
            box.innerHTML = '<div style="font-weight:700;margin-bottom:4px">\u2461 Chat from Claude or ChatGPT <span style="font-weight:400;opacity:.7">\u2014 they design in Shokker for you, using your own plan (no key)</span></div><div class="spb-pai-meta" style="margin:0 0 6px">You type in the <b>Claude</b> or <b>ChatGPT/Codex</b> app, not here. Switch this on, install Shokker in that app once, then tell it what to paint. Shokker\u2019s Copilot model setting does not apply to this way: the model is chosen inside Claude / ChatGPT.</div>' +
                '<label style="display:flex;gap:8px;align-items:center;cursor:pointer"><input type="checkbox" data-mcp="toggle"' + (enabled ? ' checked' : '') + '> Let an AI assistant (Claude or ChatGPT/Codex) control Shokker Paint Booth</label>' +
                '<div class="spb-pai-meta" style="margin:6px 0">' + (enabled ? (stats.superseded ? '○ Another Shokker window has the AI connection (switch this off and on to move it here)' : stats.connected ? '● Connected' : '○ Waiting for your AI assistant…') + (stats.calls ? ' · ' + stats.calls + ' request' + (stats.calls > 1 ? 's' : '') + (stats.lastTool ? ' (last: ' + esc(stats.lastTool) + ')' : '') : '') : 'Off. Your AI assistant cannot touch your paint until you switch this on. Every AI change shows up in this panel with an Undo button.') + '</div>' +
                '<div class="spb-pai-meta" style="margin:6px 0"><b>Claude model?</b> You pick it in Claude itself: the model menu in the Claude Desktop chat box (or <code>/model</code> in Claude Code). <b>Sonnet 5.5</b> is the economical everyday choice; <b>Opus 5.5</b> and <b>Fable 5.1</b> design a little better and use more of your plan. The built-in brain inside Shokker needs no model at all.</div>' +
                '<div style="margin:6px 0"><button type="button" class="spb-pai-act" data-mcp="install" title="Opens the Shokker extension in Claude Desktop: you confirm the install there">Install in Claude Desktop</button> <span class="spb-pai-meta" data-mcp="instmsg"></span></div><details><summary style="cursor:pointer">Other ways to connect Claude</summary><div style="margin-top:6px"><b>Claude Desktop:</b> Settings → Extensions → Advanced → Install Extension… and choose <code>shokker-paint-booth.mcpb</code> from the app\'s mcp folder (or paste the config below into <i>claude_desktop_config.json</i> and restart Claude).<br><b>Claude Code:</b> run the command below once.<br>Then ask Claude: “Using Shokker Paint Booth, give me a Gulf-style livery.”</div>' +
                '<div style="margin-top:6px"><button type="button" class="spb-pai-act" data-mcp="copycmd">Copy Claude Code command</button> <button type="button" class="spb-pai-act" data-mcp="copycfg">Copy Claude Desktop config</button></div>' +
                '<div class="spb-pai-meta" style="margin-top:4px;word-break:break-all">' + esc(dir) + '</div></details>' +
                '<div data-mcp="carmap" style="margin-top:10px;font-weight:700">Car map</div><div class="spb-pai-meta">Parts you showed the copilot on this car. Share them to help every Shokker owner get this car recognised automatically.</div>' +
                '<div style="margin-top:4px"><button type="button" class="spb-pai-act" data-mcp="mapcopy">Copy my car map</button> <button type="button" class="spb-pai-act" data-mcp="mapdl">Save as file</button> <button type="button" class="spb-pai-act" data-mcp="mapload">Load a car map…</button></div><div class="spb-pai-meta" data-mcp="mapmsg"></div>';
            if (window.SpbCodexSetup) {
                var codexPanel = window.SpbCodexSetup.panel(); box.insertBefore(codexPanel, box.querySelector('[data-mcp="carmap"]'));
                var connect = document.createElement('button'); connect.type = 'button'; connect.className = 'spb-pai-act'; connect.textContent = 'Connect Codex';
                connect.onclick = function () { codexPanel.open = !codexPanel.open; };
                var claudeInstall = box.querySelector('[data-mcp="install"]'); claudeInstall.parentNode.insertBefore(connect, claudeInstall.nextSibling);
            }
            var take = document.createElement('button'); take.type = 'button'; take.className = 'spb-pai-act'; take.textContent = 'Take over in SPB'; take.onclick = function () { if (!window.SpbAiLease || window.SpbAiLease.takeover()) take.textContent = 'SPB has control'; else take.textContent = 'Wait for the current call to finish'; }; box.appendChild(take);
            var msg = box.querySelector('[data-mcp="mapmsg"]');
            function say(t) { if (msg) msg.textContent = t; }
            var m1 = box.querySelector('[data-mcp="mapcopy"]'); if (m1) m1.onclick = function () { var o = window.SpbProCar && window.SpbProCar.exportTaught(); if (!o) return say('Nothing taught yet on this car: ask for a design, then show the parts when asked.'); copy(JSON.stringify(o, null, 1), m1); say('Copied. Paste it in a message to Shokker support or keep it as a backup.'); };
            var m2 = box.querySelector('[data-mcp="mapdl"]'); if (m2) m2.onclick = function () { var o = window.SpbProCar && window.SpbProCar.exportTaught(); if (!o) return say('Nothing taught yet on this car.'); try { var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(o, null, 1)], { type: 'application/json' })); a.download = 'my-car-map.json'; document.body.appendChild(a); a.click(); a.remove(); say('Saved my-car-map.json to your Downloads.'); } catch (e) { say('Could not save the file.'); } };
            var m3 = box.querySelector('[data-mcp="mapload"]'); if (m3) m3.onclick = function () { var inp = document.createElement('input'); inp.type = 'file'; inp.accept = '.json,application/json'; inp.onchange = function () { var f = inp.files && inp.files[0]; if (!f) return; var rd = new FileReader(); rd.onload = function () { try { var n = window.SpbProCar.importTaught(JSON.parse(String(rd.result))); say(n ? 'Loaded ' + n + ' parts for this car.' : 'That file has no usable parts for this car.'); } catch (e) { say('That is not a Shokker car map file.'); } }; rd.readAsText(f); }; inp.click(); };
            var t = box.querySelector('[data-mcp="toggle"]'); if (t) t.onchange = function () { setEnabled(t.checked); };
            var bi = box.querySelector('[data-mcp="install"]'), bm = box.querySelector('[data-mcp="instmsg"]'); if (bi) bi.onclick = function () { if (bm) bm.textContent = 'Opening…'; var go = function () { api('/api/mcp/open-bundle', { method: 'POST' }).then(function (j) { if (bm) bm.textContent = j && j.ok ? 'Claude Desktop should now ask you to confirm the install. Then switch the box above ON.' : ((j && j.message) || 'Could not open it.'); }, function () { if (bm) bm.textContent = 'Could not reach the Shokker server.'; }); }; if (!enabled) setEnabled(true).then(go, go); else go(); };
            var c1 = box.querySelector('[data-mcp="copycmd"]'); if (c1) c1.onclick = function () { copy(cmd, c1); };
            var c2 = box.querySelector('[data-mcp="copycfg"]'); if (c2) c2.onclick = function () { copy(cfg, c2); };
        }
        listeners.push(function () { if (box.isConnected) draw(); });
        refresh().then(draw); draw();
        return box;
    }
    window.SpbMcpBridge = { refresh: refresh, setEnabled: setEnabled, panel: panel, stats: function () { return { enabled: enabled, calls: stats.calls, lastTool: stats.lastTool, connected: stats.connected }; } };
    // start polling if the buyer enabled the bridge earlier; re-check now and then (cheap local call)
    function boot() { refresh(); setInterval(function () { if (!running) refresh(); }, 60000); }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else setTimeout(boot, 1500);
})();
