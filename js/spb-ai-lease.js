/* SPB-AI 2026-10-01: one assistant owns editing until explicit takeover or idle expiry. */
(function () {
    'use strict';
    var owner = '', until = 0, active = false;
    function current() { if (!active && Date.now() >= until) owner = ''; return owner; }
    function begin(who) {
        var held = current();
        if (active || (held && held !== who)) return false;
        owner = who; active = true; until = Date.now() + 120000; return true;
    }
    function end() { active = false; until = Date.now() + 120000; }
    function takeover() { if (active) return false; owner = 'internal'; until = Date.now() + 120000; return true; }
    function internal() { if (current() === 'external') return false; owner = 'internal'; until = Date.now() + 120000; return true; }
    function holdInternal() { if (current() === 'internal') { active = true; until = Date.now() + 120000; return true; } return false; }
    function release() { if (!active) { owner = ''; until = 0; } }
    window.SpbAiLease = { begin: begin, end: end, internal: internal, holdInternal: holdInternal, takeover: takeover, release: release, owner: current };
})();
