/* ============================================================================
   SPB INTENT — a tiny OFFLINE intent model for the finish advisor   (owner 2026-10-03: "as smart as possible offline")
   A multinomial logistic regression over word 1-2 grams, trained by scripts/ai_atlas/train_intent.py on 1,500 labelled messages (independent Codex L3 corpus) + 400 truth asks.
   Held-out (even / odd split) it separates "a finish question" from "design / support / chit-chat" with 97% precision and 99% recall, and names the 13-way intent 84% of the time.
     SpbIntent.predict(text) -> { label, p, probs: {label: p} }      labels: recommend find compare about kit review taste judge inspect catalogue design support none
   ES5 only; no network; the weights live in js/spb-intent-data.js (window.SPB_INTENT_DATA).
   ========================================================================== */
(function () {
    'use strict';
    var D = null, IDX = null;
    function init() {
        if (D) return true; D = window.SPB_INTENT_DATA; if (!D) return false;
        IDX = {}; for (var i = 0; i < D.features.length; i++) IDX[D.features[i]] = i;
        return true;
    }
    function tokens(t) { t = String(t || '').toLowerCase().replace(/[’`]/g, "'").replace(/\d+/g, '0'); return t.match(/[a-z']+|0/g) || []; }
    function predict(text) {
        if (!init()) return null;
        var tk = tokens(text), seen = {}, idx = [], i, f;
        for (i = 0; i < tk.length; i++) { f = tk[i]; if (IDX[f] != null && !seen[f]) { seen[f] = 1; idx.push(IDX[f]); } if (i + 1 < tk.length) { f = tk[i] + ' ' + tk[i + 1]; if (IDX[f] != null && !seen[f]) { seen[f] = 1; idx.push(IDX[f]); } } }
        var C = D.classes.length, sc = [], mx = -1e9, c, j;
        for (c = 0; c < C; c++) { var s = D.intercept[c] / 100, w = D.weights[c]; for (j = 0; j < idx.length; j++) s += w[idx[j]] / 100; sc.push(s); if (s > mx) mx = s; }
        var z = 0, pr = []; for (c = 0; c < C; c++) { var e = Math.exp(sc[c] - mx); pr.push(e); z += e; }
        var best = 0, probs = {}; for (c = 0; c < C; c++) { pr[c] /= z; probs[D.classes[c]] = pr[c]; if (pr[c] > pr[best]) best = c; }
        return { label: D.classes[best], p: pr[best], probs: probs };
    }
    window.SpbIntent = { predict: predict, ready: init, tokens: tokens };
})();
