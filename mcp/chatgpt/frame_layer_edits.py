"""Private proposal: preserve exact layer identity throughout the intent pipeline."""
def edits(relative):
    if relative == 'js/spb-intent-model.js':
        return [
            ('    function layerMatch(name, env) {', '''    function layerMatch(name, env) {
        if (W.SpbLayerTargets && env && env.layers && env.layers.length) {
            var rows = env.layers.map(function(l){return typeof l === 'string' ? {name:l} : l;});
            var resolved = W.SpbLayerTargets.resolve(name, rows);
            return resolved.ok ? {name:resolved.selector} : {bad:String(name)};
        }''', 1),
            ('    function tgtNorm(T, env, rep, where) {', '''    function layerName(ref, env) {
        var hit = W.SpbLayerTargets && W.SpbLayerTargets.resolve(ref, (env && env.layers) || []);
        return hit && hit.ok ? String(hit.row.name) : String(ref);
    }
    function tgtNorm(T, env, rep, where) {''', 1),
            ('return dec.indexOf(l) !== -1;', 'return dec.indexOf(layerName(l, env)) !== -1;', 1),
            ("var said = env.text.toLowerCase(), named = arr(T.layers).some(function (l) { return said.indexOf(l.toLowerCase()", "var said = env.text.toLowerCase(), named = arr(T.layers).some(function (l) { l = layerName(l, env); return said.indexOf(l.toLowerCase()", 1),
            ('var ls = arr(T.layers).map(function (l) { return String(l).toLowerCase(); });', 'var ls = arr(T.layers).map(function (l) { return layerName(l, env).toLowerCase(); });', 1),
        ]
    if relative == 'js/spb-intent-frame.js':
        return [('if (layers.indexOf(L) === -1) err.push', "if (W.SpbLayerTargets ? !W.SpbLayerTargets.resolve(L, (env && env.layers) || []).ok : layers.indexOf(L) === -1) err.push", 1)]
    if relative == 'js/spb-intent-plan.js':
        return [
            ("var l = E.layers.filter(function (x) { return x && x.name === name; })[0];", "var hit = W.SpbLayerTargets && W.SpbLayerTargets.resolve(name, E.layers); var l = hit ? (hit.ok ? hit.row : null) : E.layers.filter(function (x) { return x && x.name === name; })[0];", 1),
            ('return { name: r.name, role: r.role, visible: r.visible };', 'return { id: r.id, name: r.name, group: r.group, role: r.role, visible: r.visible };', 1),
        ]
    if relative == 'js/spb-mcp-frames.js':
        return [
            ('return { name: r.name, role: r.role, visible: r.visible };', 'return { id: r.id, name: r.name, group: r.group, role: r.role, visible: r.visible, locked: r.locked };', 1),
            ('        var useRun = !!host.planRun && !repaired && !!IP().asQueue, queue = useRun ? IP().asQueue(pl) : chosen;\n        if (!useRun) queue = chosen.slice ? chosen.slice() : chosen;', '''        var nativeColour = null;
        if (!W.SPB_CX3_OFF && !special && !hooks && !repaired && W.SpbNativeLayerColour && W.SpbNativeLayerColour.frameQueue) {
            nativeColour = W.SpbNativeLayerColour.frameQueue(P.frame, String(args.text || ''), {layers:liveLayers(host)});
            if (nativeColour && nativeColour.error) return Promise.resolve(fail(nativeColour.error, {changed:false, frame:slimFrame(P.frame)}));
        }
        var useNative = !!(nativeColour && nativeColour.queue), useRun = !useNative && !!host.planRun && !repaired && !!IP().asQueue;
        var queue = useNative ? nativeColour.queue : (useRun ? IP().asQueue(pl) : (chosen.slice ? chosen.slice() : chosen));''', 1),
            ("applied_as: useRun ? 'planner run (hooks kept)'", "applied_as: useNative ? 'native layer colour (source artwork composited)' : useRun ? 'planner run (hooks kept)'", 2),
            ("via: useRun ? 'run' : 'flat'", "via: useNative ? 'native-layer-colour' : useRun ? 'run' : 'flat'", 1),
            ('if (fresh && !useRun) rememberLast(E, P);', 'if (fresh && !useRun && !useNative) rememberLast(E, P);', 1),
            ('txt = textOf(frame) || text', 'txt = text || textOf(frame)', 1),
            ('var meas = fresh ? measureEntry(E, P.text, P.flat, host, false) : Promise.resolve(null);', '''// Native layer operations use the existing native report-only contract.
            // The zone reporter cannot safely trim a layer overlay into zone masks.
            var meas = fresh ? (useNative ? measureOnly(E, P.text, queue, host) : measureEntry(E, P.text, P.flat, host, false)) : Promise.resolve(null);''', 1),
            ("var m = measuredOf(rep, host), reverted", "var m = useNative && rep ? rep : measuredOf(rep, host), reverted", 1),
        ]
    return []
