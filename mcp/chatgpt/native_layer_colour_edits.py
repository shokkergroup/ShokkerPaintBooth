"""Private native colour adapter: existing layer FX setter + existing Undo path."""
def edits(relative, original=''):
    if relative == 'js/spb-pro-ai.js':
        return [
            ("                    if (m) { out0.result.measured = m;", """                    // Show measured evidence even if the external assistant exits before replying.
                    if (m && m.line && m.verdict !== 'not_measured' && m.verdict !== 'skip' && !mcpStaleResult(mcpContext, !!ap.lines.length)) {
                        entry.text += '\\nPreview check (estimated): ' + m.line + ' This preview check does not verify every source pixel.';
                        render();
                    }
                    if (m) { out0.result.measured = m;""", 1),
            ('        var lres = lops.length ? applyLayerOps(lops, mcpContext) : { lines: [], failed: [], undoSteps: 0 };\n', '', 1),
            ('        try {\n            zones.forEach(function (z) { if (z) idsBefore[String(z.id)] = 1; });', """        // SPB-93: a layer edit invalidates the preview. Capture before either layer or zone mutation.
        var lres = lops.length ? applyLayerOps(lops, mcpContext) : { lines: [], failed: [], undoSteps: 0 };
        try {
            zones.forEach(function (z) { if (z) idsBefore[String(z.id)] = 1; });""", 1),
            ('var lines = [], failed = [], before = -1;', 'var lines = [], failed = [], colourOutcomes = [], before = -1;', 1),
            ('return { lines: lines, failed: failed, undoSteps:', 'return { lines: lines, failed: failed, colourOutcomes: colourOutcomes, undoSteps:', 1),
            ('return { results: results, lines: lines, failed: failed, layerUndo:', 'return { results: results, lines: lines, failed: failed, colourOutcomes: lres.colourOutcomes || [], layerUndo:', 1),
            ('applied: ap.lines, zones_touched:', 'applied: ap.lines, layer_colour_outcomes: ap.colourOutcomes || [], zones_touched:', 1),
            ('            entry.lines = ap.lines; if (entry._budget)', """            entry.colourOutcomes = ap.colourOutcomes || [];
            if (r.offline && ap.colourOutcomes && ap.colourOutcomes.length && r.queue.every(function (o) { return o.kind === 'layer' && o.colour != null; })) {
                entry.text = ap.colourOutcomes.map(function (o) { return o.line; }).join(' ');
            }
            entry.lines = ap.lines; if (entry._budget)""", 1),
            ('return { layerColours: function (nm)', """return { sourceLayerPixels: function (ref) {
            return window.SpbNativeLayerColour ? SpbNativeLayerColour.inspect(ref, {layers:typeof _psdLayers !== 'undefined' ? _psdLayers : [],busy:!!((typeof isDrawing !== 'undefined' && isDrawing)||(typeof _activeLayerCanvas !== 'undefined' && _activeLayerCanvas)||(typeof freeTransformState !== 'undefined' && freeTransformState && freeTransformState.active))}, false) : {error:'Source-layer inspection is unavailable.'};
        }, layerColours: function (nm)""", 1),
            ("        var pl = null; try { pl = IP.plan(frame, IP.live()); }", """        // Native builder may mark a colour step s5only and pass ed=null.
        // Reconstruct above, then require agreement with the complete typed request.
        var nativeFrame = !_specOnlyReq && window.SpbNativeLayerColour ? SpbNativeLayerColour.queue(ed, editEnv()) : null;
        if (nativeFrame && nativeFrame.error) return editReply(nativeFrame.error, [], {cannot:true});
        if (nativeFrame && !nativeFrame.error) {
            var typedNative = SpbNativeLayerColour.queue(E.plan(text, editEnv()), editEnv());
            if (typedNative && !typedNative.error && JSON.stringify(typedNative.queue) === JSON.stringify(nativeFrame.queue))
                return {offline:true,text:nativeFrame.text,queue:nativeFrame.queue,usage:{cost:0},calls:0,model:'built-in',tools:['edit_layer']};
            return editReply('The colour step and complete request no longer agree. Review the step before running it.', [], {cannot:true});
        }
        var pl = null; try { pl = IP.plan(frame, IP.live()); }""", 1),
            ('            var pr5 = s5RunReply(text, ed, ob.s5frame);', """            // Exact source-layer colour must use the native operation before the generic zone planner.
            // Box/post-processing and spec-only runs retain their existing routes.
            var nativeBuilder = !ob.s5only && !ob.post && !ob.specOnly && window.SpbNativeLayerColour ? SpbNativeLayerColour.queue(ed, editEnv()) : null;
            if (nativeBuilder) {
                var nativeReply = nativeBuilder.error ? editReply(nativeBuilder.error, [], {cannot:true}) : {offline:true,text:nativeBuilder.text,queue:nativeBuilder.queue,usage:{cost:0},calls:0,model:'built-in',tools:['edit_layer']};
                render(); return Promise.resolve(nativeReply).then(function (r) { return finish(r, text, 'ask', {builderRunReceipt:ob.runReceipt}); });
            }
            var pr5 = s5RunReply(text, ed, ob.s5frame);""", 1),
            ('{ id: l.id, v: l.visible, o: l.opacity, b: l.blendMode }', '{ id: l.id, v: l.visible, o: l.opacity, b: l.blendMode, img: l.img, fx: l.effects === undefined ? undefined : JSON.parse(JSON.stringify(l.effects)) }', 1),
            ("(a.b || 'source-over') === (b.b || 'source-over');", "(a.b || 'source-over') === (b.b || 'source-over') && a.img === b.img && JSON.stringify(a.fx) === JSON.stringify(b.fx);", 1),
            ('if (l.visible === b.v && l.opacity === b.o && l.blendMode === b.b) return;', 'if (l.visible === b.v && l.opacity === b.o && l.blendMode === b.b && l.img === b.img && JSON.stringify(l.effects) === JSON.stringify(b.fx)) return;', 1),
            ('            lch++;\n        });', """            // Private59910 native colour acceptance: chat Undo omitted FX and falsely reported restoration.
            // Restore this entry's effects only while no later effect change owns them.
            if (fullL || !al[b.id] || JSON.stringify(l.effects) === JSON.stringify(al[b.id].fx)) {
                if (b.fx === undefined) delete l.effects; else l.effects = JSON.parse(JSON.stringify(b.fx));
            }
            // Same immutable drawable contract as native _pushLayerUndo.
            // A later edit owns a different image and must not be overwritten.
            if (b.img && (fullL || !al[b.id] || l.img === al[b.id].img)) l.img = b.img;
            lch++;
        });""", 1),
            ('out.push({ id: l.id, name: l.name,', 'out.push({ id: l.id, colour_overlay: window.SpbNativeLayerColour ? SpbNativeLayerColour.overlay(l) : undefined, name: l.name,', 1),
            ('        if (ed.kind === \'describe\') {', """        var nativeColour = window.SpbNativeLayerColour && SpbNativeLayerColour.queue(ed, editEnv());
        if (nativeColour) return Promise.resolve(nativeColour.error ? editReply(nativeColour.error, []) : {offline:true,text:nativeColour.text,queue:nativeColour.queue,usage:{cost:0},calls:0,model:'built-in',tools:['edit_layer']});
        if (ed.kind === 'describe') {""", 1),
            ("blend: { type: 'string' } }, required: ['layer']", "blend: { type: 'string' }, colour: {type:'string'}, colour_opacity: {type:'number'}, source_colour:{type:'string'}, replace_tolerance:{type:'number'} }, required: ['layer']", 1),
            ("                  var curVis = l.visible !== false", """                  var nativePatch = a.colour == null ? null : window.SpbNativeLayerColour && SpbNativeLayerColour.patch(a.colour, a.colour_opacity);
                  if (a.colour != null && (!nativePatch || nativePatch.error)) return {error:nativePatch ? nativePatch.error : 'Native layer colour controls are not ready.'};
                  if (a.colour == null && a.colour_opacity != null) return {error:'Supply a layer colour with its amount.'};
                  if (a.source_colour != null) {
                      var replacementPatch = window.SpbNativeLayerColour && SpbNativeLayerColour.replacement(a.colour,a.source_colour,a.replace_tolerance);
                      if (!replacementPatch || replacementPatch.error) return {error:replacementPatch ? replacementPatch.error : 'Native colour replacement is not ready.'};
                      if (a.colour_opacity != null && a.colour_opacity !== 100) return {error:'Source-colour replacement requires colour_opacity 100 or omitted.'};
                      if (a.visible != null || a.opacity != null || a.blend != null) return {error:'Apply source-colour replacement separately from visibility, opacity or blending changes.'};
                      nativePatch = replacementPatch;
                  } else if (a.replace_tolerance != null) return {error:'Supply source_colour with replace_tolerance.'};
                  var curVis = l.visible !== false""", 1),
            ('a.opacity == null && a.blend == null) return { ok: true, note:', 'a.opacity == null && a.blend == null && a.colour == null) return { ok: true, note:', 1),
            ('a.visible == null && a.blend == null) return { ok: true, note:', 'a.visible == null && a.blend == null && a.colour == null) return { ok: true, note:', 1),
            ('a.visible == null && a.opacity == null) return { ok: true, note:', 'a.visible == null && a.opacity == null && a.colour == null) return { ok: true, note:', 1),
            ("var op = { kind: 'layer', layer: l.id, name: l.name, visible: a.visible, opacity: a.opacity, blend: a.blend };", "var op = { kind: 'layer', layer: l.id, name: l.name, visible: a.visible, opacity: a.opacity, blend: a.blend, colour: nativePatch && nativePatch.colour, colourOpacity: nativePatch && nativePatch.colourOpacity, sourceColour: nativePatch && nativePatch.sourceColour, replaceTolerance: nativePatch && nativePatch.replaceTolerance };", 1),
            ("                        if (bits.length) lines.push('Layer ' + o.name", """                        if (o.colour != null) {
                            var colourResult = window.SpbNativeLayerColour ? SpbNativeLayerColour.apply(o,l) : {error:'Native layer colour controls are not ready.'};
                            if (window.SpbNativeLayerColour) colourOutcomes.push(SpbNativeLayerColour.outcome(o,colourResult));
                            if (colourResult.error) failed.push((o.name||'Layer')+': '+colourResult.error); else if (!colourResult.unchanged) bits.push('colour '+o.colour);
                        }
                        if (bits.length) lines.push('Layer ' + o.name""", 1),
            ("                    lines.push('Layer ' + o.name + ': ' + (bits.join(', ') || 'unchanged'));", """                    if (o.colour != null) {
                        var nativeResult = window.SpbNativeLayerColour ? SpbNativeLayerColour.apply(o,l) : {error:'Native layer colour controls are not ready.'};
                        if (window.SpbNativeLayerColour) colourOutcomes.push(SpbNativeLayerColour.outcome(o,nativeResult));
                        if (nativeResult.error) failed.push((o.name||'Layer')+': '+nativeResult.error); else if (!nativeResult.unchanged) bits.push('colour '+o.colour);
                    }
                    if (bits.length || o.colour == null) lines.push('Layer ' + o.name + ': ' + (bits.join(', ') || 'unchanged'));""", 1),
            ("if (!bits.length && failed.length === failedBeforeOperation) lines.push('Layer ' + o.name + ': unchanged');", "if (!bits.length && o.colour == null && failed.length === failedBeforeOperation) lines.push('Layer ' + o.name + ': unchanged');", 1),
        ]
    if relative == 'mcp/server/index.js':
        adopted = 'let NATIVE_LAYER_COLOUR = null' in original
        native_name = 'PRIVATE_LAYER_COLOUR' if adopted else 'NATIVE_LAYER_COLOUR'
        tools_before = '  return NATIVE_LAYER_COLOUR ? out.map(NATIVE_LAYER_COLOUR.tool) : out;' if adopted else '  return out;\n}\n\n// M2'
        tools_after = '  return NATIVE_LAYER_COLOUR ? out.map(NATIVE_LAYER_COLOUR.tool).map(PRIVATE_LAYER_COLOUR.tool) : out;' if adopted else '  return out.map(NATIVE_LAYER_COLOUR.tool);\n}\n\n// M2'
        result = [
            ("const CAR_KNOWLEDGE = require('../chatgpt/car-knowledge/lookup.cjs');", f"const {native_name} = require('../chatgpt/native-layer-colour.js');\nconst CAR_KNOWLEDGE = require('../chatgpt/car-knowledge/lookup.cjs');", 1),
            (tools_before, tools_after, 1),
            ('instructions: INSTRUCTIONS });', "instructions: INSTRUCTIONS + '\\nFor an entire paint-layer colour-only change, use spb_edit_layer with the exact current group/layer (or ID) and colour #RRGGBB. This uses the native layer colour effect and preserves layers above it. It is not a whole-car zone. Read colour_overlay in current STATE. For exact source-RGB replacement inside one paint layer use source_colour and colour with spb_edit_layer (optional replace_tolerance, default40); this edits source pixels through native Color Replace and chat Undo restores them. Material/finish changes use their scoped tools; do not apply paint colour to spec/alpha map layers.' });", 1),
        ]
        if adopted:
            result[-1] = ('Colour changes inside a layer or material/finish changes use their scoped tools;', 'For exact source-RGB replacement inside one paint layer use source_colour and colour with spb_edit_layer (optional replace_tolerance, default40); this edits source pixels through native Color Replace and chat Undo restores them. Material/finish changes use their scoped tools;', 1)
        return result
    return []
