(function (W) {
    'use strict';
    // In-memory execution references expire at committed document boundaries.
    // This is separate from historical .spbproj discussion and owns no pixels.
    var bound = identity(), epoch = 0, failures = [];
    function identity() {
        var T = W.SPBSourceLoadTransaction;
        try { return T ? { path: String(T.getCommittedPath() || ''), fingerprint: String(T.getCommittedFingerprint() || ''), generation: T.getGeneration() } : null; }
        catch (e) { return null; }
    }
    function sameFile(a, b) { return !!a && !!b && a.path === b.path && a.fingerprint === b.fingerprint; }
    function reset(name, object, method) {
        if (!object) return;
        if (typeof object[method] !== 'function') { failures.push(name); return; }
        try { object[method](); } catch (e) { failures.push(name); }
    }
    function invalidate(now) {
        bound = now; epoch++; failures = [];
        reset('Full Editor conversation', W.spbProAI, '_sourceChanged');
        reset('Connected assistant replies', W.SpbAiConnect, '_sourceChanged');
        reset('Offline choices', W.SpbOfflineBuilder, '_sourceChanged');
        reset('Paint by numbers choices', W.SpbPbn, '_sourceChanged');
        reset('Offline follow-ups', W.SpbOfflineAnswer, '_resetConvo');
        reset('Live conversation', W.SpbConvo, 'reset');
        reset('Rendered change verifier', W.SpbIntentReport, '_reset');
        reset('Template source reference', W.SpbTemplateIdentity, '_sourceChanged');
        // Also reset the planner when OfflineAnswer has not loaded yet.
        var P = W.SpbIntentPlan;
        reset('Intent plan', P, P && P.forgetAll ? 'forgetAll' : 'forget');
    }
    function observe() {
        var now = identity();
        if (!bound) { bound = now; return; }
        if (!sameFile(bound, now)) invalidate(now);
    }
    function sourceCommitted() {
        var now = identity();
        if (!sameFile(bound, now) || !bound || bound.generation !== now.generation) invalidate(now);
    }
    function stamp() { observe(); return epoch; }
    function current(value) { observe(); return !!bound && failures.length === 0 && value === epoch; }
    function status() { observe(); return { epoch: epoch, available: !!bound && failures.length === 0, failed_resets: failures.slice(), scope: 'Current committed document only; saved discussion is historical.' }; }
    W.SpbConversationScope = { observe: observe, sourceCommitted: sourceCommitted, stamp: stamp, current: current, status: status };
})(window);
