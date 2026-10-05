/**
 * SPB EXPERIMENT — Pit Lane Live (auto-deploy mirror to the sim)
 * File: js/experiments/spb-exp-pit-lane-live.js  (NEW file — zero edits to existing repo files)
 *
 * WHAT IT DOES
 *   Adds a "LIVE → SIM" toggle to the render bar (#renderFloat .render-float-actions,
 *   paint-booth-v2.html:2393). Pick an iRacing car folder once (dropdown fed by
 *   GET /iracing-cars — server_routes/iracing_utility_routes.py:27). While armed, every
 *   successful FULL render auto-POSTs the fresh job_id to /deploy-to-iracing
 *   (server_routes/iracing_utility_routes.py:158), debounced, with a status pill
 *   ("✓ 14:32" / "✗ failed"). iRacing hot-reloads changed paint TGAs in solo/test
 *   sessions, so the sim becomes the true 3D preview — SPB itself never builds one
 *   (identity rule intact).
 *
 * HOW IT HOOKS RENDERS (no repo edits)
 *   doRender() calls the global showRenderResults(result) exactly once per successful
 *   full render (paint-booth-5-api-render.js:3346 → :3492) and result.job_id is the
 *   deployable job (:3500). showRenderResults is a top-level function declaration in a
 *   classic script, i.e. a writable window property — so this module wraps
 *   window.showRenderResults with a passthrough that fires our deploy hook afterwards.
 *   Live-preview renders NEVER call showRenderResults, so preview-only work is skipped
 *   by construction (plus a job_id guard).
 *
 * CONTRACT
 *   - No-op until enable() is called via the window.SPB_EXPERIMENTS registry.
 *   - disable() removes all DOM/listeners/timers and restores showRenderResults.
 *   - Every app global is touched defensively (typeof guards): ShokkerAPI,
 *     showToast, lastRenderedJobId, showRenderResults.
 */
