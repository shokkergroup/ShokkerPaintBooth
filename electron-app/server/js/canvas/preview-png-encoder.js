(function (root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    if (root) root.SPBPreviewPngEncoder = api;
})(typeof window !== 'undefined' ? window : globalThis, function () {
    'use strict';
    // SPB-93 2026-09-07: encode away from the main thread; only the still
    // current paint/request may publish its PNG into the shared source memo.
    async function encode(canvas, options) {
        if (!canvas || !canvas.width || !canvas.height) return null;
        const revision = options.revision(), memo = options.memo, now = options.now();
        const current = () => options.current() && options.revision() === revision;
        if (!current()) return null;
        if (memo.url && memo.rev === revision && memo.sigAt && now - memo.sigAt < 30000) {
            return { url: memo.url, sig: memo.sig };
        }
        let sig;
        if (memo.rev !== revision) sig = 'rev:' + revision + ':' + options.stamp();
        else {
            sig = options.signature(canvas);
            if (sig && memo.sig === sig && memo.url) {
                memo.sigAt = now;
                return { url: memo.url, sig };
            }
        }
        const url = await options.encode(canvas);
        if (!current()) return null;
        if (sig) Object.assign(memo, { sig, url, rev: revision, sigAt: now });
        else Object.assign(memo, { sig: null, url: null, rev: null, sigAt: 0 });
        return { url, sig };
    }
    return { encode };
});
