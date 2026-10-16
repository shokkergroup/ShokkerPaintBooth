/* [SPB-POLISH-B 2026-10-09] UI polish wave 2 - the few things CSS cannot do.
   (1) Tool-options band: when the active tool has no options the band is empty; this writes the tool's name + a one-line hint
       into two data-* attributes on the band, and the stylesheet paints them (::before / ::after). No child nodes are added,
       so js/canvas/tool-options-split.js still sees an empty band and keeps its own bookkeeping.
   (2) Emoji-as-icons: wraps a LEADING emoji of short labels (buttons, menu rows, headings, toasts) in <span class="spb-pb-emo">;
       the stylesheet hides that span while the polish is on. textContent is unchanged, so no handler that reads a label breaks,
       and the polish kill switch (body.spb-polish-off) brings the emoji straight back.
   (3) Right-click menus that open near the window edge (#layerCtxMenu) are nudged back inside the window.
   Pure presentation. Kill switch: document.body.classList.add('spb-polish-off')  /  'spb-polish-b-off'. */
(function () {
    'use strict';
    if (window.__spbPolishB) return;
    window.__spbPolishB = true;
    var doc = document;

    function polishOn() {
        var b = doc.body;
        return !!b && !b.classList.contains('spb-polish-off') && !b.classList.contains('spb-polish-b-off');
    }

    /* ---------------------------------------------------------------- (1) tool hint */
    var lastKey = '';
    function toolInfo() {
        var mode = window.canvasMode, g = window.TOOL_GUIDE || {};
        var rec = mode && g[mode];
        var name = '', tip = '';
        if (rec && rec.length) {
            name = String(rec[0] || '');
            tip = String(rec[1] || '');
        }
        if (!name) {
            var act = doc.querySelector('#spbTopToolbar .vtool-btn.active .spb-ti-lbl, .spb-top-toolbar .vtool-btn.active .spb-ti-lbl');
            if (act) name = (act.textContent || '').trim();
        }
        // "...as your foreground color.   [ P ]" -> "...as your foreground color.  Shortcut P"
        var m = /\s*\[\s*([^\]]{1,24}?)\s*\]\s*$/.exec(tip);
        if (m) tip = tip.slice(0, m.index).replace(/\s+$/, '') + '   ·   Shortcut ' + m[1];
        tip = tip.replace(/\s+/g, ' ').trim();
        return { name: name, tip: tip };
    }
    function updateHint() {
        var band = doc.getElementById('spbToolRowTop');
        if (!band) return;
        var info = toolInfo();
        var key = (window.canvasMode || '') + '|' + info.name + '|' + info.tip;
        if (key === lastKey && band.getAttribute('data-spb-name') != null) return;
        lastKey = key;
        if (info.name) band.setAttribute('data-spb-name', info.name); else band.removeAttribute('data-spb-name');
        if (info.tip) band.setAttribute('data-spb-tip', info.tip); else band.removeAttribute('data-spb-tip');
    }
    /* the one-line "Layer mode / Drawing for" strip ellipsizes its long hint in narrow windows: keep the full text as a tooltip */
    function syncHintTitle() {
        var h = doc.getElementById('drawZoneHint');
        if (!h) return;
        var t = (h.textContent || '').replace(/\s+/g, ' ').trim();
        if (t) { if (h.title !== t) h.title = t; } else if (h.title) { h.removeAttribute('title'); }
    }

    /* ---------------------------------------------------------------- (2) emoji scrub */
    var RE_LEAD = null;
    try { RE_LEAD = new RegExp('^(\\s*)((?:\\p{Extended_Pictographic}[\\uFE0F\\u200D\\u{1F3FB}-\\u{1F3FF}]*\\s*)+)', 'u'); } catch (e) { RE_LEAD = null; }
    var ROOTS = '#swatchPopup,#shokkLibraryModal,#spbProjectsModal,#spbEnc,#settingsDropdown,#rightPanel,#leftPanel,#zoneEditorFloat,.spb-tb-pop,#layerActionsMenu,#layerCtxMenu,#canvasContextMenu,#undoHistoryPanel,#toast,#spbStaleBanner,#spbTopToolbar,.spb-top-toolbar,.header,#previewBottomBar,.workbench-command-bar,#splitViewContainer,.modal-overlay,.preset-gallery-overlay,.finish-browser-overlay,.finish-compare-overlay,.dual-shift-overlay,.tmpl-name-overlay,.file-picker-overlay,#saveShokkModal,#shortcutOverlay,#layerEffectsDialog';
    var SKIP = 'script,style,textarea,input,select,option,canvas,code,pre,[contenteditable],.layer-name,.zone-name,.shokk-card-name,.spb-pb-emo,.spb-pb-emo-solo,[class*="spb-pai"],[id*="spbProAI"],[class*="spb-cs"],[class*="spb-easy"]';
    function scrubText(tn) {
        if (!RE_LEAD || !tn || tn.nodeType !== 3) return;
        var t = tn.nodeValue;
        if (!t || t.length > 90) return;
        var m = RE_LEAD.exec(t);
        if (!m) return;
        var p = tn.parentNode;
        if (!p || p.nodeType !== 1) return;
        if (p.closest(SKIP)) return;
        if (!p.closest(ROOTS)) return;
        var rest = t.slice(m[0].length);
        var span = doc.createElement('span');
        span.setAttribute('aria-hidden', 'true');
        span.textContent = m[2];
        var wordsHere = /[A-Za-z]{2}/.test(rest);
        // a button / link that holds ONLY an emoji is an icon button: it keeps its glyph (greyed), it is never emptied
        var interactive = /^(BUTTON|A|SUMMARY|LABEL)$/.test(p.tagName) || p.getAttribute('role') === 'button' || /(^|[\s_-])(dot|badge|status|icon|ico)([\s_-]|$)/i.test(String(p.className || ''));
        if (!wordsHere && !interactive) {
            // an emoji in its own little span next to real words ("<span>X</span> Label") is a decoration: hide it too
            var host = p;
            if (p.childNodes.length === 1 && p.parentElement && p.parentElement !== doc.body) host = p.parentElement;
            if (host !== p && /[A-Za-z]{2}/.test((host.textContent || '').replace(t, ''))) wordsHere = true;
        }
        if (!wordsHere) {
            // icon-only label: keep the glyph, but monochrome (the stylesheet greys it)
            span.className = 'spb-pb-emo-solo';
            span.textContent = m[0].replace(/^\s+/, '');
            tn.nodeValue = m[1] + '';
            p.insertBefore(span, tn.nextSibling);
            if (rest) p.insertBefore(doc.createTextNode(rest), span.nextSibling);
            return;
        }
        span.className = 'spb-pb-emo';
        tn.nodeValue = m[1] + rest;
        p.insertBefore(span, tn);
    }
    function scrubTree(root) {
        if (!root || !RE_LEAD) return;
        if (root.nodeType === 3) { scrubText(root); return; }
        if (root.nodeType !== 1) return;
        if (root.closest && root.closest(SKIP)) return;
        var w = doc.createTreeWalker(root, 4, null);
        var n, list = [];
        while ((n = w.nextNode())) {
            var v = n.nodeValue;
            if (v && v.length <= 90) list.push(n);
            if (list.length > 4000) break;
        }
        for (var i = 0; i < list.length; i++) scrubText(list[i]);
    }

    /* ---------------------------------------------------------------- (3) keep right-click menus on screen */
    function clampMenu(el) {
        if (!el || el.nodeType !== 1) return;
        var r = el.getBoundingClientRect();
        if (!r.width) return;
        var vw = window.innerWidth, vh = window.innerHeight, m = 8;
        var left = parseFloat(el.style.left), top = parseFloat(el.style.top);
        if (isNaN(left) || isNaN(top)) return;
        var nl = left, nt = top;
        if (r.right > vw - m) nl = Math.max(m, vw - r.width - m);
        if (r.bottom > vh - m) nt = Math.max(m, vh - r.height - m);
        if (nl !== left) el.style.left = nl + 'px';
        if (nt !== top) el.style.top = nt + 'px';
    }

    /* ---------------------------------------------------------------- observers */
    var queue = [], scheduled = false;
    function flush() {
        scheduled = false;
        var q = queue; queue = [];
        if (!polishOn()) return;
        for (var i = 0; i < q.length; i++) {
            var n = q[i];
            if (n.nodeType === 1 && n.id === 'layerCtxMenu') clampMenu(n);
            if (n.isConnected !== false) scrubTree(n);
        }
    }
    function enqueue(n) {
        queue.push(n);
        if (!scheduled) { scheduled = true; (window.requestAnimationFrame || setTimeout)(flush, 16); }
    }
    function start() {
        if (!doc.body) return;
        updateHint();
        setInterval(function () { if (polishOn()) { updateHint(); syncHintTitle(); } }, 350);
        doc.addEventListener('click', function () { setTimeout(updateHint, 60); }, true);
        doc.addEventListener('keydown', function () { setTimeout(updateHint, 80); }, true);
        try {
            var mo = new MutationObserver(function (muts) {
                for (var i = 0; i < muts.length; i++) {
                    var m = muts[i];
                    if (m.type === 'childList') {
                        for (var j = 0; j < m.addedNodes.length; j++) {
                            var a = m.addedNodes[j];
                            if (a.nodeType === 1 && a.classList && (a.classList.contains('spb-pb-emo') || a.classList.contains('spb-pb-emo-solo'))) continue;
                            enqueue(a);
                        }
                    } else if (m.type === 'characterData') {
                        enqueue(m.target);
                    }
                }
            });
            mo.observe(doc.body, { childList: true, subtree: true, characterData: true });
        } catch (e) {}
        // first pass over what is already on the page
        setTimeout(function () { if (polishOn()) scrubTree(doc.body); }, 900);
        setTimeout(function () { if (polishOn()) scrubTree(doc.body); }, 4000);
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', start); else start();
})();
