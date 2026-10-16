"""Bind builder status to the exact Run entry, including native layer effects."""
def edits(relative, original=''):
    if relative == 'js/spb-offline-builder.js':
        result = [
            ('var p8 = null; try { p8 = B.run', 'var p8 = null, ran8 = {at:Date.now()}; try { p8 = B.run', 1),
            ('s5only: true }); } catch (e8)', 's5only: true, runReceipt:ran8 }); } catch (e8)', 1),
            ('S.ran = { at: Date.now() }; S.edit = null; draw(); if (p8', 'S.ran = ran8; S.edit = null; draw(); if (p8', 1),
            ('var said = readAs(S.steps), p = null;', 'var said = readAs(S.steps), p = null, ran = {at:Date.now()};', 1),
            ("logText: '▶ Run: ' + said, s5frame:", "logText: '▶ Run: ' + said, runReceipt:ran, s5frame:", 2),
            ('S.ran = { at: Date.now() }; S.edit = null; draw();\n        if (p && p.then)', 'S.ran = ran; S.edit = null; draw();\n        if (p && p.then)', 1),
            ('    function undoChanged(entry) {', '''    function runCompleted(entry, receipt) {
        if (!entry || !receipt || S.ran !== receipt || entry.id == null) return false;
        receipt.eid = entry.id; receipt.undone = !!entry.undone; receipt.canUndo = !!entry.undoable;
        receipt.noChange = !!entry.noChange || !!(entry.colourOutcomes && entry.colourOutcomes.length && !(entry.lines || []).length && entry.colourOutcomes.every(function (o) { return o.status === 'unchanged'; }));
        draw(); return true;
    }
    function undoChanged(entry) {''', 1),
            ('if (!S.ran || !entry || !rep || rep.eid !== entry.id) return false;', 'if (!S.ran || !entry || (S.ran.eid != null ? S.ran.eid !== entry.id : (!rep || rep.eid !== entry.id))) return false;', 1),
            ('W.SpbOfflineBuilder = { _sourceChanged:', 'W.SpbOfflineBuilder = { _runCompleted:runCompleted, _sourceChanged:', 1),
            ("v && v.verdict && v.verdict !== 'skip';", "v && v.verdict && v.verdict !== 'skip' && (S.ran.eid == null || v.eid === S.ran.eid);", 1),
            ("(nodo ? '⚠ Not done yet:' : '✓ Done:')", "(S.ran.noChange ? 'No change made:' : (nodo ? '⚠ Not done yet:' : '✓ Done:'))", 1),
            ("(s3back ? ' disabled' : '')", "(s3back || S.ran.noChange || S.ran.canUndo === false ? ' disabled' : '')", 1),
            ("else if (a === 'undo') { var lastReport = s3Ran();", "else if (a === 'undo') { if (!S.ran || S.ran.noChange || S.ran.canUndo === false || S.ran.undone || S.ran.eid == null) return; var lastReport = s3Ran();", 1),
            ("B && B.undo ? B.undo() : (W.spbProAI && W.spbProAI._undoLast ? W.spbProAI._undoLast() : false)", "B && B.undo ? B.undo(S.ran.eid) : false", 1),
        ]
        if '    function runCompleted(entry, receipt) {' in original:
            from owner_promotions import function_text
            adapted = []
            for before, after, count in result:
                if before == '    function undoChanged(entry) {':
                    before, after = function_text(original, 'runCompleted'), function_text(after, 'runCompleted')
                elif before == "(s3back ? ' disabled' : '')":
                    before = "(s3back || S.ran.noChange ? ' disabled' : '')"
                elif before == "else if (a === 'undo') { var lastReport = s3Ran();":
                    before = "else if (a === 'undo') { if (!S.ran || S.ran.noChange || S.ran.undone || S.ran.eid == null) return; var lastReport = s3Ran();"
                adapted.append((before, after, count))
            result = adapted
        return result
    if relative == 'js/spb-pro-ai.js':
        return [
            ('undo: function () { return undoLast(); },', 'undo: function (eid) { return undoBuilderEntry(eid); },', 1),
            ('    function undoLast() {', '''    function undoBuilderEntry(eid) {
        if (eid == null) return false;
        var ent = _log.filter(function (m) { return m.role === 'ai' && m.id === eid && m.undoable && !m.undone; })[0];
        if (!ent) return false; doUndo(ent); return !!ent.undone;
    }
    function undoLast() {''', 1),
            ("return finish(r5, text, 'ask');", "return finish(r5, text, 'ask', {builderRunReceipt:ob.runReceipt});", 1),
            ("return finish(r8, text, 'ask');", "return finish(r8, text, 'ask', {builderRunReceipt:ob.runReceipt});", 1),
            ("return finish(r, text, 'ask'); }, function (e4)", "return finish(r, text, 'ask', {builderRunReceipt:ob.runReceipt}); }, function (e4)", 1),
            ('_log.push(entry); _last = entry; try { if (window.SpbConvo', '''_log.push(entry); _last = entry;
        try { if (entryOpts.builderRunReceipt && window.SpbOfflineBuilder && SpbOfflineBuilder._runCompleted) SpbOfflineBuilder._runCompleted(entry,entryOpts.builderRunReceipt); } catch (eOBReceipt) {}
        try { if (window.SpbConvo''', 1),
        ]
    return []
