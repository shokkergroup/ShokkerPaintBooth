/* Layer groups you can make and edit (ticket TL-19, TOOLS-LAYERS lane, 2026-10-10).
 * The compositor already knows groups (js/canvas/layer/clipping-mask.js: every layer carries layer.groupChain = [{key, name, mode, opacity,
 * blendMode, visible, ...}], an isolated group is flattened once and then drawn with its own opacity / blend, a pass-through group draws
 * straight into its parent) - but only imported PSDs ever had them. This file adds the missing half, modelled on PhotoCraft's layer tree
 * (a group is a node with opacity, blend mode and visibility; children are composited inside it): group the selected layers, ungroup,
 * take layers out of a group, rename it, give it an opacity / blend mode / pass-through switch, all from the group header in the layer
 * panel. New groups are pass-through at 100% (the picture does not change when you group); moving the opacity or blend makes them isolated,
 * like Photoshop. A layer dropped between the members of a group joins it, a layer moved out of it leaves it (heal(), run before every
 * composite and panel render), so the compositor's "children must be contiguous" rule can never block the picture.
 * Everything goes through the normal layer history (one undo step per action / slider drag) and the groupChain data that projects, crash
 * recovery and the PhotoCraft round trip already save. Kill switch: window.SPB_TLAY_OFF = true (no healing, no header controls, no menu).
 */
