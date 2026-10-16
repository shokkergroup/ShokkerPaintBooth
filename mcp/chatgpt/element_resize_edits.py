"""Exact W20 scope/lock preflight, preserving Claude's resize raster algorithm."""
def edits(relative):
    if relative == 'js/spb-offline-answer.js':
        return [(
            "        if (!steps.length) return null;\n        for (i = 0; i < steps.length; i++) { var el0 = steps[i].extra.w20x.element, nt = w20xElemLayersNote(el0, env);",
            """        if (!steps.length) return null;
        if (W.SpbElementResizeScope) {
            var resizeScope = W.SpbElementResizeScope.bind(t, steps, (env4g(W.SpbIntentPlan, env) || {}).layers || []);
            if (!resizeScope.ok) return asked('resize-layer-scope', resizeScope.error, []);
            steps = resizeScope.steps;
        } else if (/\\blayers?\\b/i.test(t)) return asked('resize-layer-scope', 'Exact layer resizing is unavailable in this build. Nothing was resized.', []);
        for (i = 0; i < steps.length; i++) { var el0 = steps[i].extra.w20x.element, nt = w20xElemLayersNote(el0, env);""", 1)]
    if relative == 'js/spb-offline-builder.js':
        return [
            ('function w20xLayersFor(el, kinds) {', 'function w20xLayersFor(el, kinds, ids) {', 1),
            ("        var all = rl.filter(function (r) { return rx.test(String(r.role || '')) && r.visible !== false; }).map(function (r) { return PL.filter(function (l) { return l && l.name === r.name && l.img; })[0]; }).filter(Boolean);",
             """        if (ids) {
            if (!W.SpbElementResizeScope) throw Error('Exact resize scope is unavailable. Nothing was resized.');
            return W.SpbElementResizeScope.exactTargets(ids, PL, rl, el);
        }
        var all = rl.filter(function (r) { return rx.test(String(r.role || '')) && r.visible !== false; }).map(function (r) {
            if (W.SpbElementResizeScope) return W.SpbElementResizeScope.roleLayer(r, PL);
            var named = PL.filter(function (l) { return l && l.name === r.name && l.img; });
            if (named.length > 1) throw Error('Several artwork layers have the same name. Choose an exact group and layer.');
            return named[0];
        }).filter(Boolean);""", 1),
            ("        var said = readAs(wx), notes = [], did = [], undo = 0;\n        tlStart('▶ Run: ' + said, 'run');",
             """        var said = readAs(wx), notes = [], did = [], undo = 0, resizeTargets = [];
        // Validate every intended layer before the first write or Undo entry.
        try { resizeTargets = wx.map(function (st) {
            var x = st.extra.w20x, ls = w20xLayersFor(x.element, x.kinds, x.layer_ids);
            if (W.SpbElementResizeScope) return W.SpbElementResizeScope.validate(x, ls);
            if (ls.some(function (l) { return l.locked || l.visible === false; })) throw Error('A resize layer is locked or hidden. Nothing was resized.');
            return ls;
        }); } catch (resizeError) { S.msg = String(resizeError.message || resizeError); draw(); return 'done'; }
        tlStart('▶ Run: ' + said, 'run');""", 1),
            ("        wx.forEach(function (st) {\n            var x = st.extra.w20x, nm = x.element === 'numbers' ? 'numbers' : 'sponsors and logos', ls = w20xLayersFor(x.element, x.kinds);",
             "        wx.forEach(function (st, resizeIndex) {\n            var x = st.extra.w20x, nm = x.element === 'numbers' ? 'numbers' : 'sponsors and logos', ls = resizeTargets[resizeIndex];", 1),
            ("try { if (W.spbProAI && W.spbProAI._push) W.spbProAI._push({ role: 'ai', undoable: undo > 0, layerUndo: undo, zoneUndo: false, request: said, text: txt, offline: true, model: 'built-in', usage: { cost: 0 }, calls: 0, lines: did.slice(), notes: notes.slice() }); } catch (eP) {}",
             "var resizeEntry = { role: 'ai', undoable: undo > 0, layerUndo: undo, zoneUndo: false, request: said, text: txt, offline: true, model: 'built-in', usage: { cost: 0 }, calls: 0, lines: did.slice(), notes: notes.slice() };\n        try { if (W.spbProAI && W.spbProAI._push) W.spbProAI._push(resizeEntry); } catch (eP) {}", 1),
            ("        S.ran = { at: Date.now() }; S.edit = null; draw(); return 'done';",
             "        S.ran = { at: Date.now(), eid: resizeEntry.id, noChange: undo === 0, resize: true }; S.edit = null; draw(); return 'done';", 1),
            ("return !st.colour && !(st.tex && st.tex.mode === 'pattern') && (st.act === 'shine'",
             "return !(st.extra && st.extra.w20x) && !st.colour && !(st.tex && st.tex.mode === 'pattern') && (st.act === 'shine'", 1),
        ]
    if relative == 'js/spb-pbn.js':
        return [(
            '                var readState3 = B && B.state ? B.state() : null, readAns3 = readState3 && readState3.answer && readState3.answer.answer;',
            '''                var readState3 = B && B.state ? B.state() : null, readAns3 = readState3 && readState3.answer && readState3.answer.answer;
                // W20 has a reviewed executable builder plan; do not contradict
                // it with the older generic "cannot resize" funnel card.
                if (readState3 && String(readState3.text || '').trim() === String(S.text || '').trim() && !(readState3.liveText || '').trim() && !readState3.msg && (readState3.steps || []).some(function (st) { return st.extra && st.extra.w20x; })) { CUR = null; off = true; }''', 1)]
    return []
