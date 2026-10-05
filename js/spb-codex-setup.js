/* SPB-AI 2026-10-01: subscription MCP setup and model choice, with review before config append. */
(function () {
    'use strict';
    function panel() {
        var box = document.createElement('details');
        box.innerHTML = '<summary style="cursor:pointer;margin:8px 0">Connect ChatGPT / Codex</summary>' +
            '<p>Use your ChatGPT plan by chatting in Codex while SPB stays open. Sign into Codex with ChatGPT; your plan limits apply.</p>' +
            '<p><b>Choose your model in Codex:</b> use the model picker beneath the composer, or type <code>/model</code> in the CLI. Available models depend on your account. SPB uses whichever model you choose there.</p>' +
            '<p data-codex="status">Loading setup…</p><pre data-codex="config" style="white-space:pre-wrap;word-break:break-all;max-height:220px;overflow:auto"></pre>' +
            '<button type="button" class="spb-pai-act" data-codex="install" disabled>Add SPB to Codex settings</button> ' +
            '<button type="button" class="spb-pai-act" data-codex="copy" disabled>Copy config</button>' +
            '<div data-codex="review" hidden><p>Add the shown connection to the settings file above? Your other settings and model selection will be preserved.</p><button type="button" class="spb-pai-act" data-codex="confirm">Confirm add</button> <button type="button" class="spb-pai-act" data-codex="cancel">Cancel</button></div>' +
            '<p>The button adds only the shown SPB entry, with a 200-second tool timeout. Existing entries are preserved. Restart Codex afterward, switch the AI bridge on above, then ask: “Using Shokker Paint Booth, call spb_status.”</p>' +
            '<p>If Node.js is missing, install it from <a href="https://nodejs.org/" target="_blank" rel="noopener">nodejs.org</a>, then restart SPB.</p>';
        var status = box.querySelector('[data-codex="status"]'), config = box.querySelector('[data-codex="config"]'), install = box.querySelector('[data-codex="install"]'), copy = box.querySelector('[data-codex="copy"]'), payload;
        var url = (window.SPB_AI_BASE || '') + '/api/mcp/codex-setup';
        fetch(url).then(function (r) { return r.json(); }).then(function (p) {
            payload = p; config.textContent = p.config || ''; status.textContent = p.ready ? 'Settings file: ' + p.configPath : (p.message || 'Setup unavailable.') + (!p.nodeFound ? ' Node.js was not found.' : '');
            install.disabled = !p.ready; copy.disabled = !p.config;
        }).catch(function () { status.textContent = 'Restart the SPB server to load Codex setup, then reopen these settings.'; });
        install.onclick = function () {
            if (payload) box.querySelector('[data-codex="review"]').hidden = false;
        };
        box.querySelector('[data-codex="cancel"]').onclick = function () { box.querySelector('[data-codex="review"]').hidden = true; };
        box.querySelector('[data-codex="confirm"]').onclick = function () {
            if (!payload) return;
            box.querySelector('[data-codex="review"]').hidden = true;
            install.disabled = true;
            fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirmed: true }) }).then(function (r) { return r.json(); }).then(function (p) { status.textContent = p.message; install.disabled = false; }).catch(function () { status.textContent = 'Could not complete setup. Copy the config and add it manually.'; install.disabled = false; });
        };
        copy.onclick = function () {
            if (!navigator.clipboard) { config.focus(); status.textContent = 'Select and copy the config above.'; return; }
            navigator.clipboard.writeText(payload.config).then(function () { status.textContent = 'Copied. Add it to ' + payload.configPath + ', preserving other sections; restart Codex.'; }).catch(function () { status.textContent = 'Select and copy the config above.'; });
        };
        return box;
    }
    window.SpbCodexSetup = { panel: panel };
})();
