"""Reuse native material builder/queue/Undo for exact named zones; shared files read-only."""
from pathlib import Path

def edits(relative):
    if relative == 'js/spb-pbn.js':
        return [("                var readState3 = B && B.state ? B.state() : null,", "                var handledMaterial = B && B.state && B.state()._handledMaterial;\n                if (W.SpbNamedZoneMaterial && (W.SpbNamedZoneMaterial.parse(S.text) || (handledMaterial && handledMaterial.text === S.text && W.SpbConversationScope && W.SpbConversationScope.current(handledMaterial.stamp)))) { CUR = null; off = true; }\n                var readState3 = B && B.state ? B.state() : null,", 1)]
    if relative == 'js/spb-intent-report.js':
        return [("            var dm = dims(), Wd = dm[0]", """            // Exact named-zone channel operations use their declared channel,
            // not the generic >28 visual-difference threshold (a +10 step is real).
            if (!W.SPB_CX3_OFF && r && r.namedMaterial && W.SpbNamedZoneMaterial) {
                var nm = r.namedMaterial, measured = W.SpbNamedZoneMaterial.measure(A,B,SA,SB,nm.channel,nm.delta);
                var nmLine = measured && measured.verified ? 'Measured in the spec preview: ' + nm.channel + ' changed; paint colours and the other channels are unchanged.' : !measured ? 'The channel adjustment ran, but a current before-and-after spec preview was unavailable for verification.' : measured.paint || measured.otherChannels || measured.wrongDirection ? 'The preview differs beyond the requested material change. Use Undo to take it back.' : 'The setting changed, but no spec-preview difference was measured. The zone may be covered by another zone or the channel may already be clipped.';
                var nmRep = {v:1,mode:m,verdict:measured && measured.verified ? 'ok' : 'reported',line:nmLine,channel:nm.channel,measurement:measured,scope:'Channel-level preview check; exact zone targeting uses the native edit_zone kernel.'};
                entry.text += '\\n' + nmLine; entry.s3=nmRep; logR(nmRep); postLog(text,nmRep); try{ctx.render();}catch(eNM){} return done(nmRep);
            }
            var dm = dims(), Wd = dm[0]""",1)]
    if relative != 'js/spb-pro-ai.js':
        return []
    module = Path(__file__).with_name('named-zone-material.js').read_text(encoding='utf-8')
    handler = '''    function offlineNamedZoneMaterial(parsed) {
        var N = window.SpbNamedZoneMaterial, MC = window.SpbMaterialControls;
        var found = N.resolve(zones, parsed);
        if (found.kind !== 'zone') return editReply(found.question);
        var z = found.zone, edit = MC && MC.buildEdit ? MC.buildEdit(z, parsed) : null;
        if (edit && edit.kind === 'noop') return editReply('That channel is already at the requested adjustment limit. Nothing was changed.');
        if (!edit || edit.kind !== 'edit') return editReply('I could not read that zone’s material settings. Nothing was changed.');
        var slot = parsed.channel === 'metalness' ? 'metal' : parsed.channel === 'roughness' ? 'rough' : 'clearcoat';
        var before = {id:String(z.id),metal:Number(z.specShiftR)||0,rough:Number(z.specShiftG)||0,clearcoat:Number(z.specShiftB)||0};
        var delta = edit.spec_shift[slot] - before[slot];
        delete edit.kind;
        // Identity cannot be supplied through JSON: only this local adapter
        // passes the live zone object, and doEdit admits spec_shift alone.
        edit._spbNamedChannelTarget = z;
        var queue = [], tool = null;
        makeTools(queue).forEach(function(t){if(t.name === 'edit_zone') tool=t;});
        var result = tool && tool.handler(edit);
        if (!result || result.error || queue.length !== 1) return editReply('I could not adjust that zone: ' + ((result && result.error) || 'the target could not be resolved') + '. Nothing was changed.');
        queue[0]._spbMaterialBefore = before;
        queue[0]._spbNamedMaterialBefore = {zone:z,name:z.name,muted:z.muted,locked:z.locked,region:z.regionMask,spatial:z.spatialMask,document:window.SpbConversationScope && SpbConversationScope.stamp()};
        return editReply('Adjusting “' + z.name + '” ' + parsed.channel + ' ' + (delta > 0 ? 'up' : 'down') + ' by ' + Math.abs(delta) + ' points. Its paint colours, finish and other material channels stay the same.', ['Undo'], {queue:queue,tools:['edit_zone'],namedMaterial:{channel:parsed.channel,delta:delta},editCtx:{named_material:{zoneId:String(z.id),zoneName:z.name,channel:parsed.channel,delta:delta,documentStamp:SpbConversationScope.stamp()}}});
    }
    function namedMaterialFollowup(text) {
        var N=window.SpbNamedZoneMaterial, entry=N.previous(_log), ctx=entry&&entry.editCtx&&entry.editCtx.named_material;
        if(!ctx || !N.followupShape(text))return null;
        var now=null, unchanged=false;
        try { now=undoSigNow(); unchanged=undoSameZones(entry.undoAfter,now)&&undoSameLayers(entry.undoAfter&&entry.undoAfter.layers,now.layers); } catch(eNM){}
        return N.followup(text,entry,{zones:zones,current:!!(window.SpbConversationScope&&SpbConversationScope.current(ctx.documentStamp)),unchanged:unchanged});
    }
'''
    return [
        ("cleanArgs = strip(a); delete cleanArgs._spbPartRegKey;", "cleanArgs = strip(a), namedChannelTarget = a._spbNamedChannelTarget; delete cleanArgs._spbNamedChannelTarget; delete cleanArgs._spbPartRegKey;", 1),
        ("var autoNote = preservePartSelector ? null : protectDecals(spec, zones[i]),", "var preserveNamedSelector = namedChannelTarget === zones[i] && Object.keys(cleanArgs).length === 1 && !!cleanArgs.spec_shift && Object.keys(spec).every(function(k){return k === 'spec_shift';});\n                  var autoNote = (preservePartSelector || preserveNamedSelector) ? null : protectDecals(spec, zones[i]),", 1),
        ('    function offlineMaterialPlan(text) {', module + '\n' + handler + '    function offlineMaterialPlan(text) {\n        var named = !window.SPB_CX3_OFF && window.SpbNamedZoneMaterial.parse(text); if (named) return named;', 1),
        ("        _busy = true; _progress = 'Checking the current part material'; render();", """        var namedScope = null, namedTarget = null;
        if (parsed.namedZone) {
            if (!window.SpbConversationScope || !SpbConversationScope.status().available) return Promise.resolve(editReply('Wait for this project to finish loading, then ask again. Nothing was changed.'));
            namedScope = SpbConversationScope.stamp();
            var namedFound = window.SpbNamedZoneMaterial.resolve(zones,parsed);
            if (namedFound.kind !== 'zone') return Promise.resolve(editReply(namedFound.question));
            namedTarget = namedFound.zone;
        }
        _busy = true; _progress = 'Checking the current part material'; render();""", 1),
        ("            var MC = window.SpbMaterialControls, probe = null;", """            if (parsed.namedZone) {
                var currentNamed = window.SpbNamedZoneMaterial.resolve(zones,parsed);
                if (!SpbConversationScope.current(namedScope) || currentNamed.zone !== namedTarget) return editReply('The project or zone changed while I was checking it. Nothing was changed; ask again on the current project.');
                return offlineNamedZoneMaterial(parsed);
            }
            var MC = window.SpbMaterialControls, probe = null;""", 1),
        ("            if (q._spbMaterialBefore) {", """            if (q._spbNamedMaterialBefore) {
                var nb = q._spbNamedMaterialBefore, nz = zones[q.zone];
                if (!nz || nz !== nb.zone || nz.name !== nb.name || nz.muted !== nb.muted || nz.locked !== nb.locked || nz.regionMask !== nb.region || nz.spatialMask !== nb.spatial || (nb.document != null && (!window.SpbConversationScope || !SpbConversationScope.current(nb.document)))) {
                    byIndex[i] = {ok:false,applied:[],warnings:['the zone or document changed after this request; ask again'],index:q.zone}; return;
                }
            }
            if (q._spbMaterialBefore) {""", 1),
        ("        /* W24L 2026-10-10:", """        var namedMaterial = !window.SPB_CX3_OFF && window.SpbOfflineBuilder && SpbOfflineBuilder.offlineMode() && (window.SpbNamedZoneMaterial.parse(text) || namedMaterialFollowup(text));
        if (namedMaterial) {
            try { captureOriginal(); } catch (eNM) {}
            // The completed chat operation owns this request. Retire the old
            // FAQ/proposal dock so its controls cannot contradict the new result.
            if (SpbOfflineBuilder.showSteps) SpbOfflineBuilder.showSteps([],text);
            if (SpbOfflineBuilder.state) SpbOfflineBuilder.state()._handledMaterial = {text:text,stamp:window.SpbConversationScope && SpbConversationScope.stamp()};
            if (window.SpbPbn && SpbPbn.draw) SpbPbn.draw();
            _reqText = text; _specOnlyReq = true; _beforeImg = null;
            offlineMaterialAsk(text,namedMaterial).then(function(r){finish(r,text,'ask');}); return;
        }
        /* W24L 2026-10-10:""", 1),
    ]
