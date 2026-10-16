/* [SPB-REV-COLOURWAY 2026-10-10] Colourway Studio, UI. Opens from Adjust > Colourway Studio... (and from the Colourway layer's card).
 * A fixed-position window: nothing in the page layout moves when it opens, and it fits 1100 x 800.
 *   left   the livery palette (roles editable), team colours (2-3 hex codes), sponsor / logo art that stays untouched, finish suggestions
 *   middle the variant grid (client-side thumbnails of the whole sheet, downscaled)
 *   right  the picked colourway at larger size, its colour map, Save As Variant
 * A click on a card applies it to the real layers + zones at once (the Live Preview behind follows); "See Live Preview" docks the window to a small bar.
 * Apply keeps it as ONE undo step; Cancel puts everything back exactly. Kill switch: SPB_REV_COLOURWAY_OFF.
 */
(function (root) {
    'use strict';
    var doc = root && root.document;
    if (!doc || root.SPBRevColourwayUI) return;
    var C = root.SPBRevColourway;
    if (!C || C.off) { root.SPBRevColourwayUI = { off: true }; return; }
    var MA = root.SPBRevColourwayMath;
    var ICON = '<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.25" aria-hidden="true"><circle cx="6" cy="6" r="3.7"/><circle cx="10.2" cy="6.4" r="3.7"/><circle cx="8" cy="10.2" r="3.7"/></svg>';
    var XI = '<svg viewBox="0 0 12 12" width="11" height="11" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M2 2l8 8M10 2l-8 8"/></svg>';
    var P = null, UI = { open: false, docked: false, busy: 0, thumbQ: [], thumbRaf: 0, lastPrev: '' };

    function el(tag, attrs, html) {
        var e = doc.createElement(tag);
        if (attrs) for (var k in attrs) { if (attrs[k] != null) e.setAttribute(k, attrs[k]); }
        if (html != null) e.innerHTML = html;
        return e;
    }
    function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function $(sel) { return P ? P.querySelector(sel) : null; }
    function toast(m, bad) { try { if (typeof root.showToast === 'function') root.showToast(m, !!bad); } catch (_) {} }
    var ROLE_LABEL = { main: 'Main', accent: 'Accent', trim: 'Trim', detail: 'Detail', ink: 'Dark', paper: 'Light', grey: 'Grey' };
    var MAT_LABEL = { candy: 'Candy', pearl: 'Pearl', chrome: 'Chrome', matte: 'Matte', satin: 'Satin', gloss: 'Gloss' };

    // ------------------------------------------------------------------ build
    function build() {
        if (P) return P;
        P = el('div', { class: 'spb-cw', id: 'spbCwStudio', role: 'dialog', 'aria-label': 'Colourway Studio', 'aria-modal': 'false' });
        P.innerHTML =
            '<div class="spb-cw-head"><span class="spb-cw-ico">' + ICON + '</span><span class="spb-cw-ttl">Colourway Studio</span><span class="spb-cw-sub" data-cw="sub"></span>' +
            '<button type="button" class="spb-cw-btn" data-cw="dock" title="Shrink this window to a bar so you can see the Live Preview, then bring it back">See Live Preview</button>' +
            '' + /* [SHINE-OFF 2026-10-11] owner: artificial shine never works; Shine Lens button removed */
            '<button type="button" class="spb-cw-x" data-cw="cancel" aria-label="Close Colourway Studio (Esc)" title="Close and put everything back (Esc)">' + XI + '</button></div>' +
            '<div class="spb-cw-body">' +
              '<div class="spb-cw-side">' +
                '<div class="spb-cw-h">Livery Palette</div><ul class="spb-cw-pal" data-cw="pal"></ul>' +
                '<div class="spb-cw-h">Team Colours</div>' +
                '<div class="spb-cw-team" data-cw="team"></div>' +
                '<div class="spb-cw-h">Sponsor And Logo Art</div><div class="spb-cw-prot" data-cw="prot"></div>' +
                '<label class="spb-cw-chk"><input type="checkbox" data-cw="inc"> Recolour sponsors and logos too</label>' +
                '<div class="spb-cw-h">Finishes</div>' +
                '<label class="spb-cw-chk"><input type="checkbox" data-cw="mats"> Also set a finish per role</label>' +
                '<div class="spb-cw-note" data-cw="matnote">Colour-picked zones follow the new colours either way. This also swaps the base finish of zones: accent to candy, body to gloss, and so on.</div>' +
              '</div>' +
              '<div class="spb-cw-mid"><div class="spb-cw-grid" data-cw="grid" role="listbox" aria-label="Colourways"></div></div>' +
              '<div class="spb-cw-right">' +
                '<div class="spb-cw-big"><canvas data-cw="big" width="720" height="720"></canvas><div class="spb-cw-bigbusy" data-cw="busy">Applying...</div></div>' +
                '<div class="spb-cw-name" data-cw="name"></div>' +
                '<div class="spb-cw-note" data-cw="note"></div>' +
                '<div class="spb-cw-map" data-cw="map"></div>' +
                '<div class="spb-cw-save"><input type="text" data-cw="vname" maxlength="40" placeholder="Name for this colourway" aria-label="Name for this colourway">' +
                '<button type="button" class="spb-cw-btn" data-cw="save">Save As Variant</button></div>' +
              '</div>' +
            '</div>' +
            '<div class="spb-cw-dockbar"><button type="button" class="spb-cw-btn" data-cw="prev" aria-label="Previous colourway">&lt;</button><span class="spb-cw-dname" data-cw="dname"></span><button type="button" class="spb-cw-btn" data-cw="next" aria-label="Next colourway">&gt;</button>' +
              '<button type="button" class="spb-cw-btn" data-cw="undock">Back To Studio</button></div>' +
            '<div class="spb-cw-foot"><span class="spb-cw-status" data-cw="status" aria-live="polite"></span>' +
              '<button type="button" class="spb-cw-btn" data-cw="cancel2">Cancel</button><button type="button" class="spb-cw-btn spb-cw-primary" data-cw="apply">Apply Colourway</button></div>';
        doc.body.appendChild(P);
        P.addEventListener('click', onClick);
        P.addEventListener('change', onChange);
        P.addEventListener('input', onInput);
        P.addEventListener('keydown', onKey);
        return P;
    }

    // ------------------------------------------------------------------ rendering of the sections
    function setStatus(html) { var s = $('[data-cw="status"]'); if (s) s.innerHTML = html || ''; }
    function drawPalette() {
        var st = C.state(), ul = $('[data-cw="pal"]'); if (!st || !ul) return;
        var v = C.variantById(st.activeId) || st.vars[0], html = '';
        st.pal.forEach(function (c, i) {
            var to = v.to[i], changed = to.toLowerCase() !== c.hex.toLowerCase();
            var roles = (c.role === 'ink' || c.role === 'paper' || c.role === 'grey')
                ? '<span class="spb-cw-role fixed">' + ROLE_LABEL[c.role] + '</span>'
                : '<select class="spb-cw-role" data-cw="role" data-i="' + i + '" aria-label="Role of ' + esc(c.name) + '">' + ['main', 'accent', 'trim', 'detail'].map(function (r) { return '<option value="' + r + '"' + (r === c.role ? ' selected' : '') + '>' + ROLE_LABEL[r] + '</option>'; }).join('') + '</select>';
            html += '<li class="spb-cw-pi">' +
                '<span class="spb-cw-sw" style="background:' + c.hex + '" title="' + esc(c.name) + ' ' + c.hex + '"></span>' +
                '<span class="spb-cw-pn"><b>' + esc(c.name) + '</b><i>' + (c.implicit ? 'always kept' : Math.round(c.cov * 100) + '%') + '</i></span>' + roles +
                '<label class="spb-cw-to' + (changed ? ' on' : '') + '" title="Pick the new colour for ' + esc(c.name) + '"><span class="spb-cw-sw" style="background:' + to + '"></span><input type="color" value="' + to + '" data-cw="tocol" data-i="' + i + '" aria-label="New colour for ' + esc(c.name) + '"></label></li>';
        });
        ul.innerHTML = html || '<li class="spb-cw-empty">No colours found on the visible art layers.</li>';
    }
    function drawTeam() {
        var box = $('[data-cw="team"]'); if (!box) return;
        if (box.firstChild) return;   // keep what the user typed
        var h = '';
        ['Main', 'Accent', 'Trim'].forEach(function (n, i) {
            h += '<label class="spb-cw-tm"><span>' + n + '</span><input type="text" data-cw="team" data-i="' + i + '" maxlength="7" placeholder="#rrggbb" spellcheck="false" aria-label="Team ' + n.toLowerCase() + ' colour hex"><i class="spb-cw-sw" data-cw="tsw" data-i="' + i + '"></i></label>';
        });
        box.innerHTML = h + '<button type="button" class="spb-cw-btn" data-cw="teamgo">Make Team Colourway</button>';
    }
    function drawProt() {
        var box = $('[data-cw="prot"]'), st = C.state(); if (!box || !st) return;
        var list = C.layerList().filter(function (l) { return l.def || st.prot.has(l.id) || /sponsor|logo|decal/.test(l.role); });
        if (!list.length) { box.innerHTML = '<div class="spb-cw-note">No sponsor or logo layers found. Everything is recoloured.</div>'; }
        else {
            box.innerHTML = list.map(function (l) {
                return '<label class="spb-cw-chk" title="' + esc(l.name) + '"><input type="checkbox" data-cw="protl" data-id="' + esc(l.id) + '"' + (st.prot.has(l.id) ? ' checked' : '') + (st.inc ? ' disabled' : '') + '> <span class="spb-cw-ln">' + esc(l.name) + '</span><i>' + esc(l.role) + '</i></label>';
            }).join('');
        }
        var inc = $('[data-cw="inc"]'); if (inc) inc.checked = !!st.inc;
    }
    function drawGrid() {
        var st = C.state(), g = $('[data-cw="grid"]'); if (!st || !g) return;
        var html = '';
        st.vars.forEach(function (v) {
            var strip = v.to.map(function (h, i) { return h.toLowerCase() !== st.pal[i].hex.toLowerCase() ? '<i style="background:' + h + '"></i>' : ''; }).join('');
            html += '<div class="spb-cw-card' + (v.id === st.activeId ? ' on' : '') + '" role="option" tabindex="' + (v.id === st.activeId ? 0 : -1) + '" aria-selected="' + (v.id === st.activeId) + '" data-id="' + esc(v.id) + '">' +
                '<canvas width="256" height="256" data-cw="th" data-id="' + esc(v.id) + '"></canvas>' +
                '<div class="spb-cw-cl"><b>' + esc(v.name) + '</b>' + (v.saved ? '<em>Saved</em>' : '') + '</div>' +
                '<div class="spb-cw-strip">' + (v.id === 'orig' ? '<span>As painted</span>' : strip) + (v.lowContrast ? '<u title="Main and accent are close in lightness: they may blend together on track">low contrast</u>' : '') + '</div>' +
                (v.saved ? '<button type="button" class="spb-cw-del" data-cw="del" data-id="' + esc(v.id) + '" aria-label="Delete ' + esc(v.name) + '" title="Delete this saved colourway">' + XI + '</button>' : '') +
                '</div>';
        });
        g.innerHTML = html;
        queueThumbs();
    }
    function queueThumbs() {
        UI.thumbQ = Array.prototype.slice.call(P.querySelectorAll('canvas[data-cw="th"]'));
        if (UI.thumbRaf) return;
        var step = function () {
            UI.thumbRaf = 0;
            if (!UI.open || !C.state()) return;
            var t0 = performance.now();
            while (UI.thumbQ.length && performance.now() - t0 < 24) {
                var c = UI.thumbQ.shift(); try { C.thumbFor(c.getAttribute('data-id'), c); } catch (e) { console.warn('[colourway] thumb', e); }
            }
            if (UI.thumbQ.length) UI.thumbRaf = root.requestAnimationFrame(step);
        };
        UI.thumbRaf = root.requestAnimationFrame(step);
    }
    function drawDetail() {
        var st = C.state(); if (!st) return;
        var v = C.variantById(st.activeId) || st.vars[0];
        var nm = $('[data-cw="name"]'); if (nm) nm.textContent = v.name;
        var dn = $('[data-cw="dname"]'); if (dn) dn.textContent = v.name;
        var nt = $('[data-cw="note"]'); if (nt) nt.textContent = v.note || (v.id === 'orig' ? 'The livery as painted. Pick a colourway on the left to try it.' : (v.saved ? 'A saved colourway. It stays in the project.' : ''));
        var map = $('[data-cw="map"]'), h = '';
        st.pal.forEach(function (c, i) {
            if (v.to[i].toLowerCase() === c.hex.toLowerCase() && v.id !== 'orig') return;
            if (v.id === 'orig' && c.implicit) return;
            var mk = v.mats && v.mats[c.role], mat = mk && C.materialId(mk);
            h += v.id === 'orig' ? '<div class="spb-cw-mr"><i class="spb-cw-sw" style="background:' + c.hex + '"></i><b>' + esc(c.name) + '</b><span class="spb-cw-mat">' + ROLE_LABEL[c.role] + '</span></div>' :
                '<div class="spb-cw-mr"><i class="spb-cw-sw" style="background:' + c.hex + '"></i><span class="spb-cw-ar">to</span><i class="spb-cw-sw" style="background:' + v.to[i] + '"></i>' +
                '<b>' + ROLE_LABEL[c.role] + '</b><span class="spb-cw-mat' + (st.matsOn && mat ? ' on' : '') + '">' + (mat ? esc(MAT_LABEL[mk] || mk) + ' finish' : '') + '</span></div>';
        });
        if (!h) h = '<div class="spb-cw-note">Nothing changes in this colourway.</div>';
        if (map) map.innerHTML = h;
        var sv = $('[data-cw="save"]'), vn = $('[data-cw="vname"]');
        if (sv) sv.disabled = (v.id === 'orig');
        if (vn && !UI.vnameTouched) vn.value = (v.id === 'orig' || v.saved) ? '' : v.name;
        drawBig();
    }
    function drawBig() {
        var st = C.state(); if (!st) return;
        var big = $('[data-cw="big"]'); if (!big) return;
        try { C.previewFor(st.activeId, big, 720); } catch (e) { console.warn('[colourway] preview', e); }
    }
    function drawSub() {
        var st = C.state(), s = $('[data-cw="sub"]'); if (!st || !s) return;
        var n = st.pal.filter(function (c) { return !c.implicit; }).length;
        s.textContent = n + ' livery colours' + (st.prot.size && !st.inc ? ' - ' + st.prot.size + ' sponsor / logo layer' + (st.prot.size > 1 ? 's' : '') + ' kept' : '');
    }
    function statusFor() {
        var st = C.state(); if (!st) return;
        var v = C.variantById(st.activeId), z = st.lastZones || { moved: [], kept: [] }, m = st.lastMats || [];
        if (!v || v.id === 'orig') { setStatus('The livery as painted. Pick a colourway to try it. Nothing is kept until you press Apply.'); return; }
        var parts = [];
        parts.push('<b>' + esc(v.name) + '</b> is showing');
        if (z.moved.length) parts.push(z.moved.length + ' colour-picked zone' + (z.moved.length > 1 ? 's follow' : ' follows') + ' the new colours');
        else parts.push('no colour-picked zones to move');
        if (z.kept.length) parts.push(z.kept.length + ' zone' + (z.kept.length > 1 ? 's' : '') + ' on sponsor art kept');
        if (m.length) parts.push(m.length + ' finish' + (m.length > 1 ? 'es' : '') + ' set');
        setStatus(parts.join(' - '));
    }
    function redrawAll(keepTeam) {
        drawSub(); drawPalette(); if (!keepTeam) drawTeam(); drawProt(); drawGrid(); drawDetail(); statusFor();
    }

    // ------------------------------------------------------------------ actions
    function setBusy(on) {
        UI.busy += on ? 1 : -1; if (UI.busy < 0) UI.busy = 0;
        var b = $('[data-cw="busy"]'); if (b) b.classList.toggle('on', UI.busy > 0);
        if (P) P.classList.toggle('busy', UI.busy > 0);
    }
    function pick(id) {
        var st = C.state(); if (!st || !C.variantById(id)) return;
        st.activeId = id;      // reflect the pick at once; the heavy part (full-size recolour) runs next frame
        syncCards(); drawPalette(); drawDetail();
        setBusy(true);
        root.setTimeout(function () {
            try { C.setVariant(id); } catch (e) { console.error('[colourway] apply', e); toast('Colourway could not be applied: ' + (e && e.message || e), true); }
            setBusy(false); statusFor();
        }, 20);
    }
    function syncCards() {
        var st = C.state(); if (!st) return;
        Array.prototype.forEach.call(P.querySelectorAll('.spb-cw-card'), function (c) {
            var on = c.getAttribute('data-id') === st.activeId;
            c.classList.toggle('on', on); c.setAttribute('aria-selected', on ? 'true' : 'false'); c.tabIndex = on ? 0 : -1;
        });
    }
    function step(dir) {
        var st = C.state(); if (!st) return;
        var i = st.vars.findIndex(function (v) { return v.id === st.activeId; });
        var n = st.vars.length; pick(st.vars[(i + dir + n) % n].id);
    }
    function teamValues() {
        return Array.prototype.map.call(P.querySelectorAll('input[data-cw="team"]'), function (i) {
            var v = String(i.value || '').trim(); if (/^[0-9a-f]{6}$/i.test(v)) v = '#' + v; return MA.isHex(v) ? v.toLowerCase() : '';
        }).filter(Boolean);
    }
    function onClick(e) {
        var t = e.target, act = t.closest && t.closest('[data-cw]'), key = act && act.getAttribute('data-cw');
        var card = t.closest && t.closest('.spb-cw-card');
        if (key === 'del') { e.stopPropagation(); C.deleteVariant(act.getAttribute('data-id')); redrawAll(true); return; }
        if (card && !key) { pick(card.getAttribute('data-id')); card.focus(); return; }
        if (card && key === 'th') { pick(card.getAttribute('data-id')); return; }
        switch (key) {
            case 'cancel': case 'cancel2': close(false); break;
            case 'apply': close(true); break;
            case 'dock': dock(true); break;
            case 'undock': dock(false); break;
            case 'prev': step(-1); break;
            case 'next': step(1); break;
            case 'lens': toggleLens(); break;
            case 'save': {
                var nm = ($('[data-cw="vname"]') || {}).value || '';
                var r = C.saveVariant(nm);
                if (r) { UI.vnameTouched = false; redrawAll(true); setStatus('Saved <b>' + esc(r.name) + '</b>. Switch back to it any time from this window or the Colourway layer.'); }
                break;
            }
            case 'teamgo': {
                var vals = teamValues();
                if (!vals.length) { setStatus('Type 2 or 3 hex codes first, for example #c8102e.'); break; }
                C.setTeam(vals); redrawAll(true); pick('team');
                break;
            }
        }
    }
    function onChange(e) {
        var t = e.target, key = t.getAttribute && t.getAttribute('data-cw');
        if (key === 'role') { setBusy(true); root.setTimeout(function () { C.setRole(+t.getAttribute('data-i'), t.value); setBusy(false); redrawAll(true); }, 10); }
        else if (key === 'tocol') { setBusy(true); root.setTimeout(function () { C.editColour(+t.getAttribute('data-i'), t.value); setBusy(false); redrawAll(true); }, 10); }
        else if (key === 'protl' || key === 'inc') {
            var ids = Array.prototype.filter.call(P.querySelectorAll('input[data-cw="protl"]'), function (i) { return i.checked; }).map(function (i) { return i.getAttribute('data-id'); });
            var inc = !!($('[data-cw="inc"]') || {}).checked;
            setStatus('Working out which pixels belong to the sponsor art...');
            setBusy(true);
            root.setTimeout(function () { C.setProtected(ids, inc); setBusy(false); redrawAll(true); }, 30);
        }
        else if (key === 'mats') {
            C.setMaterials(t.checked); var st = C.state();
            if (st && st.activeId !== 'orig') pick(st.activeId); else drawDetail();
        }
    }
    function onInput(e) {
        var t = e.target;
        if (t.getAttribute && t.getAttribute('data-cw') === 'team') {
            var v = String(t.value || '').trim(); if (/^[0-9a-f]{6}$/i.test(v)) v = '#' + v;
            var sw = P.querySelector('i[data-cw="tsw"][data-i="' + t.getAttribute('data-i') + '"]'); if (sw) sw.style.background = MA.isHex(v) ? v : 'transparent';
        } else if (t.getAttribute && t.getAttribute('data-cw') === 'vname') UI.vnameTouched = true;
    }
    function onKey(e) {
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(false); return; }
        var card = e.target.closest && e.target.closest('.spb-cw-card');
        if (card && /^Arrow(Left|Right|Up|Down)$/.test(e.key)) {
            e.preventDefault();
            var d = (e.key === 'ArrowLeft' || e.key === 'ArrowUp') ? -1 : 1, cards = Array.prototype.slice.call(P.querySelectorAll('.spb-cw-card')), i = cards.indexOf(card);
            var n = cards[(i + d + cards.length) % cards.length]; if (n) { n.focus(); pick(n.getAttribute('data-id')); }
        } else if (card && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); pick(card.getAttribute('data-id')); }
        else if (e.key === 'Enter' && e.target.getAttribute && e.target.getAttribute('data-cw') === 'team') { e.preventDefault(); onClick({ target: P.querySelector('[data-cw="teamgo"]'), stopPropagation: function () {} }); }
    }
    function dock(on) {
        UI.docked = !!on; if (P) P.classList.toggle('docked', UI.docked);
        if (on) { try { if (root.SPBRevLens && root.SPBRevLens.refresh) root.SPBRevLens.refresh(); } catch (_) {} var b = $('[data-cw="undock"]'); if (b) b.focus(); }
        else { var c = $('.spb-cw-card.on'); if (c) c.focus(); }
    }
    function toggleLens() {
        var L = root.SPBRevLens; if (!L || L.off || typeof L.setMode !== 'function') { toast('Shine Lens is not available in this build.', true); return; }
        var m = L.getMode(); L.setMode(m === 'off' ? 'lens' : 'off'); dock(true);
    }

    // ------------------------------------------------------------------ open / close
    function open() {
        if (UI.open) { if (P) P.style.display = 'flex'; return true; }
        if (root.SPB_REV_COLOURWAY_OFF) return false;
        build();
        var st = C.open();
        if (!st) return false;
        UI.open = true; UI.docked = false; UI.vnameTouched = false;
        P.classList.remove('docked'); P.style.display = 'flex'; P.classList.add('open');
        var team = P.querySelector('[data-cw="team"]'); if (team) team.innerHTML = '';
        var mats = $('[data-cw="mats"]'); if (mats) mats.checked = !!st.matsOn;
        redrawAll(false);
        setStatus(st.activeId === 'orig' ? 'Found ' + st.pal.filter(function (c) { return !c.implicit; }).length + ' livery colours in ' + Math.round(st.t.total) + ' ms. Pick a colourway; nothing is kept until you press Apply.' : '');
        if (st.activeId !== 'orig') statusFor();
        root.setTimeout(function () { var c = $('.spb-cw-card.on'); if (c) c.focus(); }, 30);
        return true;
    }
    function close(keep) {
        if (!UI.open) return;
        var r = C.close(!!keep);
        UI.open = false; UI.docked = false;
        if (P) { P.style.display = 'none'; P.classList.remove('open'); P.classList.remove('docked'); }
        if (keep) toast(r.changed ? 'Colourway applied. Ctrl+Z puts the old colours back in one step.' : 'No change to apply.');
        else toast('Colourway Studio closed. Nothing was changed.');
    }

    // ------------------------------------------------------------------ menu + layer card + keys
    function menuButton() {
        var b = el('button', { type: 'button', class: 'vtool-btn spb-cw-menu', 'data-spb-colourway': '1', title: 'Colourway Studio: make the same livery in several colourways (teammates, sponsors, a night race); the layers and the zones both follow', 'aria-label': 'Colourway Studio' },
            '<span class="spb-mi-ico spb-cw-mi">' + ICON + '</span> Colourway Studio...');
        b.addEventListener('click', function (e) {
            e.preventDefault(); e.stopPropagation();
            var det = b.closest('details'); if (det) det.removeAttribute('open');
            open();
        });
        return b;
    }
    function inject() {
        var sums = doc.querySelectorAll('details.spb-tb-menu > summary');
        for (var i = 0; i < sums.length; i++) {
            if (!/^\s*Adjust/i.test(sums[i].textContent || '')) continue;
            var pop = sums[i].parentNode.querySelector('.spb-tb-pop');
            if (!pop) return false;
            if (!pop.querySelector('[data-spb-colourway]')) {
                var sep = el('div', { class: 'spb-tb-pop-sep', role: 'separator' }); pop.appendChild(sep); pop.appendChild(menuButton());
            }
            return true;
        }
        return false;
    }
    function init() {
        var tries = 0;
        if (!inject()) { var t = setInterval(function () { if (inject() || ++tries > 60) clearInterval(t); }, 1000); }
    }
    root.SPBRevColourwayUI = { version: 'cwui-1', open: open, close: close, dock: dock, isOpen: function () { return UI.open; }, pick: pick, panel: function () { return P; }, state: UI, _inject: inject };
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init); else init();
})(typeof window !== 'undefined' ? window : null);
