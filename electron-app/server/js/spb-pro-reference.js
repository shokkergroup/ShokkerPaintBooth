/* SPB PRO REFERENCE (2026-10-02): "make my car look like THIS picture".
   Holds the buyer's reference picture, measures its design on the server (engine/ref_analyze.py via /api/trace/analyze) and builds the side-by-side picture the vision model uses to compare the reference with the current result.
   The design is taken from a SIDE view (nose-left or nose-right, roof on top): a side panel of the paint sheet is an orthographic side view in the same orientation, so both are directly comparable.
   API: SpbReference.set(dataUrl) -> Promise<info>;  .get();  .clear();  .analyze({box,nose,snap}) -> Promise<analysis>;  .compareImage() -> Promise<dataUrl|null>;  .sideAspect() -> Promise<number>
   ES5 only. Pure helpers + two fetches; keeps one picture in memory. */
(function () {
    'use strict';
    var W = window, _ref = null;
    function base() { return W.SPB_AI_BASE || ''; }
    function load(src) { return new Promise(function (res, rej) { var im = new Image(); im.onload = function () { res(im); }; im.onerror = function () { rej(new Error('picture could not be read')); }; im.src = src; }); }
    // shrink to a sane size (the model + server do not need 6000 px): longest side <= 1400, JPEG
    function normalise(src) {
        return load(src).then(function (im) {
            var s = Math.min(1, 1400 / Math.max(im.naturalWidth, im.naturalHeight)), w = Math.max(1, Math.round(im.naturalWidth * s)), h = Math.max(1, Math.round(im.naturalHeight * s)), c = document.createElement('canvas'); c.width = w; c.height = h;
            var x = c.getContext('2d'); x.fillStyle = '#ffffff'; x.fillRect(0, 0, w, h); x.drawImage(im, 0, 0, w, h);
            return { url: c.toDataURL('image/jpeg', 0.86), w: w, h: h, im: im };
        });
    }
    function set(src) { return normalise(src).then(function (n) { _ref = { url: n.url, w: n.w, h: n.h, box: null, nose: 'left' }; return { w: n.w, h: n.h }; }); }
    function get() { return _ref; }
    function clear() { _ref = null; }
    function partPx(part) { var G = W.SpbGraphics, F = G && G.frame ? G.frame(part || 'left side') : null; return F ? [Math.round(F.L), Math.round(F.H)] : [1800, 512]; }

    // measure the design (server side). box = [x0,y0,x1,y1] as FRACTIONS of the picture; nose = which way the car's nose points in that view
    function analyze(o) {
        o = o || {}; if (!_ref) return Promise.reject(new Error('no reference picture is attached'));
        var box = o.box || _ref.box; if (box) _ref.box = box; if (o.nose) _ref.nose = o.nose;
        var body = { image: _ref.url, views: box ? [{ kind: 'side', nose: _ref.nose || 'left', box: box }] : [], part_px: partPx('left side'), snap: !!o.snap, nose: _ref.nose || 'left' };
        return fetch(base() + '/api/trace/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).then(function (r) { return r.json(); });
    }

    // the reference side view oriented like a side panel (nose left, roof on top), at W x H
    function refSide(Wd, Hd) {
        if (!_ref) return Promise.resolve(null);
        return load(_ref.url).then(function (im) {
            var b = _ref.box || [0, 0, 1, 1], sx = b[0] * im.naturalWidth, sy = b[1] * im.naturalHeight, sw = (b[2] - b[0]) * im.naturalWidth, sh = (b[3] - b[1]) * im.naturalHeight, c = document.createElement('canvas'); c.width = Wd; c.height = Hd; var x = c.getContext('2d');
            x.fillStyle = '#ffffff'; x.fillRect(0, 0, Wd, Hd); if (_ref.nose === 'right') { x.translate(Wd, 0); x.scale(-1, 1); } x.drawImage(im, sx, sy, sw, sh, 0, 0, Wd, Hd); return c;
        });
    }
    // OUR current result for the left side panel, in the same orientation, from the live preview
    function ourSide(Wd, Hd) {
        var G = W.SpbGraphics, F = G && G.frame ? G.frame('left side') : null, im = document.getElementById('livePreviewImg'); if (!F || !im || !(im.naturalWidth > 32) || !im.complete) return Promise.resolve(null);
        var pc = document.getElementById('paintCanvas'), k = im.naturalWidth / (pc ? pc.width : 2048), b = F.box, m = F.m, c = document.createElement('canvas'); c.width = Wd; c.height = Hd; var x = c.getContext('2d'); x.fillStyle = '#ffffff'; x.fillRect(0, 0, Wd, Hd);
        x.save(); if (m[0] === -1) { x.translate(Wd, 0); x.scale(-1, 1); } if (m[3] === -1) { x.translate(0, Hd); x.scale(1, -1); }      // undo the part's orientation (front-right / roof-bottom panels are flipped on the sheet)
        x.drawImage(im, b[0] * k, b[1] * k, (b[2] - b[0]) * k, (b[3] - b[1]) * k, 0, 0, Wd, Hd); x.restore(); return Promise.resolve(c);
    }
    function compareImage() {
        var pp = partPx('left side'), Wd = 900, Hd = Math.max(120, Math.round(900 * pp[1] / pp[0]));
        return Promise.all([refSide(Wd, Hd), ourSide(Wd, Hd)]).then(function (r) {
            if (!r[0] || !r[1]) return null; var gap = 14, lab = 22, c = document.createElement('canvas'); c.width = Wd; c.height = Hd * 2 + gap + lab * 2; var x = c.getContext('2d');
            x.fillStyle = '#20232f'; x.fillRect(0, 0, c.width, c.height); x.fillStyle = '#ffffff'; x.font = 'bold 15px sans-serif'; x.fillText('TOP: the REFERENCE side view (the design to copy)', 8, 16); x.drawImage(r[0], 0, lab); x.fillText('BOTTOM: the CURRENT RESULT (left side of the paint sheet, nose left, roof on top)', 8, lab + Hd + gap + 16); x.drawImage(r[1], 0, lab * 2 + Hd + gap);
            return c.toDataURL('image/jpeg', 0.88);
        });
    }
    function sideAspect() { return _ref ? Promise.resolve(_ref.w / _ref.h) : Promise.resolve(0); }

    W.SpbReference = { set: set, get: get, clear: clear, analyze: analyze, compareImage: compareImage, refSide: refSide, ourSide: ourSide, partPx: partPx, sideAspect: sideAspect, normalise: normalise };
})();
