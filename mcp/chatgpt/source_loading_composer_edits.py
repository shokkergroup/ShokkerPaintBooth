"""Keep a typed question local while a layered source import is in flight.

No automatic replay: the customer sends once the current paint is ready.
Shared source remains untouched; compose after existing composer candidates.
"""


def edits(relative):
    if relative != 'js/spb-pro-ai.js':
        return []
    return [
        ('    function composerPending() { return !!(_busy || _composerFinishing); }', """    var _composerSourceTimer = null;
    function composerSourceLoading() {
        if (window._spbPsdImportInFlight === true) return true;
        // Claude's existing project transaction spans source, rasters and settings.
        // Reuse its public status instead of treating PSD decode as full readiness.
        try { var p = window.SPB_PERSIST; return !!(p && p.status && Number(p.status().busy) > 0); }
        catch (e) { return false; }
    }
    function composerPending() { return !!(_busy || _composerFinishing || composerSourceLoading()); }""", 1),
        ('        var pending = composerPending(), checking = !_busy && _composerFinishing > 0;', """        var sourceLoading = composerSourceLoading();
        // Observe only an active import. No model calls, render or queued Send.
        if (sourceLoading && _composerSourceTimer === null) {
            _composerSourceTimer = setTimeout(function () { _composerSourceTimer = null; composerSync(); }, 250);
        } else if (!sourceLoading && _composerSourceTimer !== null) {
            clearTimeout(_composerSourceTimer); _composerSourceTimer = null;
        }
        var pending = composerPending(), checking = !_busy && _composerFinishing > 0;""", 1),
        ("button.textContent = pending ? (checking ? 'Checking…' : 'Working…') : 'Send';", "button.textContent = pending ? (sourceLoading ? 'Loading paint…' : (checking ? 'Checking…' : 'Working…')) : 'Send';", 1),
        ("button.title = pending ? 'Your message stays here. Send it when this change finishes.' : 'Send your message';", "button.title = pending ? (sourceLoading ? 'Your draft stays here. Send it when the paint finishes loading.' : 'Your message stays here. Send it when this change finishes.') : 'Send your message';", 1),
        ("status.textContent = pending ? (checking ? 'Checking the change. You can write your next message.' : 'Working. You can write your next message.') : '';", "status.textContent = pending ? (sourceLoading ? 'The paint is loading. You can write your question; send it when loading finishes.' : (checking ? 'Checking the change. You can write your next message.' : 'Working. You can write your next message.')) : '';", 1),
    ]
