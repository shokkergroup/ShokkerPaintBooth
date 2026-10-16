"""Keep the composer honest until finishCore verification actually settles."""

def edits(relative):
    if relative != 'js/spb-pro-ai.js':
        return []
    return [
        ('    function finish(r, text, kind, entryOpts) {', '''    // ChatGPT Oct10: a completed-looking bubble can precede final verification.
    // Keep drafts editable, but never dispatch another turn until it settles.
    var _composerFinishing = 0;
    function composerPending() { return !!(_busy || _composerFinishing); }
    function composerSync() {
        if (!_panel) return;
        var pending = composerPending(), checking = !_busy && _composerFinishing > 0;
        var button = _panel.querySelector('[data-act="send"]');
        if (button) {
            button.disabled = pending;
            button.textContent = pending ? (checking ? 'Checking…' : 'Working…') : 'Send';
            button.setAttribute('aria-disabled', String(pending));
            button.title = pending ? 'Your message stays here. Send it when this change finishes.' : 'Send your message';
        }
        var input = _panel.querySelector('.spb-pai-input');
        if (input) input.disabled = false;
        var status = _panel.querySelector('.spb-pai-compose-status');
        if (status) {
            status.hidden = !pending;
            status.textContent = pending ? (checking ? 'Checking the change. You can write your next message.' : 'Working. You can write your next message.') : '';
        }
    }
    function composerSettled() { _composerFinishing = Math.max(0, _composerFinishing - 1); composerSync(); }
    function finish(r, text, kind, entryOpts) {''', 1),
        ('        var lease = window.SpbAiLease, held = lease && lease.holdInternal();', '        _composerFinishing++; composerSync();\n        var lease = window.SpbAiLease, held = lease && lease.holdInternal();', 1),
        ('if (held) lease.end(); return out; }, function (e) { if (held) lease.end(); throw e;', 'if (held) lease.end(); composerSettled(); return out; }, function (e) { if (held) lease.end(); composerSettled(); throw e;', 1),
        ('    function send(text, o) {', '    function send(text, o) {\n        if (composerPending()) { composerSync(); return; }', 1),
        ('        var inp = _panel.querySelector(\'.spb-pai-input\'); if (inp) inp.disabled = !!_busy;', '        composerSync();', 1),
        ('<button type="button" class="spb-pai-send" data-act="send">Send</button></div>', '<button type="button" class="spb-pai-send" data-act="send">Send</button></div><div class="spb-pai-compose-status spb-pai-meta" role="status" aria-live="polite" hidden></div>', 1),
    ]
