// ============================================================================
// SPB EXPERIMENTS LOADER (2026-07-04, gauntlet integration)
// ----------------------------------------------------------------------------
// Owner brief: "5 new features... make them EXPERIMENTAL that we can take out
// if I don't like them." Every experiment is a self-contained module in
// js/experiments/spb-exp-<id>.js that registers {id, name, pitch, enable,
// disable} into window.SPB_EXPERIMENTS and is a NO-OP until enable() runs.
//
// This loader adds a "🧪 EXPERIMENTS" section to the Settings dropdown with a
// toggle per experiment (default OFF, persisted in localStorage), and calls
// enable()/disable() accordingly. Removing ANY experiment = delete its script
// tag + file. Removing ALL of it = delete the experiments script tags.
// ============================================================================
(function () {
    'use strict';

    var LS_KEY = 'spb_experiments_enabled';

    function enabledIds() {
        try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]') || []; }
        catch (e) { return []; }
    }
    function saveEnabled(ids) {
        try { localStorage.setItem(LS_KEY, JSON.stringify(ids)); } catch (e) {}
    }
    function registry() {
        return (typeof window.SPB_EXPERIMENTS !== 'undefined' && Array.isArray(window.SPB_EXPERIMENTS))
            ? window.SPB_EXPERIMENTS : [];
    }

    function setExperiment(id, on) {
        var exp = registry().find(function (e) { return e && e.id === id; });
        if (!exp) return false;
        try {
            if (on) exp.enable(); else exp.disable();
        } catch (err) {
            console.error('[experiments] ' + id + ' ' + (on ? 'enable' : 'disable') + ' failed:', err);
            if (typeof showToast === 'function') showToast('Experiment "' + (exp.name || id) + '" failed to ' + (on ? 'start' : 'stop') + ' — see console', true);
            return false;
        }
        var ids = enabledIds().filter(function (x) { return x !== id; });
        if (on) ids.push(id);
        saveEnabled(ids);
        return true;
    }
    window.spbSetExperiment = setExperiment;

    function buildSection() {
        var dropdown = document.getElementById('settingsDropdown');
        if (!dropdown || document.getElementById('spbExperimentsSection')) return;
        var on = enabledIds();
        var section = document.createElement('section');
        section.className = 'settings-section';
        section.id = 'spbExperimentsSection';
        var cards = registry().map(function (exp) {
            var checked = on.indexOf(exp.id) !== -1 ? ' checked' : '';
            return '<label style="display:flex; align-items:flex-start; gap:8px; padding:7px 8px; border:1px solid rgba(157,124,255,0.35); border-radius:7px; background:rgba(157,124,255,0.06); cursor:pointer;">' +
                '<input type="checkbox" data-exp="' + exp.id + '"' + checked + ' style="margin-top:2px;">' +
                '<span style="min-width:0;"><span style="display:block; font-size:11px; font-weight:800; color:#c9b8ff;">' + exp.name + '</span>' +
                '<span style="display:block; font-size:9px; color:var(--text-dim); line-height:1.35; margin-top:1px;">' + (exp.pitch || '') + '</span></span></label>';
        }).join('');
        section.innerHTML =
            '<div class="settings-section-title" style="font-weight:800; letter-spacing:0.5px;">🧪 EXPERIMENTS — try them, keep what you love</div>' +
            '<div id="spbExperimentalMenu" style="display:grid; grid-template-columns:1fr; gap:6px; margin-top:4px;">' + cards + '</div>' +
            '<div style="font-size:8px; color:var(--text-dim); margin-top:4px; opacity:0.8;">Each one is fully removable. Toggles stick across sessions.</div>';
        dropdown.appendChild(section);
        section.addEventListener('change', function (ev) {
            var t = ev.target;
            if (t && t.dataset && t.dataset.exp) {
                var ok = setExperiment(t.dataset.exp, t.checked);
                if (!ok) t.checked = !t.checked;
            }
        });
    }

    function boot() {
        // Re-enable persisted experiments — each isolated so one failure can't
        // break boot or its siblings.
        enabledIds().forEach(function (id) {
            var exp = registry().find(function (e) { return e && e.id === id; });
            if (!exp) return;
            try { exp.enable(); }
            catch (err) { console.error('[experiments] boot enable failed for ' + id + ':', err); }
        });
        buildSection();
        // The settings dropdown may be (re)built lazily — same pattern as LOOKS.
        document.addEventListener('click', function () { setTimeout(buildSection, 80); }, true);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 500); });
    } else {
        setTimeout(boot, 500);
    }
})();
