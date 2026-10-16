/* Edit in PhotoCraft - round trip between SPB layers and a layered PSD.
 * [2026-10-09 W12-ROUNDTRIP] Owner: "Edit in PhotoCraft - SPB car files go to PhotoCraft and come back easily".
 *
 * Flow: Layers > Actions > "Edit in PhotoCraft" sends the layer stack to /api/photocraft/export (layered
 * PSD in a work folder, last-render spec map as a hidden group), launches PhotoCraft on it, then watches
 * the file. When the painter saves, only the layers whose pixels actually changed come back; they replace
 * the matching SPB layer's pixels as ONE undoable step (_pushLayerStackUndo). Zones, finishes, render
 * settings are never touched. Layers deleted in PhotoCraft are NOT deleted in SPB.
 *
 * Kill switch: window.SPB_PHOTOCRAFT_OFF = true (set before this script loads) hides the menu item and
 * makes start() a no-op. Server twin: env SPB_PHOTOCRAFT_OFF=1.
 * PhotoCraft is third-party (Apache-2.0 / MIT), bundled in tools/photocraft (owner 2026-10-09) - see NOTICE.
 */
(function () {
    'use strict';
    var HELP_URL = 'https://github.com/storytold/photocraft/releases';
    var BLEND_FROM_PSD = {
        normal: 'source-over', multiply: 'multiply', screen: 'screen', overlay: 'overlay', darken: 'darken',
        lighten: 'lighten', color_dodge: 'color-dodge', color_burn: 'color-burn', hard_light: 'hard-light',
        soft_light: 'soft-light', difference: 'difference', exclusion: 'exclusion', hue: 'hue',
        saturation: 'saturation', color: 'color', luminosity: 'luminosity'
    };
    var BLEND_TO_PSD = { 'source-over': 'normal', 'color-dodge': 'color_dodge', 'color-burn': 'color_burn',
        'hard-light': 'hard_light', 'soft-light': 'soft_light' };
    var state = { session: null, name: '', timer: null, busy: false, psdPath: '', launched: false, lastMsg: '' };

    function off() { return !!window.SPB_PHOTOCRAFT_OFF; }
    function toast(msg, kind) {
        try { if (typeof window.showToast === 'function') window.showToast(msg, kind === 'error' ? true : kind); } catch (_) {}
    }
    function api(path, body) {
        var opts = { headers: { 'X-Shokker-Internal': '1' } };
        if (body !== undefined) {
            opts.method = 'POST';
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        }
        return fetch(path, opts).then(function (r) {
            return r.json().catch(function () { return { ok: false, error: 'bad response (HTTP ' + r.status + ')' }; });
        });
    }

    function layerList() { return Array.isArray(window._psdLayers) ? window._psdLayers : []; }

    function groupPathOf(l) {
        if (Array.isArray(l.groupChain) && l.groupChain.length) {
            return l.groupChain.map(function (g) { return String(g && g.name || 'Group'); });
        }
        return l.groupName ? String(l.groupName).split(' / ').filter(Boolean) : [];
    }

    function layerPng(l) {
        var img = l.img;
        var w = img.width || img.naturalWidth, h = img.height || img.naturalHeight;
        if (!w || !h) return null;
        var c = document.createElement('canvas');
        c.width = w; c.height = h;
        var ctx = c.getContext('2d');
        // bake the non-destructive Hue/Sat/Bright adjust, like EXPORT does, so PhotoCraft shows what SPB shows
        var f = (window.SPBLayerClippingMask && typeof window.SPBLayerClippingMask.adjustFilterFor === 'function')
            ? window.SPBLayerClippingMask.adjustFilterFor(l) : null;
        // [SPB-TLAY2 2026-10-10 L2-3] Hue/Sat use the PhotoCraft math now; hand PhotoCraft the baked copy (matches the canvas). SPB_TLAY2_OFF -> old CSS filter.
        var t2h = (window.SPBTlay2Hsb && typeof window.SPBTlay2Hsb.baked === 'function') ? window.SPBTlay2Hsb.baked(l) : null;
        if (f && !t2h) ctx.filter = f;
        ctx.drawImage(t2h || img, 0, 0);
        var ox = Array.isArray(l.bbox) ? (l.bbox[0] || 0) : 0, oy = Array.isArray(l.bbox) ? (l.bbox[1] || 0) : 0;
        return { png: c.toDataURL('image/png'), bbox: [ox, oy, ox + w, oy + h] };
    }

    /* [SPB-TLAY2 2026-10-10 L2-4] What the round trip used to lose without saying so (kill switch window.SPB_TLAY2_OFF = true -> old behaviour):
     *  - adjustment layers (pcAdj) went out as BLANK full-canvas pixel layers: PhotoCraft showed the layer without the adjustment, and
     *    anything painted on the blank layer came back and replaced its (ignored) pixels = the painter's work silently vanished.
     *    Now they are kept out of the PSD, stay in SPB untouched, and the painter is told in one line.
     *  - layer masks and active layer effects stay on the SPB layer (the pixels travel unmasked), so PhotoCraft shows more than SPB does:
     *    counted and told in the same line.
     *  - a group's own opacity / blend / visibility / pass-through mode did not travel (members drew at 100% normal): now sent with the groups.
     *  - group settings changed IN PhotoCraft are not applied to SPB groups: the route reports them and the bring-back message names them. */
    function t2on() { return window.SPB_TLAY2_OFF !== true; }
    function noteGroups(l, meta, seen) {
        var c = Array.isArray(l.groupChain) ? l.groupChain : [];
        var path = [];
        for (var i = 0; i < c.length; i++) {
            var g = c[i] || {};
            path.push(String(g.name || 'Group'));
            var k = path.join('\u0001');
            if (seen[k]) continue;
            seen[k] = 1;
            meta.push({ path: path.slice(), opacity: g.opacity == null ? 255 : Math.round(+g.opacity), visible: !(g.visible === false || g.ownVisible === false),
                        blend: BLEND_TO_PSD[g.blendMode || 'source-over'] || g.blendMode || 'normal', pass_through: g.mode === 'pass-through' });
        }
    }
    function hasFx(l) {
        var e = l && l.effects;
        if (!e || typeof e !== 'object') return false;
        return Object.keys(e).some(function (k) { return e[k] && e[k].enabled; });
    }

    function collectLayers() {
        var pc = document.getElementById('paintCanvas');
        var W = pc ? pc.width : 0, H = pc ? pc.height : 0;
        var out = [];
        var T2 = t2on(), adj = 0, masked = 0, fx = 0, gmeta = [], gseen = {};
        layerList().forEach(function (l) {
            if (!l || !l.img) return;
            if (T2 && l.pcAdj) { adj++; return; }
            var p = layerPng(l);
            if (!p) return;
            if (T2) { if (l.pcMask) masked++; if (hasFx(l)) fx++; noteGroups(l, gmeta, gseen); }
            out.push({
                id: l.id, name: l.name || 'Layer', group_path: groupPathOf(l), visible: l.visible !== false,
                opacity: l.opacity != null ? l.opacity : 255,
                blend: BLEND_TO_PSD[l.blendMode || 'source-over'] || l.blendMode || 'normal',
                clipping: !!l.clippingMask, bbox: p.bbox, png: p.png
            });
        });
        var flat = false;
        if (!out.length && pc && W && H) {   // flat TGA/PNG document: send the source paint as one layer
            flat = true;
            out.push({ id: 'flat_base', name: 'SPB Paint', group_path: [], visible: true, opacity: 255, blend: 'normal',
                       clipping: false, bbox: [0, 0, W, H], png: pc.toDataURL('image/png') });
        }
        return { W: W, H: H, layers: out, flat: flat, adj: adj, masked: masked, fx: fx, groups: gmeta };
    }
    // one line, shown when the painter sends the layers and again when they come back (state.kept holds the counts)
    function keptLine(d) {
        var bits = [];
        if (d.adj) bits.push(d.adj + ' adjustment layer' + (d.adj > 1 ? 's' : ''));
        if (d.masked) bits.push(d.masked + ' layer mask' + (d.masked > 1 ? 's' : ''));
        if (d.fx) bits.push(d.fx + ' layer effect' + (d.fx > 1 ? 's' : ''));
        if (!bits.length) return '';
        var last = bits.pop();
        return (bits.length ? bits.join(', ') + ' and ' + last : last) + ' stay in SPB and still apply when you bring the layers back; PhotoCraft shows the layers without them.';
    }
    function groupChangeLine(list) {
        if (!list || !list.length) return '';
        var parts = list.slice(0, 4).map(function (g) {
            var nm = (g.path || []).join(' / ') || 'Group', f = (g.fields || []).map(function (x) { return x === 'removed-or-renamed' ? 'renamed or removed' : x; });
            return nm + ' (' + f.join(', ') + ')';
        });
        return 'Group settings changed in PhotoCraft were not applied (set them in SPB): ' + parts.join('; ') + (list.length > 4 ? '; +' + (list.length - 4) + ' more' : '') + '.';
    }

    /* ---------- small status card (SPB look: dark card, cyan accent) ---------- */
    function card() {
        var el = document.getElementById('spbPhotoCraftCard');
        if (!el) {
            el = document.createElement('div');
            el.id = 'spbPhotoCraftCard';
            el.setAttribute('role', 'status');
            el.style.cssText = 'position:fixed;right:14px;bottom:84px;z-index:100000;max-width:340px;font-size:11px;' +
                'background:var(--bg-dark,#10141c);color:var(--text,#dfe6f0);border:1px solid var(--accent-cyan,#00e5ff);' +
                'border-radius:8px;padding:10px 12px;box-shadow:0 8px 24px rgba(0,0,0,.55);';
            document.body.appendChild(el);
        }
        return el;
    }
    function btn(label, onclick, primary) {
        var b = document.createElement('button');
        b.type = 'button'; b.textContent = label; b.onclick = onclick;
        b.style.cssText = 'font-size:10px;padding:3px 9px;margin:6px 6px 0 0;border-radius:3px;cursor:pointer;font-weight:bold;' +
            'background:' + (primary ? 'rgba(0,229,255,0.12)' : 'transparent') + ';border:1px solid ' +
            (primary ? 'var(--accent-cyan,#00e5ff)' : 'var(--border,#2a3342)') + ';color:' +
            (primary ? 'var(--accent-cyan,#00e5ff)' : 'var(--text-dim,#9aa7ba)') + ';';
        return b;
    }
    function render(title, lines, buttons) {
        var el = card();
        el.textContent = '';
        var t = document.createElement('div');
        t.style.cssText = 'font-weight:bold;color:var(--accent-cyan,#00e5ff);margin-bottom:4px;';
        t.textContent = title;
        el.appendChild(t);
        (lines || []).forEach(function (s) {
            var d = document.createElement('div');
            d.style.cssText = 'color:var(--text-dim,#9aa7ba);line-height:1.4;word-break:break-word;';
            d.textContent = s;
            el.appendChild(d);
        });
        (buttons || []).forEach(function (b) { el.appendChild(b); });
    }
    function closeCard() { var el = document.getElementById('spbPhotoCraftCard'); if (el) el.remove(); }

    function showWaiting(extra) {
        var lines = ['Edit in PhotoCraft, then press Save (Ctrl+S). Changed layers come back here automatically.'];
        if (!state.launched) lines.push('PhotoCraft did not open by itself. Open this file in it (or any PSD editor):');
        if (!state.launched) lines.push(state.psdPath);
        if (Array.isArray(extra)) extra.forEach(function (x) { if (x) lines.push(x); });   // [SPB-TLAY2 L2-4] several lines (spec note, kept-in-SPB notice)
        else if (extra) lines.push(extra);
        lines.push('Zones and finishes are never touched. Ctrl+Z undoes a bring-back.');
        var b = [btn('Bring back now', function () { pull(true); }, true), btn('Reopen', relaunch), btn('Stop watching', stop)];
        if (!state.launched) b.push(btn('Get PhotoCraft', function () { window.open(HELP_URL, '_blank', 'noopener'); }));
        render('PhotoCraft: ' + state.name, lines, b);
    }

    function showMissing(res) {
        var input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'Paste the path to photocraft.exe';
        input.style.cssText = 'width:100%;box-sizing:border-box;margin-top:6px;font-size:10px;padding:3px 6px;' +
            'background:var(--bg-card,#161c27);color:var(--text,#dfe6f0);border:1px solid var(--border,#2a3342);border-radius:3px;';
        var lines = ['PhotoCraft is a free layered image editor (Photoshop-style). SPB did not find it on this PC.',
                     'Your layers are already saved as a PSD, so you can also open this file in any editor:', state.psdPath];
        render('Get PhotoCraft', lines, [
            btn('Download PhotoCraft', function () { window.open(HELP_URL, '_blank', 'noopener'); }, true),
            btn('Use my copy', function () {
                api('/api/photocraft/settings', { exe: input.value.trim() }).then(function (r) {
                    if (r.ok) { toast('PhotoCraft found. Opening it...'); relaunch(); }
                    else toast(r.error || 'That path did not work', 'error');
                });
            }),
            btn('Keep watching the file', function () { showWaiting(); })
        ]);
        card().appendChild(input);
    }

    function relaunch() {
        if (!state.session) return;
        api('/api/photocraft/launch', { session: state.session }).then(function (r) {
            state.launched = !!r.launched;
            if (r.launched) showWaiting(); else showMissing(r);
        });
    }

    function stop() {
        if (state.timer) clearInterval(state.timer);
        state.timer = null; state.session = null; closeCard();
        toast('Stopped watching the PhotoCraft file.');
    }

    /* ---------- bring changes back ---------- */
    function decode(url, w, h) {
        return new Promise(function (resolve, reject) {
            var im = new Image();
            im.onload = function () {
                var c = document.createElement('canvas');
                c.width = im.naturalWidth || w; c.height = im.naturalHeight || h;
                c.getContext('2d').drawImage(im, 0, 0);
                resolve(c);
            };
            im.onerror = function () { reject(new Error('could not decode a layer image')); };
            im.src = url;
        });
    }

    async function apply(res) {
        var layers = layerList();
        var byId = {};
        layers.forEach(function (l) { if (l) byId[l.id] = l; });
        var edits = res.layers || [];
        var prepared = [];
        for (var i = 0; i < edits.length; i++) {          // decode everything first: nothing mutates on a failure
            var e = edits[i];
            var canvas = e.png ? await decode(e.png) : null;
            prepared.push({ e: e, canvas: canvas, target: e.spb_id ? byId[e.spb_id] : null });
        }
        var stackLoaded = !!window._psdLayersLoaded;
        if (stackLoaded && typeof window._pushLayerStackUndo === 'function') window._pushLayerStackUndo('Edit in PhotoCraft');
        var replaced = 0, added = 0, metaOnly = 0, skipped = 0, protectedAdj = 0, addedIds = {};
        prepared.forEach(function (p) {
            var e = p.e, t = p.target, blend = BLEND_FROM_PSD[e.blend] || 'source-over';
            // [SPB-TLAY2 2026-10-10 L2-4] an adjustment layer is never overwritten by pixels coming back (none are sent now; this is the backstop)
            if (t && t.pcAdj && t2on()) { skipped++; protectedAdj++; return; }
            if (t) {
                if (p.canvas) {
                    t.img = p.canvas; t.bbox = e.bbox.slice();
                    t.adjHue = 0; t.adjSat = 0; t.adjBri = 0;   // baked into the exported pixels
                    replaced++;
                } else metaOnly++;
                if ((e.meta_changed || []).indexOf('visible') >= 0) t.visible = !!e.visible;
                if ((e.meta_changed || []).indexOf('opacity') >= 0) t.opacity = e.opacity;
                if ((e.meta_changed || []).indexOf('blend') >= 0) t.blendMode = blend;
                return;
            }
            if (!p.canvas) { skipped++; return; }
            // layer made inside PhotoCraft (or renamed there): add it, never replace anything
            var nl;
            if (stackLoaded) {
                nl = { id: 'pc_' + Date.now().toString(36) + '_' + i, name: e.name, path: '', visible: !!e.visible,
                       opacity: e.opacity, blendMode: blend, locked: false, alphaLock: false, clippingMask: false,
                       effects: null, bbox: e.bbox.slice(), img: p.canvas };
                var below = e.below_id ? layers.findIndex(function (l) { return l && l.id === e.below_id; }) : -1;
                if (below >= 0) {
                    var bl = layers[below];
                    if (bl && groupPathOf(bl).join(' / ') === (e.group_path || []).join(' / ')) {
                        nl.groupName = bl.groupName; nl.groupChain = bl.groupChain; nl.parentGroupKey = bl.parentGroupKey;
                        nl.importVisible = bl.importVisible; nl.ownVisible = true;
                    }
                    layers.splice(below + 1, 0, nl);
                } else layers.push(nl);
            } else if (typeof window.addBlankLayer === 'function') {   // flat paint: first layer, own undo entry
                nl = window.addBlankLayer();
                if (!nl) { skipped++; return; }
                nl.name = e.name === 'SPB Paint' ? 'SPB Paint (PhotoCraft)' : e.name;
                nl.img = p.canvas; nl.bbox = e.bbox.slice(); nl.opacity = e.opacity; nl.blendMode = blend;
                stackLoaded = true;
            } else { skipped++; return; }
            addedIds[e.index] = nl.id;
            added++;
        });
        window._spbLayerRev = (window._spbLayerRev || 0) + 1;
        try { if (typeof window.invalidateLayerVisibleContributionCache === 'function') window.invalidateLayerVisibleContributionCache(); } catch (_) {}
        try { if (typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers(); } catch (_) {}
        try { if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel(); } catch (_) {}
        try { if (typeof window.drawLayerBounds === 'function') window.drawLayerBounds(); } catch (_) {}
        try { if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender(); } catch (_) {}
        return { replaced: replaced, added: added, metaOnly: metaOnly, skipped: skipped, protectedAdj: protectedAdj, addedIds: addedIds };
    }

    async function applySpec(spec) {
        if (!spec || !spec.temp_path) return;
        var ok = true;
        // [SPB-CONFIRM-POLISH 2026-10-10] native confirm() -> in-app SpbDialog.ask (kill switch SPB_CONFIRM_POLISH_OFF).
        try {
            ok = await SpbDialog.ask('Use The PhotoCraft Spec Map?', { message: 'You also changed the Spec map in PhotoCraft. Use it as your Imported Spec map? It replaces the generated spec until you press Clear Spec Map. (Layers were already brought back either way.)', okLabel: 'Use Spec Map', cancelLabel: 'Keep Current', nativeText: 'You also changed the Spec map in PhotoCraft.\n\nUse it as your Imported Spec map? It replaces the generated spec until you press Clear Spec Map. (Layers were already brought back either way.)' });
        } catch (_) {}
        if (!ok) return;
        window.importedSpecMapPath = spec.temp_path;
        try { if (typeof importedSpecMapPath !== 'undefined') importedSpecMapPath = spec.temp_path; } catch (_) {}
        var status = document.getElementById('importSpecMapStatus');
        if (status) status.innerHTML = '<span style="color:var(--accent-green);font-weight:700;">&#10003; Spec active</span> - from PhotoCraft';
        var clr = document.getElementById('btnClearSpecMap');
        if (clr) clr.disabled = false;
        try { if (typeof window.triggerPreviewRender === 'function') window.triggerPreviewRender(); } catch (_) {}
    }

    async function pull(manual) {
        if (!state.session || state.busy) return;
        state.busy = true;
        try {
            var res = await api('/api/photocraft/import', { session: state.session });
            if (!res.ok) { toast(res.error || 'Could not bring the PhotoCraft file back', 'error'); showWaiting(res.error); return; }
            var nothing = !(res.layers || []).length && !res.spec;
            var gline = t2on() ? groupChangeLine(res.group_changes) : '';   // [SPB-TLAY2 L2-4] group edits made in PhotoCraft are named, never dropped silently
            if (nothing) {
                await api('/api/photocraft/ack', { session: state.session, added_ids: {} });
                if (manual || gline) toast(gline || 'No changes found in the PhotoCraft file yet.', gline ? 'warn' : undefined);
                showWaiting('Saved, no layer changes found.' + (gline ? ' ' + gline : ''));
                return;
            }
            var out = await apply(res);
            await api('/api/photocraft/ack', { session: state.session, added_ids: out.addedIds });
            var bits = [];
            if (out.replaced) bits.push(out.replaced + ' layer' + (out.replaced > 1 ? 's' : '') + ' updated');
            if (out.added) bits.push(out.added + ' new');
            if (out.metaOnly) bits.push(out.metaOnly + ' visibility/opacity change' + (out.metaOnly > 1 ? 's' : ''));
            var msg = 'Back from PhotoCraft: ' + (bits.join(', ') || 'no pixel changes') + '. Ctrl+Z undoes it.';
            if ((res.removed || []).length) msg += ' (' + res.removed.length + ' layer(s) deleted there were kept here.)';
            if (t2on()) {   // [SPB-TLAY2 L2-4] the one-line "what stayed as it was" so nothing changes without being said
                var k = state.kept || {}, kb = [];
                if (k.adj) kb.push(k.adj + ' adjustment layer' + (k.adj > 1 ? 's' : ''));
                if (k.masked) kb.push(k.masked + ' mask' + (k.masked > 1 ? 's' : ''));
                if (k.fx) kb.push(k.fx + ' effect' + (k.fx > 1 ? 's' : ''));
                if (kb.length) msg += ' ' + kb.join(', ') + ' in SPB were left as they were.';
                if (out.protectedAdj) msg += ' ' + out.protectedAdj + ' edit(s) aimed at an adjustment layer were not applied.';
                if (gline) msg += ' ' + gline;
            }
            toast(msg, 'success');
            showWaiting(msg);
            if (res.spec) applySpec(res.spec);
        } catch (err) {
            console.error('[PhotoCraft] bring-back failed', err);
            toast('PhotoCraft bring-back failed: ' + err.message + '. Nothing was changed.', 'error');
        } finally { state.busy = false; }
    }

    function tick() {
        if (!state.session || state.busy) return;
        api('/api/photocraft/poll?session=' + encodeURIComponent(state.session)).then(function (r) {
            if (r && r.ok && r.state === 'saved') pull(false);
            else if (r && r.ok === false && /Unknown session/.test(r.error || '')) stop();
        }).catch(function () {});
    }

    async function start() {
        if (off()) { toast('Edit in PhotoCraft is switched off.', 'warn'); return; }
        if (state.busy) return;
        if (state.session) { showWaiting(); return; }
        state.busy = true;
        try {
            var doc = collectLayers();
            if (doc.adj && (!doc.layers.length || doc.flat)) { toast('Only adjustment layers here: they have no pixels to edit in PhotoCraft. Add a paint layer first.', 'warn'); return; }   // [SPB-TLAY2 L2-4]
            if (!doc.layers.length) { toast('Open a paint or a layered PSD first.', 'warn'); return; }
            toast('Sending ' + doc.layers.length + ' layer' + (doc.layers.length > 1 ? 's' : '') + ' to PhotoCraft...');
            var pf = document.getElementById('paintFile');
            var nm = (pf && pf.value ? pf.value.split(/[\\/]/).pop().replace(/\.[^.]+$/, '') : '') || 'shokker_car';
            var body = { name: nm, width: doc.W, height: doc.H, layers: doc.layers, include_spec: true, launch: true };
            if (t2on() && doc.groups && doc.groups.length) body.groups = doc.groups;   // [SPB-TLAY2 L2-4] group opacity / blend / visibility travel
            var res = await api('/api/photocraft/export', body);
            if (!res.ok) { toast(res.error || 'Export to PhotoCraft failed', 'error'); return; }
            state.session = res.session; state.name = nm; state.psdPath = res.psd_path;
            state.launched = !!(res.launch && res.launch.launched);
            state.kept = t2on() ? { adj: doc.adj, masked: doc.masked, fx: doc.fx } : null;
            var kline = t2on() ? keptLine(doc) : '';
            if (kline) toast(kline, 'warn');
            if (state.timer) clearInterval(state.timer);
            state.timer = setInterval(tick, 1500);
            var extra = [res.has_spec ? 'Spec map is in the hidden "SPB SPEC" group.' : '', kline];
            if (state.launched) showWaiting(extra);
            else if (res.launch && res.launch.reason === 'missing') showMissing(res.launch);
            else showWaiting(res.launch && res.launch.error ? [res.launch.error, kline] : extra);
        } catch (err) {
            toast('Edit in PhotoCraft failed: ' + err.message, 'error');
        } finally { state.busy = false; }
    }

    window.SPBPhotoCraft = { start: start, pull: function () { return pull(true); }, stop: stop,
                             state: state, _apply: apply, _showMissing: showMissing };
    document.addEventListener('DOMContentLoaded', function () {
        if (off()) document.querySelectorAll('[data-spb-photocraft]').forEach(function (n) { n.style.display = 'none'; });
    });
})();