(function () {
    'use strict';

    var EXP_ID = 'pit-lane-live';
    var LOG = '[pit-lane-live]';
    var LS_CAR_KEY = 'spbExpPitLaneLive.carFolder';
    var DEBOUNCE_MS = 400;          // coalesce rapid re-renders so we never race the file copy
    var FETCH_TIMEOUT_MS = 15000;   // mirrors API_TIMEOUT_GENERAL_MS (paint-booth-5-api-render.js:574)
    var WRAP_POLL_MS = 750;         // if showRenderResults isn't defined yet (script order), retry
    var WRAP_POLL_MAX = 40;

    // ---------------------------------------------------------------- state
    var S = {
        enabled: false,          // enable() has run
        live: false,             // toggle armed
        carFolder: '',           // chosen iRacing car folder name
        busy: false,             // a deploy POST is in flight
        pendingJobId: null,      // newest job that arrived while busy
        debounceTimer: null,
        mountTimer: null,
        wrapPollTimer: null,
        wrapPollTries: 0,
        wrapInstalled: false,
        wrapper: null,
        origShowRenderResults: null,
        els: { wrap: null, toggle: null, caret: null, pill: null, popover: null },
        docClick: null,
        docKeydown: null,
    };

    // ------------------------------------------------------- tiny defensive helpers
    function apiBase() {
        try {
            if (typeof ShokkerAPI !== 'undefined' && ShokkerAPI && ShokkerAPI.baseUrl) return ShokkerAPI.baseUrl;
        } catch (e) { /* TDZ / not defined */ }
        if (typeof window.ShokkerAPI === 'object' && window.ShokkerAPI && window.ShokkerAPI.baseUrl) return window.ShokkerAPI.baseUrl;
        return ''; // same-origin fallback
    }

    function apiOnline() {
        try {
            if (typeof ShokkerAPI !== 'undefined' && ShokkerAPI && typeof ShokkerAPI.online !== 'undefined') return ShokkerAPI.online !== false;
        } catch (e) { /* ignore */ }
        return true; // unknown → attempt; fetch error will surface in the pill
    }

    function toast(msg, isError) {
        try { if (typeof showToast === 'function') { showToast(msg, !!isError); return; } } catch (e) { /* ignore */ }
        try { if (typeof window.showToast === 'function') { window.showToast(msg, !!isError); return; } } catch (e) { /* ignore */ }
        (isError ? console.warn : console.log)(LOG, msg);
    }

    function fetchSignal() {
        try {
            if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') return AbortSignal.timeout(FETCH_TIMEOUT_MS);
        } catch (e) { /* ignore */ }
        return undefined;
    }

    function iracingIdValue() {
        var el = document.getElementById('iracingId'); // header input, read the same way deployToIracing() does (paint-booth-5-api-render.js:5054)
        var v = (el && el.value) ? String(el.value).trim() : '';
        return v || '00000';
    }

    function hhmm(d) {
        var h = String(d.getHours()); if (h.length < 2) h = '0' + h;
        var m = String(d.getMinutes()); if (m.length < 2) m = '0' + m;
        return h + ':' + m;
    }

    function shortCar(name) {
        name = String(name || '');
        return name.length > 16 ? (name.slice(0, 14) + '…') : name;
    }

    function lsGet(key) { try { return window.localStorage ? (localStorage.getItem(key) || '') : ''; } catch (e) { return ''; } }
    function lsSet(key, val) { try { if (window.localStorage) localStorage.setItem(key, val); } catch (e) { /* ignore */ } }

    // ------------------------------------------------------- render hook (wrap showRenderResults)
    function onRenderComplete(result) {
        if (!S.enabled || !S.live) return;
        var jobId = (result && result.job_id) ? String(result.job_id) : '';
        if (!jobId) return; // preview-only paths never reach showRenderResults, but double-guard anyway
        scheduleDeploy(jobId);
    }

    function installWrap() {
        if (S.wrapInstalled) return true;
        var cur = window.showRenderResults;
        if (typeof cur !== 'function') return false;
        if (cur.__spbExpPitLaneLive) { // already ours (e.g. re-enable after a blocked restore)
            S.wrapper = cur;
            S.wrapInstalled = true;
            return true;
        }
        S.origShowRenderResults = cur;
        var wrapper = function (result) {
            try {
                return cur.apply(this, arguments); // original display logic first, untouched
            } finally {
                try { onRenderComplete(result); } catch (e) { console.warn(LOG, 'deploy hook error:', e); }
            }
        };
        wrapper.__spbExpPitLaneLive = true;
        window.showRenderResults = wrapper;
        S.wrapper = wrapper;
        S.wrapInstalled = true;
        console.log(LOG, 'hooked showRenderResults');
        return true;
    }

    function uninstallWrap() {
        stopWrapPoll();
        if (!S.wrapInstalled) return;
        if (window.showRenderResults === S.wrapper && typeof S.origShowRenderResults === 'function') {
            window.showRenderResults = S.origShowRenderResults;
            S.origShowRenderResults = null;
            S.wrapper = null;
            console.log(LOG, 'restored showRenderResults');
        } else {
            // Someone wrapped after us — restoring would sever their chain. Our wrapper is a pure
            // passthrough while S.enabled/S.live are false, so leaving it in place is harmless.
            console.warn(LOG, 'showRenderResults was re-wrapped by another module; leaving passthrough in place');
        }
        S.wrapInstalled = false;
    }

    function startWrapPoll() {
        if (S.wrapPollTimer || S.wrapInstalled) return;
        S.wrapPollTries = 0;
        S.wrapPollTimer = setInterval(function () {
            S.wrapPollTries += 1;
            if (installWrap() || S.wrapPollTries >= WRAP_POLL_MAX) stopWrapPoll();
        }, WRAP_POLL_MS);
    }

    function stopWrapPoll() {
        if (S.wrapPollTimer) { clearInterval(S.wrapPollTimer); S.wrapPollTimer = null; }
    }

    // ------------------------------------------------------- deploy pipeline (debounced + serialized)
    function scheduleDeploy(jobId) {
        if (S.debounceTimer) clearTimeout(S.debounceTimer);
        S.debounceTimer = setTimeout(function () {
            S.debounceTimer = null;
            requestDeploy(jobId);
        }, DEBOUNCE_MS);
    }

    function requestDeploy(jobId) {
        if (!S.live) return;
        if (S.busy) { S.pendingJobId = jobId; return; } // never race the server-side file copy
        doDeploy(jobId);
    }

    function doDeploy(jobId) {
        if (!S.live) return;
        var car = S.carFolder;
        if (!car) { setPill('fail', 'No car selected — click ▾ to pick one'); return; }
        if (!apiOnline()) {
            setPill('fail', 'Server offline — deploy skipped');
            toast('Pit Lane Live: server offline — deploy skipped', true);
            return;
        }
        S.busy = true;
        setPill('busy', 'Copying job ' + jobId + ' → Documents/iRacing/paint/' + car);
        var payload = { job_id: jobId, car_folder: car, iracing_id: iracingIdValue() };
        fetch(apiBase() + '/deploy-to-iracing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: fetchSignal(),
        }).then(function (res) {
            return res.json().catch(function () { return { error: 'Invalid server response (HTTP ' + res.status + ')' }; });
        }).then(function (data) {
            if (data && data.success) {
                var n = Array.isArray(data.deployed) ? data.deployed.length : 0;
                setPill('ok', 'Deployed ' + n + ' file' + (n === 1 ? '' : 's') + ' → ' + (data.target || car) +
                    (data.message ? ' — ' + data.message : '') + ' (iRacing solo/test reloads it; Ctrl+R in-sim forces it)');
            } else {
                var err = (data && data.error) ? String(data.error) : 'deploy failed'; // surface the route's own error string
                setPill('fail', err);
                toast('Pit Lane Live deploy failed: ' + err, true);
            }
        }).catch(function (e) {
            var msg = (e && e.name === 'TimeoutError') ? 'Deploy timed out' : ((e && e.message) ? e.message : 'network error');
            setPill('fail', msg);
            toast('Pit Lane Live deploy failed: ' + msg, true);
        }).finally(function () {
            S.busy = false;
            if (S.pendingJobId) { // newest render wins
                var next = S.pendingJobId;
                S.pendingJobId = null;
                doDeploy(next);
            }
        });
    }

    // ------------------------------------------------------- status pill
    function setPill(kind, detail) {
        var pill = S.els.pill;
        if (!pill) return;
        pill.classList.remove('is-live', 'is-busy', 'is-ok', 'is-fail');
        if (kind === 'off') {
            pill.style.display = 'none';
            pill.textContent = '';
            pill.title = '';
            return;
        }
        pill.style.display = 'inline-flex';
        if (kind === 'live') {
            pill.classList.add('is-live');
            pill.textContent = '● ' + shortCar(S.carFolder);
            pill.title = detail || ('Pit Lane Live armed — every render auto-deploys to Documents/iRacing/paint/' + S.carFolder);
        } else if (kind === 'busy') {
            pill.classList.add('is-busy');
            pill.textContent = 'deploying…';
            pill.title = detail || '';
        } else if (kind === 'ok') {
            pill.classList.add('is-ok');
            pill.textContent = 'deployed ' + hhmm(new Date()) + ' ✓';
            pill.title = detail || '';
        } else if (kind === 'fail') {
            pill.classList.add('is-fail');
            pill.textContent = 'failed ✗';
            pill.title = detail || 'Deploy failed';
        }
    }

    // ------------------------------------------------------- arm / disarm
    function arm() {
        if (!S.carFolder) { openPopover(); return; }
        if (!installWrap()) startWrapPoll(); // arm anyway; hook attaches as soon as the render module is up
        S.live = true;
        if (S.els.toggle) {
            S.els.toggle.classList.add('spb-exp-pll-on');
            S.els.toggle.setAttribute('aria-pressed', 'true');
            S.els.toggle.title = 'Pit Lane Live is ON — every render auto-deploys to ' + S.carFolder + '. Click to stop.';
        }
        setPill('live');
        toast('Pit Lane Live ON — every render now auto-deploys to ' + S.carFolder);
        // Sync the sim immediately with the latest finished render, if one exists this session.
        var jid = '';
        try { if (typeof lastRenderedJobId !== 'undefined' && lastRenderedJobId) jid = String(lastRenderedJobId); } catch (e) { /* not defined yet */ }
        if (jid) scheduleDeploy(jid);
    }

    function disarm(quiet) {
        S.live = false;
        S.pendingJobId = null;
        if (S.debounceTimer) { clearTimeout(S.debounceTimer); S.debounceTimer = null; }
        if (S.els.toggle) {
            S.els.toggle.classList.remove('spb-exp-pll-on');
            S.els.toggle.setAttribute('aria-pressed', 'false');
            S.els.toggle.title = 'Pit Lane Live — auto-deploy every render to your iRacing car folder. Click to go live.';
        }
        setPill('off');
        if (!quiet) toast('Pit Lane Live OFF');
    }

    // ------------------------------------------------------- car-picker popover
    function openPopover() {
        closePopover();
        var pop = document.createElement('div');
        pop.id = 'spbExpPllPopover';
        pop.className = 'spb-exp-pll-popover';
        pop.setAttribute('role', 'dialog');
        pop.setAttribute('aria-label', 'Pit Lane Live car picker');

        var title = document.createElement('div');
        title.className = 'spb-exp-pll-pop-title';
        title.textContent = 'PIT LANE LIVE — pick your sim car';
        pop.appendChild(title);

        var sel = document.createElement('select');
        sel.className = 'spb-exp-pll-pop-select';
        sel.setAttribute('aria-label', 'iRacing car folder');
        var opt0 = document.createElement('option');
        opt0.value = '';
        opt0.textContent = 'Loading car folders…';
        sel.appendChild(opt0);
        pop.appendChild(sel);

        var row = document.createElement('div');
        row.className = 'spb-exp-pll-pop-row';

        var goBtn = document.createElement('button');
        goBtn.type = 'button';
        goBtn.className = 'spb-exp-pll-pop-go';
        goBtn.textContent = S.live ? 'SWITCH CAR' : 'GO LIVE';
        goBtn.addEventListener('click', function () {
            var v = sel.value;
            if (!v) { toast('Pick a car folder first', true); return; }
            S.carFolder = v;
            lsSet(LS_CAR_KEY, v);
            closePopover();
            if (S.live) { setPill('live'); toast('Pit Lane Live now targets ' + v); }
            else arm();
        });
        row.appendChild(goBtn);

        var refreshBtn = document.createElement('button');
        refreshBtn.type = 'button';
        refreshBtn.className = 'spb-exp-pll-pop-btn';
        refreshBtn.textContent = '↻ Rescan';
        refreshBtn.title = 'Re-list Documents/iRacing/paint car folders';
        refreshBtn.addEventListener('click', function () { loadCars(sel); });
        row.appendChild(refreshBtn);

        var closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'spb-exp-pll-pop-btn';
        closeBtn.textContent = 'Close';
        closeBtn.addEventListener('click', function () { closePopover(); });
        row.appendChild(closeBtn);

        pop.appendChild(row);

        var note = document.createElement('div');
        note.className = 'spb-exp-pll-pop-note';
        note.textContent = 'Copies each finished render’s TGAs into Documents/iRacing/paint/<car>. ' +
            'Sit in a solo/test session and the sim repaints itself (Ctrl+R in-sim forces a reload).';
        pop.appendChild(note);

        document.body.appendChild(pop);
        S.els.popover = pop;

        // Anchor above the toggle (render bar lives at the bottom) without measuring: bottom/right anchored.
        var anchor = S.els.toggle || document.getElementById('btnRender');
        if (anchor && anchor.getBoundingClientRect) {
            var r = anchor.getBoundingClientRect();
            pop.style.bottom = Math.max(8, (window.innerHeight - r.top + 8)) + 'px';
            pop.style.right = Math.max(8, (window.innerWidth - r.right)) + 'px';
        } else {
            pop.style.bottom = '60px';
            pop.style.right = '14px';
        }

        // Click-outside + Escape close (bound on open, unbound on close).
        S.docClick = function (ev) {
            if (!S.els.popover) return;
            if (S.els.popover.contains(ev.target)) return;
            if (S.els.wrap && S.els.wrap.contains(ev.target)) return;
            closePopover();
        };
        S.docKeydown = function (ev) { if (ev.key === 'Escape') closePopover(); };
        setTimeout(function () { // skip the click that opened us
            document.addEventListener('mousedown', S.docClick, true);
            document.addEventListener('keydown', S.docKeydown, true);
        }, 0);

        loadCars(sel);
    }

    function closePopover() {
        if (S.docClick) { document.removeEventListener('mousedown', S.docClick, true); S.docClick = null; }
        if (S.docKeydown) { document.removeEventListener('keydown', S.docKeydown, true); S.docKeydown = null; }
        if (S.els.popover) {
            if (S.els.popover.parentNode) S.els.popover.parentNode.removeChild(S.els.popover);
            S.els.popover = null;
        }
    }

    function loadCars(sel) {
        while (sel.firstChild) sel.removeChild(sel.firstChild);
        var loading = document.createElement('option');
        loading.value = '';
        loading.textContent = 'Loading car folders…';
        sel.appendChild(loading);

        fetch(apiBase() + '/iracing-cars', { signal: fetchSignal() })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                while (sel.firstChild) sel.removeChild(sel.firstChild);
                var cars = (data && Array.isArray(data.cars)) ? data.cars : [];
                if (!cars.length) {
                    var none = document.createElement('option');
                    none.value = '';
                    none.textContent = (data && data.error) ? String(data.error) : 'No car folders found in Documents/iRacing/paint';
                    sel.appendChild(none);
                    return;
                }
                var pick = document.createElement('option');
                pick.value = '';
                pick.textContent = 'Select car folder…';
                sel.appendChild(pick);
                cars.forEach(function (c) { // built via DOM APIs — folder names are never injected as HTML
                    var o = document.createElement('option');
                    o.value = String(c.name || '');
                    o.title = String(c.path || '');
                    o.textContent = String(c.name || '') + ' (' + (c.tga_count != null ? c.tga_count : 0) + ' tga)';
                    sel.appendChild(o);
                });
                var saved = S.carFolder || lsGet(LS_CAR_KEY);
                if (saved) sel.value = saved;
                if (!sel.value) sel.selectedIndex = 0;
            })
            .catch(function (e) {
                while (sel.firstChild) sel.removeChild(sel.firstChild);
                var err = document.createElement('option');
                err.value = '';
                err.textContent = 'Car list failed: ' + ((e && e.message) ? e.message : 'network error');
                sel.appendChild(err);
            });
    }

    // ------------------------------------------------------- mount / unmount UI
    function mountUI() {
        if (S.els.wrap) return true;
        var renderFloat = document.getElementById('renderFloat'); // paint-booth-v2.html:2393
        var actions = renderFloat ? renderFloat.querySelector('.render-float-actions') : null;
        if (!actions) return false;

        var wrap = document.createElement('span');
        wrap.id = 'spbExpPllWrap';
        wrap.className = 'spb-exp-pll-wrap';

        var toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.id = 'spbExpPllToggle';
        toggle.className = 'spb-exp-pll-toggle';
        toggle.setAttribute('aria-pressed', 'false');
        toggle.title = 'Pit Lane Live — auto-deploy every render to your iRacing car folder. Click to go live.';
        toggle.textContent = '⛽ LIVE → SIM';
        toggle.addEventListener('click', function () {
            if (S.live) disarm(); else arm();
        });
        wrap.appendChild(toggle);

        var caret = document.createElement('button');
        caret.type = 'button';
        caret.id = 'spbExpPllCaret';
        caret.className = 'spb-exp-pll-caret';
        caret.title = 'Choose / change the sim car folder';
        caret.setAttribute('aria-label', 'Choose sim car folder');
        caret.textContent = '▾';
        caret.addEventListener('click', function () {
            if (S.els.popover) closePopover(); else openPopover();
        });
        wrap.appendChild(caret);

        var pill = document.createElement('span');
        pill.id = 'spbExpPllPill';
        pill.className = 'spb-exp-pll-pill';
        pill.setAttribute('role', 'status');
        pill.setAttribute('aria-live', 'polite');
        pill.style.display = 'none';
        wrap.appendChild(pill);

        // Sit directly after the RENDER button so cause→effect reads left to right.
        var btnRender = document.getElementById('btnRender');
        if (btnRender && btnRender.parentNode === actions) actions.insertBefore(wrap, btnRender.nextSibling);
        else actions.appendChild(wrap);

        S.els.wrap = wrap;
        S.els.toggle = toggle;
        S.els.caret = caret;
        S.els.pill = pill;
        return true;
    }

    function unmountUI() {
        closePopover();
        if (S.els.wrap && S.els.wrap.parentNode) S.els.wrap.parentNode.removeChild(S.els.wrap);
        S.els.wrap = null; S.els.toggle = null; S.els.caret = null; S.els.pill = null;
    }

    // ------------------------------------------------------- enable / disable
    function enable() {
        if (S.enabled) return;
        S.enabled = true;
        S.carFolder = lsGet(LS_CAR_KEY);
        installWrap() || startWrapPoll();
        if (!mountUI()) {
            // DOM not ready yet — retry briefly (renderFloat is static markup, so this resolves fast).
            var tries = 0;
            S.mountTimer = setInterval(function () {
                tries += 1;
                if (mountUI() || tries >= 40) {
                    clearInterval(S.mountTimer);
                    S.mountTimer = null;
                    if (!S.els.wrap) console.warn(LOG, 'could not find #renderFloat .render-float-actions — UI not mounted');
                }
            }, 500);
        }
        console.log(LOG, 'enabled' + (S.carFolder ? (' (remembered car: ' + S.carFolder + ')') : ''));
    }

    function disable() {
        if (!S.enabled) return;
        disarm(true);
        if (S.mountTimer) { clearInterval(S.mountTimer); S.mountTimer = null; }
        unmountUI();
        uninstallWrap();
        S.enabled = false;
        console.log(LOG, 'disabled — all DOM/listeners removed');
    }

    // ------------------------------------------------------- self-register (NO-OP until enable())
    window.SPB_EXPERIMENTS = window.SPB_EXPERIMENTS || [];
    window.SPB_EXPERIMENTS.push({
        id: EXP_ID,
        name: 'Pit Lane Live (auto-deploy mirror to the sim)',
        pitch: 'I sat in the iRacing garage and watched my actual car repaint itself every time I hit render — no export, no file copying, no alt-tab shuffle.',
        enable: enable,
        disable: disable,
    });
})();
