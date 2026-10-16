/* pc-text-edit.js - [SPB-TFX2 2026-10-09 TA-034] LIVE, RE-EDITABLE TEXT LAYERS.
 *
 * Audit finding: text became pixels the moment it was committed and double-clicking it opened a NEW empty
 * box (no way to fix a typo / change font, size, colour); typing happened in a plain textarea, so the real
 * font / stroke / effect were only visible after commit.
 *
 * What this module does (Photoshop "Type layer" behaviour):
 *   - the text payload {text,font,size,fill,stroke,strokeWidth,bold,italic,spacing,lineHeight,transform,
 *     effect,align} lives ON the layer's pixel canvas (img.__spbText). Every undo/redo snapshot already
 *     retains img by reference, so the payload travels with undo/redo for free, and ANY operation that
 *     replaces the pixels (a brush stroke, a pixel transform, merge...) yields a fresh canvas WITHOUT the
 *     payload = the layer is rasterized exactly then ("paint over it"). Ctrl+Z gives the live text back.
 *   - clicking (or double-clicking) a live text layer with the Text tool re-opens it: the textarea is
 *     pre-filled, the Text options bar is loaded with the layer's font/size/colours, and the layer is
 *     re-rendered IN PLACE while you type or change an option (WYSIWYG, real font/stroke/effect).
 *   - Enter commits (Shift+Enter = new line), Esc cancels, clicking elsewhere commits. One undo step.
 *   - explicit "Rasterize Type" = SPBTextEdit.rasterize(layer) (undoable).
 *   - project files: spb-projects.js writes record.textData and restores img.__spbText on load; files
 *     written before this change simply have no textData and load as plain pixel layers.
 * Kill switch: window.SPB_TFX2_OFF = true (or localStorage SPB_TFX2_OFF='1') -> old click-to-new-box flow.
 */
