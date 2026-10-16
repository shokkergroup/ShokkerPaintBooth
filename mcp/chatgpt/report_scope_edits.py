"""Bounded S3 patches: colour requests, honest coverage, async document guard."""
def snapshot_edits(source):
    old="return p ? { p: p, s: cap('livePreviewSpecImg'), t: Date.now() } : null;"
    stamp='W.SpbConversationScope ? W.SpbConversationScope.stamp() : null'
    if not source or old in source:
        return [(old,"return p ? { p: p, s: cap('livePreviewSpecImg'), t: Date.now(), documentStamp: "+stamp+' } : null;',1)]
    if 'function paneFull(id)' not in source or "p7: 'last-live'" not in source:
        raise RuntimeError('Unknown S3 snapshot shape; preserve source and review it')
    if 'function sigNow()' in source:
        # Claude P7c independently binds paint/spec to the applied preview.
        # Keep both signature checks, including stale-spec-only invalidation.
        rows = []
        for before in [
            "LASTLIVE = { p: p, s: paneFull('livePreviewSpecImg') && LASTLIVE ? LASTLIVE.s : cap('livePreviewSpecImg'), g: sigNow(), t: Date.now() };",
            "LASTLIVE = { p: p, s: s0, g: sigNow(), t: Date.now() };",
            "LASTLIVE = { p: B, s: paneFull('livePreviewSpecImg') && LASTLIVE ? LASTLIVE.s : SB, g: sigNow(), t: Date.now() };",
            'return { p: p, s: s0, t: Date.now() };',
            "return { p: p, s: cap('livePreviewSpecImg'), t: Date.now() };",
        ]:
            # Claude P7d also validates cached spec signatures in both remember paths.
            # Add ancestry without replacing that stronger spec guard.
            if before.startswith('LASTLIVE = { p: B,') and 'LASTLIVE = { p: B, s: SB, g: sigNow(), t: Date.now() };' in source:
                before = 'LASTLIVE = { p: B, s: SB, g: sigNow(), t: Date.now() };'
            elif before not in source and "paneFull('livePreviewSpecImg') && LASTLIVE ? LASTLIVE.s :" in before:
                before = before.replace("paneFull('livePreviewSpecImg') && LASTLIVE ? LASTLIVE.s :", "paneFull('livePreviewSpecImg') ? (LASTLIVE && LASTLIVE.g && LASTLIVE.g.s && LASTLIVE.g.s === sigNow().s ? LASTLIVE.s : null) :")
            rows.append((before, before.replace('t: Date.now()', 't: Date.now(), documentStamp: '+stamp), 1))
        before = "var L = LASTLIVE, g = sigNow(); return L && L.g && L.g.p && L.g.p === g.p ? { p: L.p, s: (L.g.s === g.s ? L.s : null), t: Date.now(), p7: 'last-live' } : null;"
        after = before.replace('L.g.p === g.p ?', 'L.g.p === g.p && (!W.SpbConversationScope || (L.documentStamp != null && W.SpbConversationScope.current(L.documentStamp))) ?').replace("t: Date.now(), p7:", "t: Date.now(), documentStamp: L.documentStamp, p7:")
        rows.extend([(before, after, 1), ('PEND = 0; return true; }', 'PEND = 0; LASTLIVE = null; return true; }', 1)])
        return rows
    # Preserve Claude's P7b current-preview hash check; document ancestry is an
    # additional requirement, never a replacement for his stale-preview fix.
    hashed = 'function curHash()' in source
    h = 'h: curHash(), ' if hashed else ''
    gate = ' && L.h && L.h === curHash()' if hashed else ''
    before = "LASTLIVE = { p: p, s: paneFull('livePreviewSpecImg') && LASTLIVE ? LASTLIVE.s : cap('livePreviewSpecImg'), " + h + 't: Date.now() };'
    cache = 'LASTLIVE = { p: p, s: s0, ' + h + 't: Date.now() };'
    rows = [
        (before, before.replace('t: Date.now()', 't: Date.now(), documentStamp: '+stamp), 1),
        ("var L = LASTLIVE; return L"+gate+" ? { p: L.p, s: L.s, t: Date.now(), p7: 'last-live' } : null;", "var L = LASTLIVE; return L"+gate+" && (!W.SpbConversationScope || (L.documentStamp != null && W.SpbConversationScope.current(L.documentStamp))) ? { p: L.p, s: L.s, t: Date.now(), documentStamp:L.documentStamp, p7: 'last-live' } : null;",1),
        (cache, cache.replace('t: Date.now()', 't: Date.now(), documentStamp: '+stamp), 1),
        ('return { p: p, s: s0, t: Date.now() };','return { p: p, s: s0, t: Date.now(), documentStamp: '+stamp+' };',1),
        ("return { p: p, s: cap('livePreviewSpecImg'), t: Date.now() };", "return { p: p, s: cap('livePreviewSpecImg'), t: Date.now(), documentStamp: "+stamp+' };',1),
        ('PEND = 0; return true; }', 'PEND = 0; LASTLIVE = null; return true; }',1),
    ]
    if hashed:
        after = "LASTLIVE = { p: B, s: paneFull('livePreviewSpecImg') && LASTLIVE ? LASTLIVE.s : SB, h: curHash(), t: Date.now() };"
        rows.append((after, after.replace('t: Date.now()', 't: Date.now(), documentStamp: '+stamp), 1))
    return rows