(function () {
    'use strict';
    if (window.SPBPcGroups) return;
    var VERSION = 'pcg-1';
    function off() { return window.SPB_TLAY_OFF === true; }
    var undoers = [], stats = { heals: 0, grouped: 0, lastHealMs: 0 };

    function toast(msg, kind) { try { if (typeof window.showToast === 'function') window.showToast(msg, kind); } catch (_e) {} }
    function stack() { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : []; }
    function clamp(v, a, b) { return v < a ? a : (v > b ? b : v); }
    function chainOf(l) { return l && Array.isArray(l.groupChain) ? l.groupChain : []; }
    function keyOf(g) { return String(g && g.key); }
    function innerKey(l) { var c = chainOf(l); return c.length ? keyOf(c[c.length - 1]) : null; }
    function nameOfChain(c) { return c.map(function (g) { return String(g.name || 'Group'); }).join(' / '); }
    function hasKey(l, k) { var c = chainOf(l); for (var i = 0; i < c.length; i++) if (keyOf(c[i]) === k) return true; return false; }
    function indexInChain(l, k) { var c = chainOf(l); for (var i = 0; i < c.length; i++) if (keyOf(c[i]) === k) return i; return -1; }
    function sameChainKeys(a, b) {
        var ca = chainOf(a), cb = chainOf(b);
        if (ca.length !== cb.length) return false;
        for (var i = 0; i < ca.length; i++) if (keyOf(ca[i]) !== keyOf(cb[i])) return false;
        return true;
    }
    function pushUndo(label) { if (typeof window._pushLayerStackUndo === 'function') window._pushLayerStackUndo(label); }
    function bump() { window._spbLayerRev = (window._spbLayerRev || 0) + 1; }
    function recomp(opts) { if (typeof window.recompositeFromLayers === 'function') window.recompositeFromLayers(opts); }
    function panel() { if (typeof window.renderLayerPanel === 'function') window.renderLayerPanel(); }

    // every edit of a layer's chain goes through here, so groupName / parentGroupKey (read by the compositor's clipping rules) never go stale
    function setChain(l, chain) {
        var had = chainOf(l).length > 0;
        l.groupChain = chain;
        l.parentGroupKey = chain.length ? keyOf(chain[chain.length - 1]) : null;
        if (chain.length) {
            if (!had && l.pcgPrev === undefined) l.pcgPrev = l.groupName || '';
            l.groupName = nameOfChain(chain);
        } else {
            l.groupName = l.pcgPrev !== undefined ? l.pcgPrev : '';
            if (l.pcgPrev !== undefined) delete l.pcgPrev;
        }
    }
    function chainSig(l) { return chainOf(l).map(keyOf).join('>'); }

    // ------------------------------------------------------------------ queries
    function members(key, layers) {
        var s = layers || stack(), out = [];
        for (var i = 0; i < s.length; i++) if (s[i] && hasKey(s[i], key)) out.push(s[i]);
        return out;
    }
    function descriptor(key) {
        var s = stack();
        for (var i = 0; i < s.length; i++) { var k = indexInChain(s[i], key); if (k >= 0) return chainOf(s[i])[k]; }
        return null;
    }
    function allGroups() {
        var s = stack(), seen = {}, out = [];
        for (var i = s.length - 1; i >= 0; i--) {
            var c = chainOf(s[i]);
            for (var j = 0; j < c.length; j++) { var k = keyOf(c[j]); if (!seen[k]) { seen[k] = 1; out.push(c[j]); } }
        }
        return out;
    }
    function info(key) {
        var d = descriptor(key); if (!d) return null;
        var m = members(key);
        return { key: keyOf(d), name: d.name, mode: d.mode === 'pass-through' ? 'pass-through' : 'isolated', opacity: Number(d.opacity == null ? 255 : d.opacity), blendMode: d.blendMode || 'source-over', count: m.length, ids: m.map(function (x) { return x.id; }) };
    }

    // ------------------------------------------------------------------ heal: keep every group contiguous (Photoshop behaviour)
    // The compositor refuses a stack whose group members are not next to each other, so after any reorder / insert the stack is repaired.
    // Which layer "moved" decides who gets the blame: a layer dropped between members joins the group, a member dragged away leaves it.
    // The mover is found by diffing against the last healthy order (one moved or inserted layer); unknown = old rules (longest run wins).
    var lastOrder = null;
    function orderIds(s) { var o = new Array(s.length); for (var i = 0; i < s.length; i++) o[i] = s[i] && s[i].id; return o; }
    function hintIds() {
        var h = {};
        try {
            if (typeof _selectedLayerIds !== 'undefined' && _selectedLayerIds) _selectedLayerIds.forEach(function (id) { h[id] = 1; });
            if (typeof _selectedLayerId !== 'undefined' && _selectedLayerId) h[_selectedLayerId] = 1;
            if (typeof _layerDragReorder !== 'undefined' && _layerDragReorder && _layerDragReorder.sourceLayerId) h[_layerDragReorder.sourceLayerId] = 1;
        } catch (_e) {}
        return h;
    }
    function findMovers(s) {
        if (!lastOrder) return null;
        var cur = orderIds(s), prevSet = {}, curSet = {}, movers = {}, i;
        lastOrder.forEach(function (id) { prevSet[id] = 1; }); cur.forEach(function (id) { curSet[id] = 1; });
        cur.forEach(function (id) { if (!prevSet[id]) movers[id] = 1; });
        var a = lastOrder.filter(function (id) { return curSet[id]; }), b = cur.filter(function (id) { return prevSet[id]; });
        if (a.length !== b.length) return null;
        for (i = 0; i < a.length; i++) if (a[i] !== b[i]) break;
        if (i < a.length) {
            var valid = [];
            [b[i], a[i]].forEach(function (cand) {
                var a2 = a.filter(function (x) { return x !== cand; }), b2 = b.filter(function (x) { return x !== cand; }), same = true;
                for (var j = 0; j < a2.length; j++) if (a2[j] !== b2[j]) { same = false; break; }
                if (same) valid.push(cand);
            });
            if (!valid.length) return null;
            // an adjacent swap fits two stories (C moved up past D, or D moved down past C): the selected / dragged layer is the one that moved
            var hints = hintIds(), pick = valid[0];
            for (var v = 0; v < valid.length; v++) if (hints[valid[v]]) { pick = valid[v]; break; }
            movers[pick] = 1;
        }
        return movers;
    }
    function heal(layers) {
        var s = layers || stack(), n = s.length, i, any = false;
        for (i = 0; i < n; i++) if (chainOf(s[i]).length) { any = true; break; }
        if (!any) { lastOrder = orderIds(s); return false; }
        var t0 = performance.now(), changed = false, pass, M = findMovers(s);
        for (pass = 0; pass < 4; pass++) {
            var did = false, q;
            // rule 1: a layer sitting between two members of a group (or of the same inner group) joins it - unless it did not move
            for (i = 1; i < n - 1; i++) {
                var below = chainOf(s[i - 1]), above = chainOf(s[i + 1]), me = chainOf(s[i]);
                var common = [], m2 = Math.min(below.length, above.length);
                for (q = 0; q < m2; q++) { if (keyOf(below[q]) === keyOf(above[q])) common.push(above[q]); else break; }
                if (!common.length) continue;
                var missing = false;
                for (q = 0; q < common.length; q++) if (!hasKey(s[i], keyOf(common[q]))) { missing = true; break; }
                if (!missing) continue;
                if (M && !M[s[i].id]) continue;
                setChain(s[i], common.map(function (g) { return Object.assign({}, g); }));
                did = true;
            }
            // rule 2: a group that has split into several runs keeps one of them; the others leave it. A member that just moved is the
            // one that leaves; with no mover known the longest run (the top one on a tie) stays.
            var runs = {}, order = [];
            for (i = 0; i < n; i++) {
                var c = chainOf(s[i]);
                for (var j = 0; j < c.length; j++) {
                    var k = keyOf(c[j]), R = runs[k] || (runs[k] = []);
                    if (!R.length || R[R.length - 1].end !== i - 1) R.push({ start: i, end: i }); else R[R.length - 1].end = i;
                    if (order.indexOf(k) < 0) order.push(k);
                }
            }
            order.forEach(function (k) {
                var R = runs[k]; if (R.length < 2) return;
                var drop = [], keep = [], b;
                if (M) {
                    for (b = 0; b < R.length; b++) {
                        var hasMover = false;
                        for (var x = R[b].start; x <= R[b].end; x++) if (M[s[x].id]) hasMover = true;
                        (hasMover ? drop : keep).push(b);
                    }
                }
                if (!M || !drop.length || !keep.length) {
                    var best = 0; drop = []; keep = [];
                    for (b = 1; b < R.length; b++) if ((R[b].end - R[b].start) >= (R[best].end - R[best].start)) best = b;
                    for (b = 0; b < R.length; b++) if (b !== best) drop.push(b);
                }
                drop.forEach(function (bi) {
                    for (var x2 = R[bi].start; x2 <= R[bi].end; x2++) {
                        var L = s[x2], at = indexInChain(L, k);
                        if (at >= 0) { setChain(L, chainOf(L).slice(0, at)); did = true; }
                    }
                });
            });
            if (!did) break;
            changed = true;
        }
        if (changed) { stats.heals++; bump(); }
        lastOrder = orderIds(s);
        stats.lastHealMs = performance.now() - t0;
        return changed;
    }

    // ------------------------------------------------------------------ actions
    function selectedLayers() {
        if (typeof window._spbSelectedLayers === 'function') return window._spbSelectedLayers();
        try { if (typeof _spbSelectedLayers === 'function') return _spbSelectedLayers(); } catch (_e) {}
        var id = typeof _selectedLayerId !== 'undefined' ? _selectedLayerId : null, L = stack().filter(function (l) { return l && l.id === id; });
        return L;
    }
    function uniqueName() {
        var used = {}, i;
        allGroups().forEach(function (g) { used[String(g.name)] = 1; });
        stack().forEach(function (l) { if (l && l.groupName) used[String(l.groupName)] = 1; });
        for (i = 1; i < 500; i++) if (!used['Group ' + i]) return 'Group ' + i;
        return 'Group ' + Date.now();
    }
    // a clipped layer must stay with its base: grow the set until it holds whole clipping stacks
    function closeOverClipping(ids) {
        var s = stack(), set = {}, i, grew = true;
        ids.forEach(function (id) { set[id] = 1; });
        while (grew) {
            grew = false;
            for (i = 0; i < s.length; i++) {
                var l = s[i]; if (!l) continue;
                if (set[l.id] && l.clippingMask) {   // a clipped layer pulls its base (next non-clipped below)
                    for (var b = i - 1; b >= 0; b--) { if (!set[s[b].id]) { set[s[b].id] = 1; grew = true; } if (!s[b].clippingMask) break; }
                }
                if (set[l.id] && !l.clippingMask) {   // a base pulls the layers clipped to it (directly above)
                    for (var u = i + 1; u < s.length && s[u] && s[u].clippingMask; u++) if (!set[s[u].id]) { set[s[u].id] = 1; grew = true; }
                }
            }
        }
        return set;
    }
    function groupIds(ids, opts) {
        opts = opts || {};
        if (off()) return null;
        var s = stack();
        if (!ids || !ids.length) { toast('Select the layers to group first (Ctrl-click or Shift-click selects several).', 'warn'); return null; }
        var set = closeOverClipping(ids), picked = [], first = null, i;
        for (i = 0; i < s.length; i++) if (s[i] && set[s[i].id]) { picked.push(s[i]); if (first === null) first = i; }
        var ref = picked[0];
        for (i = 1; i < picked.length; i++) if (!sameChainKeys(ref, picked[i])) { toast('Those layers sit in different groups. Select layers from the same group (or from none) to group them.', 'warn'); return null; }
        var parent = chainOf(ref).slice();
        var key = 'pcg_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6), name = opts.name || uniqueName();
        var parentPath = parent.length ? String(parent[parent.length - 1].path || nameOfChain(parent)) + '/' : '';
        var desc = { key: key, name: name, path: parentPath + name, visible: true, ownVisible: true, opacity: 255, rawBlendMode: 'pass_through', blendMode: 'source-over', mode: 'pass-through', clipping: false };
        pushUndo('Group ' + picked.length + ' layer' + (picked.length === 1 ? '' : 's'));
        // the block lands where the topmost picked layer was; the layers in between that were not picked end up below it
        var top = -1; for (i = 0; i < s.length; i++) if (s[i] && set[s[i].id]) top = i;
        var rest = [], block = [];
        for (i = 0; i < s.length; i++) { if (s[i] && set[s[i].id]) block.push(s[i]); }
        var insertAt = 0; for (i = 0; i < top; i++) if (!(s[i] && set[s[i].id])) insertAt++;
        for (i = 0; i < s.length; i++) if (!(s[i] && set[s[i].id])) rest.push(s[i]);
        var out = rest.slice(0, insertAt).concat(block, rest.slice(insertAt));
        s.length = 0; Array.prototype.push.apply(s, out);
        var chain = parent.concat([desc]);
        block.forEach(function (l) { setChain(l, chain.map(function (g) { return Object.assign({}, g); })); });
        stats.grouped++;
        bump(); recomp(); panel();
        if (!opts.quiet) toast('Grouped ' + block.length + ' layer' + (block.length === 1 ? '' : 's') + ' as "' + name + '"');
        window.SPBPcGroups.lastKey = key;
        return key;
    }
    function groupSelected() { return groupIds(selectedLayers().map(function (l) { return l.id; })); }
    function ungroup(key, quiet) {
        if (off()) return false;
        var m = members(key); if (!m.length) return false;
        pushUndo('Ungroup');
        m.forEach(function (l) {
            var c = chainOf(l), at = indexInChain(l, key);
            if (at < 0) return;
            setChain(l, c.slice(0, at).concat(c.slice(at + 1)));
        });
        bump(); recomp(); panel();
        if (!quiet) toast('Ungrouped');
        return true;
    }
    // the layers leave their innermost group and move to just above it (otherwise heal() would take them straight back in)
    function removeFromGroup(ids) {
        if (off()) return false;
        var s = stack(), want = {}; (ids || []).forEach(function (id) { want[id] = 1; });
        var sel = s.filter(function (l) { return l && want[l.id] && chainOf(l).length; });
        if (!sel.length) { toast('Those layers are not in a group.', 'warn'); return false; }
        pushUndo('Remove from group');
        var byGroup = {};
        sel.forEach(function (l) { var k = innerKey(l); (byGroup[k] = byGroup[k] || []).push(l); });
        Object.keys(byGroup).forEach(function (k) {
            var out = byGroup[k], all = members(k), pick = {}; out.forEach(function (l) { pick[l.id] = 1; });
            var topIdx = -1; all.forEach(function (l) { var ix = s.indexOf(l); if (ix > topIdx) topIdx = ix; });
            var parent = chainOf(out[0]).slice(0, -1);
            // is the group's parent still contiguous around the new place? the layers become members of the parent group (or of none)
            var rest = s.filter(function (l) { return !pick[l.id]; });
            var ins = 0; for (var i = 0; i < s.length; i++) { if (!pick[s[i].id]) ins++; if (i === topIdx) break; }
            var outSorted = s.filter(function (l) { return pick[l.id]; });
            var res = rest.slice(0, ins).concat(outSorted, rest.slice(ins));
            s.length = 0; Array.prototype.push.apply(s, res);
            outSorted.forEach(function (l) { setChain(l, parent.map(function (g) { return Object.assign({}, g); })); });
        });
        bump(); recomp(); panel();
        return true;
    }
    function patchGroup(key, patch) {
        var m = members(key); if (!m.length) return false;
        m.forEach(function (l) {
            l.groupChain = chainOf(l).map(function (g) { return keyOf(g) === key ? Object.assign({}, g, patch) : g; });
        });
        return true;
    }
    function setGroup(key, patch, final) {
        if (off()) return false;
        var d = descriptor(key); if (!d) return false;
        var p = Object.assign({}, patch);
        if ('opacity' in p) p.opacity = clamp(Math.round(Number(p.opacity) || 0), 0, 255);
        if ('blendMode' in p) p.rawBlendMode = (p.blendMode === 'source-over' ? 'normal' : String(p.blendMode).replace(/-/g, '_'));
        var nowMode = d.mode === 'pass-through' ? 'pass-through' : 'isolated';
        if (p.mode === undefined) {
            var op = 'opacity' in p ? p.opacity : Number(d.opacity == null ? 255 : d.opacity), bm = 'blendMode' in p ? p.blendMode : (d.blendMode || 'source-over');
            // pass-through cannot carry opacity or a blend mode: asking for either switches the group to isolated, like Photoshop
            if (nowMode === 'pass-through' && (op !== 255 || bm !== 'source-over')) p.mode = 'isolated';
        }
        if (p.mode === 'pass-through') { p.opacity = 255; p.blendMode = 'source-over'; p.rawBlendMode = 'pass_through'; }
        var same = true; Object.keys(p).forEach(function (k) { if (d[k] !== p[k]) same = false; });
        if (same) { if (final) gesture = null; return true; }
        if (!gesture || gesture.key !== key || gesture.what !== Object.keys(patch).join(',')) { pushUndo('Group ' + (d.name || '')); gesture = { key: key, what: Object.keys(patch).join(',') }; }
        patchGroup(key, p);
        bump();
        if (final) { gesture = null; recomp(); panel(); }
        else schedule();
        return true;
    }
    var gesture = null, raf = 0;
    function schedule() {
        if (raf) return;
        raf = requestAnimationFrame(function () { raf = 0; recomp({ readback: false }); });
    }
    function endGesture() { gesture = null; if (raf) { cancelAnimationFrame(raf); raf = 0; } recomp(); }
    function rename(key, name) {
        if (off()) return false;
        name = String(name || '').replace(/\s+/g, ' ').trim().slice(0, 60);
        var d = descriptor(key); if (!d || !name || name === d.name) return false;
        pushUndo('Rename group');
        var oldNames = {}, m = members(key);
        m.forEach(function (l) { oldNames[l.groupName || ''] = 1; });
        patchGroup(key, { name: name, path: String(d.path || d.name).replace(/[^/]*$/, '') + name });
        m.forEach(function (l) { setChainNameOnly(l); });
        try {
            if (typeof _collapsedLayerGroups !== 'undefined') {
                Object.keys(oldNames).forEach(function (on) {
                    if (_collapsedLayerGroups.has(on)) { _collapsedLayerGroups.delete(on); }
                });
                if (typeof _persistCollapsedLayerGroups === 'function') _persistCollapsedLayerGroups();
            }
        } catch (_e) {}
        bump(); panel();
        return true;
    }
    function setChainNameOnly(l) { l.groupName = nameOfChain(chainOf(l)); }

    // ------------------------------------------------------------------ the group header: settings strip
    // the "N selected" bar gets a GROUP button; the bar wraps instead of running off the panel at 1100 px (it was a no-wrap row: MERGE, DELETE, x)
    function decorateBar(c) {
        var mb = c.querySelector('button[onclick="mergeSelectedLayers()"]');
        if (!mb || !mb.parentNode) return;
        var bar = mb.parentNode;
        if (bar.querySelector('[data-pcg-bar]')) return;
        bar.style.flexWrap = 'wrap';
        var kids = bar.children;
        for (var i = 0; i < kids.length; i++) if (kids[i].tagName === 'SPAN' && /Ctrl-click/.test(kids[i].textContent || '')) { bar.title = kids[i].textContent; kids[i].style.display = 'none'; }
        var n = selectedLayers().length;
        var gb = el('button', '', 'GROUP ' + n, { type: 'button', 'class': 'layer-act-btn', 'data-pcg-bar': '1', title: 'Put the selected layers in a new group (Ctrl+Alt+G)' });
        gb.addEventListener('click', function (ev) { ev.stopPropagation(); ev.preventDefault(); var k = groupSelected(); if (k) { openKey = k; panel(); } });
        bar.insertBefore(gb, mb.nextSibling);
    }
    var openKey = null, uiState = {};
    function groupBlendOptions() {
        var list = [['source-over', 'Normal'], ['multiply', 'Multiply'], ['screen', 'Screen'], ['overlay', 'Overlay'], ['darken', 'Darken'], ['lighten', 'Lighten'], ['color-dodge', 'Color Dodge'], ['color-burn', 'Color Burn'],
            ['hard-light', 'Hard Light'], ['soft-light', 'Soft Light'], ['difference', 'Difference'], ['exclusion', 'Exclusion'], ['hue', 'Hue'], ['saturation', 'Saturation'], ['color', 'Color'], ['luminosity', 'Luminosity']];
        return list;
    }
    function el(tag, css, text, attrs) {
        var e = document.createElement(tag); if (css) e.style.cssText = css; if (text != null) e.textContent = text;
        if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
        return e;
    }
    var BTN = 'font-size:9px;padding:2px 6px;';
    function groupHeaderKeys(container) {
        // the panel builds one header per run of equal groupName, top of the stack first: pair them with the descriptor of that run
        var s = stack(), prev = null, out = [];
        for (var i = s.length - 1; i >= 0; i--) {
            var l = s[i]; if (!l) continue;
            var g = l.groupName || '';
            if (g !== prev) { prev = g; if (g) out.push(chainOf(l).length ? innerKey(l) : null); }
        }
        return out;
    }
    function buildStrip(key) {
        var d = descriptor(key); if (!d) return null;
        var iso = d.mode !== 'pass-through', op = Math.round(Number(d.opacity == null ? 255 : d.opacity) / 255 * 100);
        var box = el('div', 'margin:0 0 4px;padding:6px;background:#1b1b1f;border:1px solid #333;border-radius:4px;display:block;', null, { 'data-pcg-strip': key });
        var r1 = el('div', 'display:flex;align-items:center;gap:4px;margin-bottom:5px;min-width:0;');
        r1.appendChild(el('i', 'font-style:normal;font-size:8px;color:#888;flex:0 0 42px;', 'Name:'));
        var nm = el('input', 'flex:1 1 0%;min-width:0;width:0;font-size:10px;padding:2px 4px;background:#111;color:#ddd;border:1px solid #444;border-radius:3px;', null, { type: 'text', value: String(d.name || ''), maxlength: '60', 'data-pcg-name': key, 'aria-label': 'Group name' });
        nm.addEventListener('keydown', function (ev) { ev.stopPropagation(); if (ev.key === 'Enter') { rename(key, nm.value); } else if (ev.key === 'Escape') { nm.value = String(d.name || ''); nm.blur(); } });
        nm.addEventListener('change', function (ev) { ev.stopPropagation(); rename(key, nm.value); });
        r1.appendChild(nm); box.appendChild(r1);
        var r2 = el('div', 'display:flex;align-items:center;gap:4px;margin-bottom:5px;min-width:0;');
        r2.appendChild(el('i', 'font-style:normal;font-size:8px;color:#888;flex:0 0 42px;', 'Opacity:'));
        var rg = el('input', 'flex:1 1 0%;min-width:0;width:0;height:12px;cursor:pointer;', null, { type: 'range', min: '0', max: '100', step: '1', value: String(op), 'data-pcg-opacity': key, 'aria-label': 'Group opacity' });
        var val = el('i', 'font-style:normal;font-size:8px;color:#ddd;flex:0 0 34px;text-align:right;', op + '%', { 'data-pcg-val': key });
        rg.addEventListener('input', function (ev) { ev.stopPropagation(); val.textContent = rg.value + '%'; setGroup(key, { opacity: Math.round(Number(rg.value) * 255 / 100) }, false); });
        rg.addEventListener('change', function (ev) { ev.stopPropagation(); setGroup(key, { opacity: Math.round(Number(rg.value) * 255 / 100) }, true); });
        rg.addEventListener('pointerup', function () { if (gesture) { gesture = null; endGesture(); panel(); } });
        r2.appendChild(rg); r2.appendChild(val); box.appendChild(r2);
        var r3 = el('div', 'display:flex;align-items:center;gap:4px;margin-bottom:5px;min-width:0;');
        r3.appendChild(el('i', 'font-style:normal;font-size:8px;color:#888;flex:0 0 42px;', 'Blend:'));
        var sel = el('select', 'flex:1 1 0%;min-width:0;width:0;font-size:10px;padding:2px;background:#111;color:#ddd;border:1px solid #444;border-radius:3px;', null, { 'data-pcg-blend': key, 'aria-label': 'Group blend mode' });
        groupBlendOptions().forEach(function (o) { var op2 = el('option', '', o[1], { value: o[0] }); if ((d.blendMode || 'source-over') === o[0]) op2.selected = true; sel.appendChild(op2); });
        sel.addEventListener('change', function (ev) { ev.stopPropagation(); setGroup(key, { blendMode: sel.value }, true); });
        r3.appendChild(sel); box.appendChild(r3);
        var r4 = el('div', 'display:flex;align-items:center;gap:4px;margin-bottom:5px;min-width:0;');
        r4.appendChild(el('i', 'font-style:normal;font-size:8px;color:#888;flex:0 0 42px;', 'Mode:'));
        var cb = el('input', 'cursor:pointer;margin:0;', null, { type: 'checkbox', 'data-pcg-pass': key, 'aria-label': 'Pass through', title: 'Pass through: the group draws straight into the picture and sees everything below it (adjustment layers inside reach the layers under the group). Turn off for opacity / blend.' });
        if (!iso) cb.checked = true;
        cb.addEventListener('change', function (ev) { ev.stopPropagation(); setGroup(key, { mode: cb.checked ? 'pass-through' : 'isolated' }, true); });
        r4.appendChild(cb); r4.appendChild(el('i', 'font-style:normal;font-size:8px;color:#aaa;', 'Pass through', { title: cb.checked ? 'The group sees what is below it' : 'The group is flattened first, then drawn with its opacity and blend mode' }));
        box.appendChild(r4);
        var r5 = el('div', 'display:flex;flex-wrap:wrap;gap:4px;');
        function B(t, attr, title, fn) { var b = el('button', BTN, t, { type: 'button', 'class': 'layer-act-btn', 'data-pcg': attr, title: title }); b.addEventListener('click', function (ev) { ev.stopPropagation(); ev.preventDefault(); fn(); }); r5.appendChild(b); return b; }
        B('Select', 'select', 'Select every layer in this group', function () { selectGroup(key); });
        B('Ungroup', 'ungroup', 'Dissolve the group; its layers stay where they are', function () { openKey = null; ungroup(key); });
        B('Close', 'close', 'Hide these settings', function () { openKey = null; panel(); });
        box.appendChild(r5);
        return box;
    }
    function selectGroup(key) {
        var m = members(key); if (!m.length) return;
        try {
            _selectedLayerId = m[m.length - 1].id; window._selectedLayerId = _selectedLayerId;
            _selectedLayerIds = new Set(m.map(function (l) { return l.id; }));
        } catch (_e) {}
        panel();
    }
    function decorate() {
        if (off()) return;
        var c = document.getElementById('layerPanelContent'); if (!c) return;
        wirePanel(c);
        injectMenu();
        decorateBar(c);
        var heads = c.querySelectorAll('.layer-group-header');
        if (!heads.length) return;
        if (typeof _layerPanelFilter !== 'undefined' && _layerPanelFilter) return;
        var keys = groupHeaderKeys(c);
        for (var i = 0; i < heads.length; i++) {
            var idx = Number(heads[i].getAttribute('data-layer-group-index')), key = keys[idx];
            if (!key) continue;
            var d = descriptor(key); if (!d) continue;
            var h = heads[i], op = Math.round(Number(d.opacity == null ? 255 : d.opacity) / 255 * 100), bm = d.blendMode && d.blendMode !== 'source-over';
            h.setAttribute('data-pcg-key', key);
            var SHORT = { multiply: 'Mul', screen: 'Scr', overlay: 'Ovl', darken: 'Drk', lighten: 'Lgt', 'color-dodge': 'Ddg', 'color-burn': 'Brn', 'hard-light': 'Hrd', 'soft-light': 'Sft', difference: 'Dif', exclusion: 'Exc', hue: 'Hue', saturation: 'Sat', color: 'Col', luminosity: 'Lum' };
            var tag = (d.mode !== 'pass-through' && (op !== 100 || bm)) ? (op + '%' + (bm ? ' ' + (SHORT[d.blendMode] || '') : '')) : '';
            var gear = el('span', 'cursor:pointer;font-size:10px;padding:0 2px;color:' + (openKey === key ? '#ffd86b' : '#8fa'), '⚙', { 'data-pcg-gear': key, title: 'Group settings: opacity, blend, rename, ungroup', role: 'button', 'aria-label': 'Group settings', tabindex: '0' });
            var last = h.lastElementChild;
            if (tag) h.insertBefore(el('span', 'font-size:8px;color:#ffd86b;margin-left:auto;white-space:nowrap;', tag, { 'data-pcg-tag': key, title: op + '% ' + String(d.blendMode || 'normal').replace('-', ' ') }), last);
            h.insertBefore(gear, last);
            if (openKey === key) { var strip = buildStrip(key); if (strip) h.parentNode.insertBefore(strip, h.nextSibling); }
        }
    }
    var wired = [];
    function wirePanel(c) {
        if (c.__pcgWired === wired) return;
        if (typeof c.__pcgOff === 'function') { try { c.__pcgOff(); } catch (_e) {} }
        c.__pcgWired = wired;
        var hs = [];
        function on(type, fn) { c.addEventListener(type, fn, true); hs.push([type, fn]); }
        c.__pcgOff = function () { hs.forEach(function (h) { c.removeEventListener(h[0], h[1], true); }); hs = []; c.__pcgWired = null; c.__pcgOff = null; };
        wired.push(c);
        function gearHit(ev) { return ev.target && ev.target.closest ? ev.target.closest('[data-pcg-gear]') : null; }
        on('click', function (ev) {
            var g = gearHit(ev); if (!g || off()) return;
            ev.stopPropagation(); ev.preventDefault();
            var k = g.getAttribute('data-pcg-gear'); openKey = openKey === k ? null : k; panel();
        });
        on('keydown', function (ev) {
            var g = gearHit(ev); if (!g || off() || (ev.key !== 'Enter' && ev.key !== ' ')) return;
            ev.stopPropagation(); ev.preventDefault();
            var k = g.getAttribute('data-pcg-gear'); openKey = openKey === k ? null : k; panel();
        });
    }

    // ------------------------------------------------------------------ Actions menu + keys
    function injectMenu(force) {
        var menu = document.getElementById('layerActionsMenu'); if (!menu) return;
        var old = menu.querySelector('[data-pcg-menu]');
        if (old) { if (!force) return; old.parentNode.removeChild(old); }
        var MI = 'display:block;width:100%;text-align:left;font-size:10px;padding:5px 8px;background:transparent;border:none;color:var(--text);border-radius:4px;cursor:pointer;';
        var wrap = el('div', '', null, { 'data-pcg-menu': '1' });
        function item(text, attr, title, fn) {
            var b = el('button', MI, text, { type: 'button', role: 'menuitem', 'data-pcg-act': attr, title: title });
            b.addEventListener('click', function (ev) {
                ev.stopPropagation(); if (off()) return;
                menu.style.display = 'none'; var mb = document.getElementById('layerActionsMenuBtn'); if (mb) mb.setAttribute('aria-expanded', 'false');
                fn();
            });
            wrap.appendChild(b);
        }
        item('Group selected layers', 'group', 'Put the selected layers in a new group (Ctrl+Alt+G). Ctrl-click or Shift-click layers to select several.', function () { var k = groupSelected(); if (k) openKey = k, panel(); });
        item('Take selected out of group', 'ungroup-sel', 'Move the selected layers out of their group (Ctrl+Alt+Shift+G)', function () { removeFromGroup(selectedLayers().map(function (l) { return l.id; })); });
        var anchor = menu.querySelector('[data-pca-menu]');
        if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(wrap, anchor.nextSibling);
        else {
            var items = menu.querySelectorAll('button[role="menuitem"]'), after = null;
            for (var i = 0; i < items.length; i++) if (/Blank layer/i.test(items[i].textContent)) after = items[i];
            if (after && after.parentNode) after.parentNode.insertBefore(wrap, after.nextSibling); else menu.insertBefore(wrap, menu.firstChild);
        }
    }
    function onKey(ev) {
        if (off() || !ev.ctrlKey || !ev.altKey || ev.metaKey) return;
        if (String(ev.key).toLowerCase() !== 'g') return;
        var t = ev.target, tag = t && t.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (t && t.isContentEditable)) return;
        ev.preventDefault(); ev.stopPropagation();
        if (ev.shiftKey) removeFromGroup(selectedLayers().map(function (l) { return l.id; }));
        else { var k = groupSelected(); if (k) { openKey = k; panel(); } }
    }
    document.addEventListener('keydown', onKey, true);
    undoers.push(function () { document.removeEventListener('keydown', onKey, true); });

    // ------------------------------------------------------------------ hooks: heal before every composite and panel render
    var prevRecomp = window.recompositeFromLayers;
    if (typeof prevRecomp === 'function' && !prevRecomp.__pcg) {
        var wrec = function () {
            var changed = false;
            if (!off()) { try { changed = heal(); } catch (e) { try { console.warn('[pcg] heal failed', e); } catch (_e) {} } }
            var r = prevRecomp.apply(this, arguments);
            if (changed) setTimeout(panel, 0);
            return r;
        };
        wrec.__pcg = true;
        for (var kk in prevRecomp) { try { if (Object.prototype.hasOwnProperty.call(prevRecomp, kk)) wrec[kk] = prevRecomp[kk]; } catch (_e) {} }
        window.recompositeFromLayers = wrec;
        undoers.push(function () { if (window.recompositeFromLayers === wrec) window.recompositeFromLayers = prevRecomp; });
    }
    var prevPanel = window.renderLayerPanel;
    if (typeof prevPanel === 'function' && !prevPanel.__pcg) {
        var wpanel = function () {
            if (!off()) { try { heal(); } catch (_e) {} }
            var r = prevPanel.apply(this, arguments);
            if (!off()) { try { decorate(); } catch (e) { try { console.warn('[pcg] decorate failed', e); } catch (_e) {} } }
            return r;
        };
        wpanel.__pcg = true;
        for (var kp in prevPanel) { try { if (Object.prototype.hasOwnProperty.call(prevPanel, kp)) wpanel[kp] = prevPanel[kp]; } catch (_e) {} }
        window.renderLayerPanel = wpanel;
        undoers.push(function () { if (window.renderLayerPanel === wpanel) window.renderLayerPanel = prevPanel; });
    }

    // The layer panel and the move / merge commands refuse to cross a group boundary ("Flatten the group first") because they were written
    // for imported PSD groups. Groups made here are free to cross: a layer moved up / down / dragged into the range of a group joins it, a member
    // moved out leaves it (heal() above decides from what moved). PSD groups keep the old protection.
    var prevBK = window._spbLayerGroupBoundaryKey;
    if (typeof prevBK === 'function' && !prevBK.__pcg) {
        var wbk = function (layer) {
            if (off()) return prevBK.apply(this, arguments);
            var c = chainOf(layer), out = [];
            for (var i = 0; i < c.length; i++) { var k = keyOf(c[i]); if (k.indexOf('pcg_') !== 0) out.push(k); }
            return out.join('>');
        };
        wbk.__pcg = true;
        window._spbLayerGroupBoundaryKey = wbk;
        undoers.push(function () { if (window._spbLayerGroupBoundaryKey === wbk) window._spbLayerGroupBoundaryKey = prevBK; });
    }

    window.SPBPcGroups = {
        version: VERSION, stats: stats, lastKey: null,
        heal: heal, groupIds: groupIds, groupSelected: groupSelected, ungroup: ungroup, removeFromGroup: removeFromGroup,
        setGroup: setGroup, rename: rename, info: info, members: members, groups: allGroups, selectGroup: selectGroup,
        openSettings: function (k) { openKey = k || null; panel(); },
        injectMenu: injectMenu, decorate: decorate,
        uninstall: function () {
            undoers.forEach(function (f) { try { f(); } catch (_e) {} });
            var c = document.getElementById('layerPanelContent'); if (c && typeof c.__pcgOff === 'function') c.__pcgOff();
            var m = document.querySelector('[data-pcg-menu]'); if (m && m.parentNode) m.parentNode.removeChild(m);
            window.SPBPcGroups = null; try { delete window.SPBPcGroups; } catch (_e) {}
        }
    };
    try { injectMenu(); } catch (_e) {}
})();