(function () {
    'use strict';
    if (window.SPBTextEdit) return;
    try { if (window.localStorage && localStorage.getItem('SPB_TFX2_OFF') === '1') window.SPB_TFX2_OFF = true; } catch (_) {}

    var $ = function (id) { return document.getElementById(id); };
    var sess = null;
    var STYLE_ID = '_spbTextEditStyle';

    function clone(o) { return JSON.parse(JSON.stringify(o)); }
    function layersArr() { return (typeof _psdLayers !== 'undefined' && Array.isArray(_psdLayers)) ? _psdLayers : (window._psdLayers || []); }
    function toast(msg, kind) { try { if (typeof showToast === 'function') showToast(msg, kind); } catch (_) {} }
    function setActiveFlag(v) { try { _textInputActive = !!v; } catch (_) {} }

    // ------------------------------------------------------------------ controls <-> payload
    function readControls() {
        var g = function (id) { return $(id); };
        var iv = function (id, d) { var e = g(id); if (!e || e.value === '') return d; var n = parseInt(e.value, 10); return isFinite(n) ? n : d; };
        var fv = function (id, d) { var e = g(id); if (!e || e.value === '') return d; var n = parseFloat(e.value); return isFinite(n) ? n : d; };
        var sv = function (id, d) { var e = g(id); return (e && e.value) ? e.value : d; };
        return {
            font: sv('textFont', 'Impact'),
            size: iv('textSize', 120),
            fill: sv('textFillColor', '#ffffff'),
            stroke: sv('textStrokeColor', '#000000'),
            strokeWidth: iv('textStrokeWidth', 3),
            bold: !!(g('textBold') && g('textBold').checked),
            italic: !!(g('textItalic') && g('textItalic').checked),
            spacing: iv('textLetterSpacing', 0),
            lineHeight: fv('textLineHeight', 1.2),
            transform: sv('textTransform', 'none'),
            effect: sv('textEffect', 'none'),
            align: sv('textAlign', 'left')
        };
    }
    function writeControls(td) {
        var set = function (id, v, isCheck) {
            var e = $(id); if (!e) return;
            if (isCheck) { e.checked = !!v; return; }
            if (e.tagName === 'SELECT') {
                var has = false;
                for (var i = 0; i < e.options.length; i++) if (e.options[i].value === String(v)) { has = true; break; }
                if (!has) { var o = document.createElement('option'); o.value = String(v); o.textContent = String(v); e.appendChild(o); }
            }
            e.value = String(v);
        };
        set('textFont', td.font); set('textSize', td.size); set('textFillColor', td.fill); set('textStrokeColor', td.stroke);
        set('textStrokeWidth', td.strokeWidth); set('textBold', td.bold, true); set('textItalic', td.italic, true);
        set('textLetterSpacing', td.spacing); set('textLineHeight', td.lineHeight); set('textTransform', td.transform);
        set('textEffect', td.effect); set('textAlign', td.align || 'left');
    }

    // ------------------------------------------------------------------ renderer (port of the old commitText)
    function applyTransform(text, tr) {
        if (tr === 'uppercase') return text.toUpperCase();
        if (tr === 'lowercase') return text.toLowerCase();
        if (tr === 'capitalize') return text.replace(/\b\w/g, function (c) { return c.toUpperCase(); });
        return text;
    }
    function layoutOf(td) {
        var lines = applyTransform(td.text, td.transform).split('\n');
        var size = td.size, sw = td.strokeWidth;
        var fontStyle = (td.italic ? 'italic ' : '') + (td.bold ? 'bold ' : '') + size + 'px "' + td.font + '"';
        var lhp = Math.round(size * td.lineHeight);
        var mc = document.createElement('canvas').getContext('2d');
        mc.font = fontStyle;
        var lineW = [], maxLW = 0;
        for (var i = 0; i < lines.length; i++) {
            var lw = mc.measureText(lines[i]).width + td.spacing * Math.max(0, lines[i].length - 1);
            lineW.push(lw); if (lw > maxLW) maxLW = lw;
        }
        var effectPad = (td.effect !== 'none') ? size * 0.15 + 8 : 0;
        return {
            lines: lines, fontStyle: fontStyle, lhp: lhp, lineW: lineW, maxLW: maxLW, effectPad: effectPad,
            tw: Math.ceil(maxLW) + sw * 2 + 20 + effectPad * 2,
            th: lhp * lines.length + sw * 2 + 20 + effectPad * 2,
            textX: sw + 10 + effectPad, textY: sw + 8 + effectPad
        };
    }
    function drawSpaced(ctx, stroke, text, x, y, sp) {
        if (!sp) { if (stroke) ctx.strokeText(text, x, y); else ctx.fillText(text, x, y); return; }
        var cx = x;
        for (var i = 0; i < text.length; i++) {
            if (stroke) ctx.strokeText(text[i], cx, y); else ctx.fillText(text[i], cx, y);
            cx += ctx.measureText(text[i]).width + sp;
        }
    }
    function render(td) {
        var lay = layoutOf(td);
        if (!lay.lines.some(function (l) { return l.length > 0; })) return null;
        var cv = document.createElement('canvas'); cv.width = lay.tw; cv.height = lay.th;
        // [SPB-TFX1 2026-10-09 TA-034b] Ctrl+T rotation keeps the text live: payload.angle (degrees) is drawn as real vector text on a canvas the size of
        // the rotated box (no bitmap resample); 0 / missing = the old upright canvas, byte for byte.
        var ang = Number(td.angle) || 0, rotated = (ang % 360 !== 0);
        if (rotated) {
            var rad0 = ang * Math.PI / 180, ca = Math.abs(Math.cos(rad0)), sa = Math.abs(Math.sin(rad0)), pad0 = (ang % 90 !== 0) ? 2 : 0;
            cv.width = Math.max(1, Math.ceil(lay.tw * ca + lay.th * sa - 1e-9)) + pad0 * 2;
            cv.height = Math.max(1, Math.ceil(lay.tw * sa + lay.th * ca - 1e-9)) + pad0 * 2;
        }
        var r = cv.getContext('2d');
        if (rotated) { r.translate(cv.width / 2, cv.height / 2); r.rotate(ang * Math.PI / 180); r.translate(-lay.tw / 2, -lay.th / 2); }
        r.font = lay.fontStyle; r.textBaseline = 'top';
        var size = td.size, sw = td.strokeWidth, eff = td.effect, sp = td.spacing;
        var xo = function (li) {
            if (td.align === 'center') return (lay.maxLW - lay.lineW[li]) / 2;
            if (td.align === 'right') return lay.maxLW - lay.lineW[li];
            return 0;
        };
        var each = function (stroke, dx, dy) {
            for (var li = 0; li < lay.lines.length; li++) drawSpaced(r, stroke, lay.lines[li], lay.textX + xo(li) + dx, lay.textY + li * lay.lhp + dy, sp);
        };
        if (eff === 'shadow') {
            r.save(); r.shadowColor = 'rgba(0,0,0,0.7)'; r.shadowBlur = size * 0.08; r.shadowOffsetX = size * 0.04; r.shadowOffsetY = size * 0.04;
        } else if (eff === 'glow') {
            r.save(); r.shadowColor = td.fill; r.shadowBlur = size * 0.15; r.shadowOffsetX = 0; r.shadowOffsetY = 0;
        } else if (eff === 'neon') {
            r.save();
            for (var pass = 3; pass >= 1; pass--) {
                r.shadowColor = td.fill; r.shadowBlur = size * 0.06 * pass; r.globalAlpha = 0.3; r.fillStyle = td.fill;
                each(false, 0, 0);
            }
            r.globalAlpha = 1.0; r.restore();
            r.save(); r.shadowColor = '#fff'; r.shadowBlur = size * 0.03;
        } else if (eff === 'emboss') {
            r.save();
            r.fillStyle = 'rgba(0,0,0,0.5)'; each(false, 2, 2);
            r.fillStyle = 'rgba(255,255,255,0.4)'; each(false, -1, -1);
            r.restore();
        }
        if (sw > 0) {
            r.strokeStyle = td.stroke; r.lineWidth = sw * 2; r.lineJoin = 'round';
            each(true, 0, 0);
        }
        r.fillStyle = td.fill; each(false, 0, 0);
        if (eff === 'shadow' || eff === 'glow' || eff === 'neon') r.restore();
        return { canvas: cv, lay: lay };
    }
    function anchorLeft(td, lay) { return td.align === 'center' ? lay.tw / 2 : (td.align === 'right' ? lay.tw - lay.textX : lay.textX); }
    function layerName(td) {
        var first = applyTransform(td.text, 'none').split('\n');
        return 'Text: ' + first[0].substring(0, 20) + (first.length > 1 ? '...' : '');
    }

    // ------------------------------------------------------------------ queries
    function payload(layer) { return (layer && layer.img && layer.img.__spbText) || null; }
    function isTextLayer(layer) { return !!payload(layer); }

    function hitTextLayer(x, y) {
        var L = layersArr(), sel = null;
        try { sel = L.find(function (l) { return l.id === _selectedLayerId; }); } catch (_) {}
        var scratch = document.createElement('canvas'); scratch.width = 11; scratch.height = 11;
        var sc = scratch.getContext('2d', { willReadFrequently: true });
        for (var i = L.length - 1; i >= 0; i--) {
            var l = L[i];
            if (!l || l.visible === false || !payload(l) || !l.bbox) continue;
            var b = l.bbox;
            if (x < b[0] - 5 || y < b[1] - 5 || x > b[2] + 5 || y > b[3] + 5) continue;
            if (l === sel && x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3]) return l;   // inside the selected text box = hit
            sc.clearRect(0, 0, 11, 11);
            try { sc.drawImage(l.img, b[0] - (x - 5), b[1] - (y - 5)); } catch (_) { continue; }
            var d = sc.getImageData(0, 0, 11, 11).data;
            for (var k = 3; k < d.length; k += 4) if (d[k] > 16) return l;
        }
        return null;
    }

    // ------------------------------------------------------------------ session
    var CTRL_IDS = { textFont: 1, textSize: 1, textFillColor: 1, textStrokeColor: 1, textStrokeWidth: 1, textBold: 1, textItalic: 1,
        textLetterSpacing: 1, textLineHeight: 1, textTransform: 1, textEffect: 1, textAlign: 1 };
    function isTextControl(t) {
        if (!t || t.nodeType !== 1) return false;
        if (t.id && CTRL_IDS[t.id]) return true;
        return !!(t.closest && t.closest('#textToolOptions, #spbTextPrimary'));
    }
    function ensureStyle() {
        if ($(STYLE_ID)) return;
        var st = document.createElement('style'); st.id = STYLE_ID;
        // global textarea theming (paint-booth-v2.css / look themes) must not paint a box or ghost text over the live render
        st.textContent = 'textarea#_spbTextEdit{position:fixed!important;z-index:99999!important;background:transparent!important;color:transparent!important;' +
            '-webkit-text-fill-color:transparent!important;caret-color:#00e5ff!important;border:0!important;border-radius:0!important;box-shadow:none!important;' +
            'outline:1px dashed #00e5ff!important;outline-offset:3px!important;padding:0!important;margin:0!important;resize:none!important;' +
            'overflow:hidden!important;white-space:pre!important;min-height:0!important;max-width:none!important;max-height:none!important;box-sizing:content-box!important;}' +
            'textarea#_spbTextEdit::selection{background:rgba(0,229,255,.35)!important;color:transparent!important;}' +
            'textarea#_spbTextEdit::placeholder{color:rgba(0,229,255,.75)!important;-webkit-text-fill-color:rgba(0,229,255,.75)!important;font:12px sans-serif!important;letter-spacing:0!important;}';
        document.head.appendChild(st);
    }

    // [SPB-TFX1 2026-10-09 TA-034b] an edit session shows the text upright; put the stored rotation back (same centre) when it ends
    // pivot = the centre of the rotated layer before the session: the upright centre moved by (dx,dy) while editing (the text grew
    // from its anchor), so the rotated centre moves by the same vector turned by the angle (the text grows ALONG its own direction)
    function applyAngle(layer, ang, pivot) {
        var td = clone(payload(layer)); td.angle = ang;
        var r = render(td); if (!r) return;
        var b = layer.bbox, cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
        if (pivot) {
            var rad = ang * Math.PI / 180, dx = cx - pivot[0], dy = cy - pivot[1];
            cx = pivot[0] + dx * Math.cos(rad) - dy * Math.sin(rad); cy = pivot[1] + dx * Math.sin(rad) + dy * Math.cos(rad);
        }
        r.canvas.__spbText = Object.freeze(td);
        layer.img = r.canvas;
        var bx = Math.round(cx - r.canvas.width / 2), by = Math.round(cy - r.canvas.height / 2);
        layer.bbox = [bx, by, bx + r.canvas.width, by + r.canvas.height];
    }
    function layerStateOf(layer) {
        return { img: layer.img, bbox: layer.bbox.slice(), name: layer.name, path: layer.path };
    }
    function restoreState(layer, st) { layer.img = st.img; layer.bbox = st.bbox.slice(); layer.name = st.name; layer.path = st.path; }

    function bumpAndRecomposite() {
        window._spbLayerRev = (window._spbLayerRev || 0) + 1;
        try { if (typeof invalidateLayerVisibleContributionCache === 'function') invalidateLayerVisibleContributionCache(); } catch (_) {}
        try { if (typeof recompositeFromLayers === 'function') recompositeFromLayers(); } catch (_) {}
    }
    function afterCommitRefresh(switchTab) {
        bumpAndRecomposite();
        try { if (typeof renderLayerPanel === 'function') renderLayerPanel(); } catch (_) {}
        try { if (typeof drawLayerBounds === 'function') drawLayerBounds(); } catch (_) {}
        if (switchTab) { try { if (typeof switchRightTab === 'function') switchRightTab('layers'); } catch (_) {} }
        try { if (typeof triggerPreviewRender === 'function') triggerPreviewRender(); } catch (_) {}
    }

    function canvasScale() {
        var pc = $('paintCanvas'); if (!pc) return null;
        var r = pc.getBoundingClientRect(); if (!r.width) return null;
        return { rect: r, s: r.width / pc.width };
    }

    function currentTd(s) {
        var td = readControls();
        td.text = s.ta.value.replace(/\r/g, '');
        return td;
    }

    function layoutTextarea(s, td, lay) {
        var cs = canvasScale(); if (!cs) return;
        var ta = s.ta, k = cs.s;
        var fs = Math.max(6, td.size * k);
        var imp = function (prop, v) { ta.style.setProperty(prop, v, 'important'); };
        imp('font', (td.italic ? 'italic ' : '') + (td.bold ? 'bold ' : '') + fs + 'px "' + td.font + '"');
        imp('letter-spacing', (td.spacing * k) + 'px');
        imp('line-height', (lay.lhp * k) + 'px');
        imp('text-align', td.align || 'left');
        var wCss = Math.max(90, (lay.maxLW + td.size * 0.6) * k);
        var hCss = Math.max(lay.lhp * k, lay.lhp * lay.lines.length * k);
        var axScreen = cs.rect.left + s.ax * k;
        var left = td.align === 'center' ? axScreen - wCss / 2 : (td.align === 'right' ? axScreen - wCss : axScreen);
        var top = cs.rect.top + s.ay * k - ((lay.lhp - td.size) / 2) * k;
        imp('width', wCss + 'px'); imp('height', hCss + 'px');
        imp('left', left + 'px'); imp('top', top + 'px');
    }

    function applyLive(s) {
        s.raf = 0;
        if (sess !== s) return;
        var td = currentTd(s);
        if (s.angle) td.angle = s.angle;   // [SPB-TFX1 2026-10-09 TA-034b] edit upright, remember the angle (re-applied on commit)
        var empty = !td.text.replace(/\s/g, '').length;
        var lay = layoutOf(td.text ? td : Object.assign({}, td, { text: ' ' }));
        layoutTextarea(s, td, lay);
        s.td = td;
        if (empty) {
            // nothing to show: new text -> take the preview layer back out; re-edit -> show the original
            if (s.isNew) {
                if (s.layer) { var arr0 = layersArr(), ix = arr0.indexOf(s.layer); if (ix >= 0) arr0.splice(ix, 1); s.layer = null; bumpAndRecomposite(); }
            } else if (s.before) {
                restoreState(s.layer, s.before); bumpAndRecomposite();
            }
            return;
        }
        var r = render(s.angle ? Object.assign({}, td, { angle: 0 }) : td);
        if (!r) return;
        if (s.angle) s.upright = true;
        var frozen = Object.freeze(clone(td));
        r.canvas.__spbText = frozen;
        var lay2 = r.lay;
        var bx = Math.round(s.ax - anchorLeft(td, lay2)), by = Math.round(s.ay - lay2.textY);
        if (!s.layer) {
            s.layer = {
                id: 'psd_text_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7),
                name: layerName(td), path: 'Text/' + td.text.split('\n')[0].substring(0, 20),
                visible: true, opacity: 255, img: r.canvas, bbox: [bx, by, bx + r.canvas.width, by + r.canvas.height],
                groupName: 'Text', blendMode: 'source-over', locked: false, alphaLock: false, clippingMask: false, effects: null
            };
            layersArr().push(s.layer);
            try { _psdLayersLoaded = true; } catch (_) {}
        } else {
            s.layer.img = r.canvas;
            s.layer.bbox = [bx, by, bx + r.canvas.width, by + r.canvas.height];
            if (s.autoName) { s.layer.name = layerName(td); s.layer.path = 'Text/' + td.text.split('\n')[0].substring(0, 20); }
        }
        bumpAndRecomposite();
        try { if (typeof drawLayerBounds === 'function') drawLayerBounds(); } catch (_) {}
    }
    function schedule(s) {
        if (s.raf) return;
        s.raf = (window.requestAnimationFrame || function (f) { return setTimeout(f, 16); })(function () { applyLive(s); });
    }

    function endSession(s) {
        if (sess === s) sess = null;
        try { document.removeEventListener('mousedown', s.onDocDown, true); } catch (_) {}
        try { document.removeEventListener('input', s.onOpt, true); document.removeEventListener('change', s.onChange, true); } catch (_) {}
        if (s.timer) clearInterval(s.timer);
        if (s.raf) { try { (window.cancelAnimationFrame || clearTimeout)(s.raf); } catch (_) {} s.raf = 0; }
        try { s.ta.remove(); } catch (_) {}
        setActiveFlag(false);
    }

    function commit() {
        var s = sess; if (!s) return false;
        if (s.raf) { try { (window.cancelAnimationFrame || clearTimeout)(s.raf); } catch (_) {} s.raf = 0; applyLive(s); }
        sess = null;   // applyLive checks sess === s, so call it before clearing (above), then finish
        endSession(s);
        var layer = s.layer;
        if (s.isNew) {
            if (!layer) return false;                            // nothing typed
            var arr = layersArr(), ix = arr.indexOf(layer);
            if (ix < 0) return false;
            arr.splice(ix, 1);                                   // snapshot the state BEFORE the text existed
            if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('add text layer');
            arr.splice(ix, 0, layer);
            try { _selectedLayerId = layer.id; window._selectedLayerId = layer.id; } catch (_) {}
            afterCommitRefresh(true);
            toast('Text "' + (payload(layer).text.split('\n')[0]) + '" added as a live text layer - double-click it with the Text tool to edit', 'success');
            return true;
        }
        // re-edit
        if (s.angle && s.upright && payload(layer)) applyAngle(layer, s.angle, [(s.before.bbox[0] + s.before.bbox[2]) / 2, (s.before.bbox[1] + s.before.bbox[3]) / 2]);   // [SPB-TFX1 2026-10-09 TA-034b]
        var cur = layerStateOf(layer);
        var tdBefore = payload({ img: s.before.img }), tdNow = payload(layer);
        var same = !tdNow || (tdBefore && JSON.stringify(tdBefore) === JSON.stringify(tdNow));
        if (same) {
            restoreState(layer, s.before); afterCommitRefresh(false); return true;
        }
        restoreState(layer, s.before);
        if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('edit text');
        restoreState(layer, cur);
        afterCommitRefresh(false);
        toast('Text updated', 'success');
        return true;
    }

    function cancel() {
        var s = sess; if (!s) return false;
        sess = null; endSession(s);
        if (s.isNew) {
            if (s.layer) { var arr = layersArr(), ix = arr.indexOf(s.layer); if (ix >= 0) arr.splice(ix, 1); bumpAndRecomposite(); try { drawLayerBounds(); } catch (_) {} }
        } else {
            restoreState(s.layer, s.before); bumpAndRecomposite(); try { drawLayerBounds(); } catch (_) {}
        }
        return true;
    }

    function open(layer, x, y) {
        if (sess) commit();
        ensureStyle();
        var isNew = !layer;
        var td0, ax, ay;
        if (isNew) {
            td0 = readControls(); td0.text = '';
            var lay0 = layoutOf(Object.assign({}, td0, { text: ' ' }));
            ax = x; ay = y - Math.round(td0.size * 0.5);
            void lay0;
        } else {
            td0 = clone(payload(layer));
            writeControls(td0);
            var lay = layoutOf(td0);
            if (td0.angle) {   // [SPB-TFX1 2026-10-09 TA-034b] rotated layer: the bbox is the rotated box, the upright box shares its centre
                ax = Math.round((layer.bbox[0] + layer.bbox[2]) / 2 - lay.tw / 2) + anchorLeft(td0, lay);
                ay = Math.round((layer.bbox[1] + layer.bbox[3]) / 2 - lay.th / 2) + lay.textY;
            } else {
                ax = layer.bbox[0] + anchorLeft(td0, lay);
                ay = layer.bbox[1] + lay.textY;
            }
        }
        var ta = document.createElement('textarea');
        ta.id = '_spbTextEdit'; ta.setAttribute('wrap', 'off'); ta.rows = 1; ta.spellcheck = false;
        ta.placeholder = 'Type text... (Enter = done, Shift+Enter = new line, Esc = cancel)';
        ta.value = isNew ? '' : td0.text;
        var s = {
            isNew: isNew, layer: isNew ? null : layer, ta: ta, ax: ax, ay: ay, td: td0, raf: 0, timer: 0,
            before: isNew ? null : layerStateOf(layer),
            autoName: isNew ? true : (layer.name === layerName(td0)),
            angle: isNew ? 0 : (Number(td0.angle) || 0)
        };
        document.body.appendChild(ta);
        sess = s;
        setActiveFlag(true);
        if (!isNew) { try { _selectedLayerId = layer.id; window._selectedLayerId = layer.id; if (typeof renderLayerPanel === 'function') renderLayerPanel(); } catch (_) {} }
        s.onDocDown = function (e) {
            var t = e.target;
            if (!t || t === ta || isTextControl(t)) return;
            var pc = $('paintCanvas');
            if (t === pc || (t.id === 'transformCanvas')) return;      // canvas clicks are handled by handleClick()
            commit();
        };
        document.addEventListener('mousedown', s.onDocDown, true);
        // tool-options-split.js moves some Text controls to #spbTextPrimary, so listen on the document
        s.onOpt = function (e) { if (isTextControl(e.target)) schedule(s); };
        s.onChange = function (e) { if (!isTextControl(e.target)) return; schedule(s); setTimeout(function () { if (sess === s) { try { ta.focus(); } catch (_) {} } }, 0); };
        document.addEventListener('input', s.onOpt, true); document.addEventListener('change', s.onChange, true);
        ta.addEventListener('input', function () { schedule(s); });
        ta.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commit(); }
            else if (e.key === 'Escape') { e.preventDefault(); cancel(); }
            e.stopPropagation();
        });
        s.timer = setInterval(function () {
            if (sess !== s) return;
            var m = (typeof canvasMode !== 'undefined') ? canvasMode : 'text';
            if (m !== 'text') commit();
        }, 300);
        var lay1 = layoutOf(Object.assign({}, td0, { text: td0.text || ' ' }));
        layoutTextarea(s, td0, lay1);
        ta.focus();
        if (!isNew) { try { ta.setSelectionRange(0, ta.value.length); } catch (_) {} }
        if (s.angle) schedule(s);   // [SPB-TFX1 2026-10-09 TA-034b] show the rotated text upright while it is being edited
        return true;
    }

    // ------------------------------------------------------------------ entry points used by the canvas
    function handleClick(x, y) {
        if (window.SPB_TFX2_OFF) return false;
        if (sess) { commit(); return true; }                         // first click outside commits (Photoshop)
        var legacy = $('_textToolInput');
        if (legacy) { try { legacy.blur(); } catch (_) {} return true; }
        var hit = hitTextLayer(x, y);
        if (hit) {
            if (hit.locked) { toast('"' + (hit.name || 'Text') + '" is locked - unlock it to edit the text', 'warn'); return true; }
            return open(hit, x, y);
        }
        return open(null, x, y);
    }

    function rasterize(layer) {
        layer = layer || (function () { var L = layersArr(); return L.find(function (l) { return l.id === _selectedLayerId; }); })();
        if (!layer || !isTextLayer(layer)) { toast('Select a live text layer first', 'info'); return false; }
        if (sess) commit();
        window.__tfx3RastAt = Date.now();   // [SPB-TFX3 AUDIT2-F8] this path has its own toast
        if (typeof _pushLayerStackUndo === 'function') _pushLayerStackUndo('rasterize text');
        var cv = document.createElement('canvas'); cv.width = layer.img.width; cv.height = layer.img.height;
        cv.getContext('2d').drawImage(layer.img, 0, 0);
        layer.img = cv;                                              // fresh canvas = no payload = plain pixels
        afterCommitRefresh(false);
        toast('Type rasterized - the text is now plain pixels (Ctrl+Z brings the live text back)', 'info');
        return true;
    }

    // restore the payload when a project is opened (called by spb-projects.js)
    function attach(layer, td) {
        if (!layer || !layer.img || !td || typeof td !== 'object') return false;
        try { layer.img.__spbText = Object.freeze(clone(td)); return true; } catch (_) { return false; }
    }

    window.SPBTextEdit = {
        handleClick: handleClick, commit: commit, cancel: cancel, rasterize: rasterize, attach: attach,
        isTextLayer: isTextLayer, payload: payload, hit: hitTextLayer, render: render,
        isEditing: function () { return !!sess; }
    };
})();
