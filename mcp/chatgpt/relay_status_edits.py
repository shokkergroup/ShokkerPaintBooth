"""Distinguish delivered work from an unconnected or waiting listener."""

def edits(relative):
    if relative != 'js/spb-ai-connect.js':
        return []
    return [
        ("lastSent: 0, status: null", "lastSent: 0, lastReply: 0, status: null", 1),
        ("S.waiting = false; S.lastSent = 0; }", "S.waiting = false; S.lastSent = 0; S.lastReply = 0; }", 1),
        ("else if (e.role === 'assistant') { S.waiting = false; S.lastSent = 0; push", "else if (e.role === 'assistant') { S.waiting = false; S.lastSent = 0; S.lastReply = Date.now(); push", 1),
        ("    function statusLine(m) {", "    function recentReply() { return !!(S.lastReply && Date.now() - S.lastReply < 120000); }\n    function statusLine(m) {", 1),
        ("        var on = S.status && S.status.enabled;", '''        var on = S.status && S.status.enabled;
        if (on && S.waiting === 'working') return '<div class="spb-aic-st">' + esc(name(m)) + ' received your message. Waiting for its answer.</div>';
        if (on && !S.waiting && recentReply()) return '<div class="spb-aic-st">Last answer received from ' + esc(name(m)) + '. You can send your next question here.</div>';''', 1),
        ("(hasLog && S.listening ? '' : ' open')", "(hasLog && (S.listening || S.waiting === 'working' || recentReply()) ? '' : ' open')", 1),
        ("        var st = S.status || {}, quiet = st.lastCallAgo == null || st.lastCallAgo > 60;", '''        var st = S.status || {}, quiet = st.lastCallAgo == null || st.lastCallAgo > 60;
        if (S.waiting === 'working' && S.lastSent && Date.now() - S.lastSent > 90000 && !S.listening && quiet)
            return '<div class="spb-pai-msg ai busy">' + esc(name()) + ' received your message, but its answer has not returned yet. Your message is kept. Check the connected assistant chat if you need to see its progress.</div>';''', 1),
    ]