def edits(source=''):
    return [
        ('return { name: x.name, role: x.role };', 'return { id: x.id, name: x.name, group: x.group, role: x.role };', 1),
        ('    function layerObj(name) {', '''    function layerLabel(ref) { var row = layerObj(ref); return row ? (W.SpbLayerTargets ? W.SpbLayerTargets.label(row) : row.name) : String(ref); }
    function layerObj(name) {''', 1),
        ("w.push('the ' + l + ' layer');", "w.push('the ' + layerLabel(l) + ' layer');", 1),
        ("return 'the ' + l + ' layer';", "return 'the ' + layerLabel(l) + ' layer';", 2),
        ('        var wholeW = rd.whole ||', '''        // Exact parsed layer scope outranks a body/base word inside its name.
        var explicitLayers = null;
        try {
            var ep = W.SpbProEdit && W.SpbProEdit.plan(said, {layers:env.layers,palette:[],zoneColours:[]});
            if (ep && ep.kind === 'ops' && ep.layerScope && ep.ops.length && ep.ops.every(function(op){return op.target && /^(?:layer|colour)$/.test(op.target.kind) && op.target.layers && op.target.layers.length;})) {
                explicitLayers = uniq(ep.ops.reduce(function(a,op){return a.concat(op.target.layers);},[]));
                rd.layers = explicitLayers; rd.parts = []; rd.whole = false;
            }
        } catch (eLayerScope) {}
        var wholeW = !explicitLayers && (rd.whole ||''', 1),
        ("\\bit\\s+all\\b/i.test(said));", "\\bit\\s+all\\b/i.test(said)));", 1),
        *snapshot_edits(source),
        ('paint: 0, spec: 0, outside: 0,', 'paint: 0, surfacePaint: 0, surfaceChanged: 0, surfaceOutside: 0, spec: 0, outside: 0,', 1),
        ('o.changed++; if (dp > 28) o.paint++;', 'o.changed++; if (!M.surface || M.surface[i]) {o.surfaceChanged++; if (dp > 28) o.surfacePaint++; if (M.allow && !M.allow[i]) o.surfaceOutside++;} if (dp > 28) o.paint++;', 1),
        ('var whole = o.changed >= 0.6 * M.paintable, where;', 'var whole = o.surfaceChanged >= 0.6 * M.paintable, where;', 1),
        ("if (whole) { where = 'the whole car';", "if (sc.colour) where = 'the ' + sc.colour.word + ' areas';\n        else if (sc.layers.length && ls.length) where = ls.map(function(l){return 'the ' + layerLabel(l) + ' layer';}).join(' and ');\n        else if (whole) { where = M.coverageUnit === 'preview' ? 'most of the preview' : 'the whole car';", 1),
        ('shareOf(o.changed, M.paintable)', 'shareOf(o.surfaceChanged, M.paintable)', 2),
        ("' of the car changed, measured on the render)'", "' of the ' + M.coverageUnit + ' changed, measured on the render)'", 1),
        ("' of the car, measured on the render)'", "' of the ' + M.coverageUnit + ', measured on the render)'", 1),
        ("else if (r6Multi(text) &&", "else if (sc.colour && o.paint >= 30) col = ' to ' + (mf || 'a different colour');\n        else if (r6Multi(text) &&", 1),
        ('        PEND++;', '''        var documentStamp = s3b.documentStamp;
        function currentDocument() { return !W.SpbConversationScope || (documentStamp != null && W.SpbConversationScope.current(documentStamp)); }
        if (!currentDocument()) return Promise.resolve({verdict:'skip',why:'source document changed'});
        PEND++;''', 1),
        ('PEND = Math.max(0, PEND - 1); return v;', 'if (currentDocument()) PEND = Math.max(0, PEND - 1); return v;', 1),
        ('            if (entry.undone ||', "            if (!currentDocument()) return done({verdict:'skip',why:'source document changed'});\n            if (entry.undone ||", 1),
        ('var gp = grid(pm, Wd, Hd, \'centre\');', "var gp = grid(pm, Wd, Hd, 'centre'); M.surface = gp;", 1),
        ('            if (!M.paintable) M.paintable = N * N * 0.55;', "            M.coverageUnit = M.paintable ? 'car' : 'preview';\n            if (!M.paintable) { M.paintable = N * N; M.surface = null; }\n            sc.colour = W.SpbColourReportScope ? W.SpbColourReportScope.read(text, A) : null;\n            if (sc.colour && !sc.src) sc.src = 'said-colour';", 1),
        ('            M.allow = allowG;', '            if (sc.colour && !allowG) allowG = dilate(sc.colour.mask, 3); // same preview anti-alias allowance as named parts\n            M.allow = allowG;', 1),
        ('changed: o.changed, paint: o.paint, spec:', 'coverage_unit: M.coverageUnit, coverage_cells: M.paintable, surface_paint: o.surfacePaint, colour_target: sc.colour ? sc.colour.word : null, changed: o.changed, paint: o.paint, spec:', 1),
        # Owner W28 repeats the same criterion before a settled-preview retry.
        # Keep both decisions aligned and retain the actual stability guard.
        ('allowG && o.outside > Math.max(SMALL, 0.12 * o.changed)', 'allowG && o.outside > (sc.colour ? SMALL : Math.max(SMALL, 0.12 * o.changed))', 2 if 'if (M.w28 && !w28conf' in source and source.count('allowG && o.outside > Math.max(SMALL, 0.12 * o.changed)') == 2 else 1),
        ('var big = o.paint >= 0.5 * M.paintable,', 'var big = o.surfacePaint >= 0.5 * M.paintable,', 1),
        ('if (big && !wholeAsk && !prevBig &&', 'if (big && !sc.colour && !wholeAsk && !prevBig &&', 1),
        ('Math.round(100 * o.paint / M.paintable)', 'Math.round(100 * o.surfacePaint / M.paintable)', 1),
        ("            var fUW = rep.findings.filter", '''            // A colour target may cover most of the sheet; pixels outside that
            // named before-picture family are still an unauthorized spill.
            if (sc.colour && spill && askOnce('That changed areas outside the ' + sc.colour.word + ' paint you named, so I took it back. Nothing stayed changed. Shall we isolate that colour more carefully?', ['Try again', 'Show me the paint'])) { logR(rep); postLog(text, rep); ctx.render(); return done(rep); }
            var fUW = rep.findings.filter''', 1),
        ("                if (ASKED[key]) return false;", "                if (!currentDocument() || ASKED[key]) return false;", 1),
        ("p2 = Z.whenSettled(60000).then(function () { var B2", "p2 = Z.whenSettled(60000).then(function () { if (!currentDocument()) return o; var B2", 1),
        ('            return p2.then(function (o2) {', "            return p2.then(function (o2) {\n                if (!currentDocument()) return done({verdict:'skip',why:'source document changed'});", 1),
        ("shareOf(o.outside, M.paintable) + ' of the car outside '", "shareOf(o.surfaceOutside, M.paintable) + ' of the ' + M.coverageUnit + ' outside '", 1),
        ("}).catch(function (e) { done(null); return logR(", "}).catch(function (e) { done(null); if (!currentDocument()) return {verdict:'skip',why:'source document changed'}; return logR(", 1),
        # SPB-93: native exact-colour evidence loses partial-alpha art even
        # below decalMin. A tolerance is not proof of untouched artwork.
        # Append to retain the reviewed owner-promotion edit indices.
        *[("if (M.protect.length && o.decal < M.decalMin && sc.protectKinds && sc.protectKinds.length) " + var + " += ' Your ' + sc.protectKinds.sort().reverse().join(' and ') + ' ' + (sc.protectKinds.length > 1 || /s$/.test(sc.protectKinds[0]) ? 'are' : 'is') + ' untouched.';",
           "if (M.protect.length && o.decal < M.decalMin && sc.protectKinds && sc.protectKinds.length) " + var + " += o.decal > 0 ? ' The preview check detected small differences in protected artwork; preservation is unverified. Review the result or use Undo.' : ' The preview check found no change in protected artwork; it does not verify every pixel.';", 1) for var in ['s7', 's']],
        ("if (!ok) return; if (o.kind === 'layer' || o.kind === 'restore' || o.kind === 'carve') return;", """if (!ok) return;
                if (o.kind === 'layer') {
                    // MCP edit_layer need not include buyer_said. Retain its exact executed target.
                    if (o.colour != null) {
                        var targetLayer = W.SpbLayerTargets && W.SpbLayerTargets.resolve(o.layer, env.layers);
                        if (!targetLayer || !targetLayer.ok || targetLayer.row.id == null) { ok = false; return; }
                        ls.push(targetLayer.row.id);
                    }
                    return;
                }
                if (o.kind === 'restore' || o.kind === 'carve') return;""", 1),
        ("        else if (whole) { where = M.coverageUnit", "        else if (!sc.src) where = 'the preview';\n        else if (whole) { where = M.coverageUnit", 1),
        ("sc.src = 'plan'; sc.parts = ps; sc.layers = uniq(ls);", "sc.src = 'plan'; sc.parts = ps; sc.layers = uniq(ls); sc.nativeColourScope = q.every(function (op) { return op.kind === 'layer' && op.colour != null; });", 1),
        ('if (big && !sc.colour && !wholeAsk', 'if (big && !sc.colour && !(sc.nativeColourScope && allowG && o.outside <= SMALL) && !wholeAsk', 1),
    ]
