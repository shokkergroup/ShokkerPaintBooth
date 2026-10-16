from pathlib import Path


def edits(relative):
    if relative == 'js/spb-mcp-frames.js':
        return [
            ("        return ensure.then(function () { return host.apply(queue, { frame_steps: (pl.steps || []).length }); }).then(function (r) {", '''        var existingPatternReport = null;
        return ensure.then(function () {
            var C=W.SpbConversationScope;
            if(!W.SPB_CX3_OFF&&!special&&!repaired&&W.SpbNamedPatternRefinement&&C&&C.status().available)existingPatternReport=W.SpbNamedPatternRefinement.captureFrame(P.frame,pl,{zones:typeof zones==='undefined'?[]:zones,current:true,documentStamp:C.stamp()});
            return host.apply(queue, { frame_steps: (pl.steps || []).length });
        }).then(function (r) {''',1),
            ('            if (fresh && !useRun && !useNative) rememberLast(E, P);', '            if(fresh&&existingPatternReport)E._cxPatternReport=existingPatternReport;\n            if (fresh && !useRun && !useNative) rememberLast(E, P);',1),
        ]
    if relative == 'js/spb-intent-report.js':
        return [
            ("        var decals = roles.filter(function (x)",'''        var patternReport = r&&r.namedPattern ? r : entry&&entry._cxPatternReport;
        var patternScope = !W.SPB_CX3_OFF && W.SpbNamedPatternRefinement && W.SpbNamedPatternRefinement.receipt(patternReport,entry,{zones:typeof zones==='undefined'?[]:zones,current:!!(patternReport&&patternReport.namedPattern&&W.SpbConversationScope&&W.SpbConversationScope.current(patternReport.namedPattern.documentStamp))});
        if(patternScope){sc.src='plan';sc.layers=patternScope.source_layer_ids.map(function(id){var layer=roles.find(function(l){return String(l.id)===String(id);});return layer&&layer.name;}).filter(Boolean);sc.existing_pattern=patternScope;}
        var decals = roles.filter(function (x)''',1),
            ('!prevBig && !(entry.zdiff', '!prevBig && !sc.existing_pattern && !(entry.zdiff',1),
        ]
    if relative == 'js/spb-pbn.js':
        return [('                var readState3 = B && B.state ? B.state() : null,', '''                var handledPattern = B && B.state && B.state()._handledPattern;
                if (W.SpbNamedPatternRefinement && (W.SpbNamedPatternRefinement.parse(S.text) || (handledPattern && handledPattern.text === S.text && W.SpbConversationScope && W.SpbConversationScope.current(handledPattern.stamp)))) { CUR = null; off = true; }
                var readState3 = B && B.state ? B.state() : null,''',1)]
    if relative != 'js/spb-pro-ai.js':
        return []
    module = Path(__file__).with_name('named-pattern-refinement.js').read_text(encoding='utf-8')
    handler = '''    var _patternAdviceSnapshot = null;
    function rememberPatternAdvice(reply) {
        var a=reply&&reply.answer,P=window.SpbNamedPatternRefinement,z=typeof selectedZoneIndex==='undefined'?null:zones[selectedZoneIndex];
        _patternAdviceSnapshot=null;
        if(!a||a.editor_topic!=='pattern'||a.needs_pattern_target||!z||String(z.id)!==String(a.pattern_zone_id)||P.patternId(z)!==a.pattern_id)return;
        try{_patternAdviceSnapshot={answer:a,target:z,signature:undoSigNow(),stamp:a.document_stamp};}catch(ePA){}
    }
    function namedPatternAdvice(text,previous) {
        var P=window.SpbNamedPatternRefinement,s=_patternAdviceSnapshot,unchanged=false;
        if(!P.adviceShape(text))return null;
        try{var now=undoSigNow();unchanged=!!s&&undoSameZones(s.signature,now)&&undoSameLayers(s.signature.layers,now.layers);}catch(ePA){}
        return P.advice(text,previous,{zones:zones,selected:typeof selectedZoneIndex==='undefined'?-1:selectedZoneIndex,snapshot:s,current:!!(s&&window.SpbConversationScope&&SpbConversationScope.current(s.stamp)),unchanged:unchanged});
    }
    function namedPatternFollowup(text) {
        var P=window.SpbNamedPatternRefinement,N=window.SpbNamedZoneMaterial,entry=N&&N.previous(_log),ctx=entry&&entry.editCtx&&entry.editCtx.named_pattern;
        if(!ctx||!P.followupShape(text))return null;
        var now=null,unchanged=false;try{now=undoSigNow();unchanged=undoSameZones(entry.undoAfter,now)&&undoSameLayers(entry.undoAfter&&entry.undoAfter.layers,now.layers);}catch(eNP){}
        return P.followup(text,entry,{zones:zones,current:!!(window.SpbConversationScope&&SpbConversationScope.current(ctx.documentStamp)),unchanged:unchanged});
    }
    function offlineNamedPatternAsk(text,p) {
        var P=window.SpbNamedPatternRefinement,C=window.SpbConversationScope;
        if(p.kind==='clarify')return Promise.resolve(editReply(p.question));
        if(!C||!C.status().available)return Promise.resolve(editReply('Wait for this project to finish loading, then ask again. Nothing changed.'));
        var found=P.resolve(zones,p,typeof selectedZoneIndex==='undefined'?-1:selectedZoneIndex);if(found.kind!=='zone')return Promise.resolve(editReply(found.question));
        var z=found.zone,stamp=C.stamp(),pid=P.patternId(z);
        _busy=true;_progress='Checking the existing pattern';render();
        return warm(5000).then(function(){
            _busy=false;var current=P.resolve(zones,p,typeof selectedZoneIndex==='undefined'?-1:selectedZoneIndex);
            if(!C.current(stamp)||current.zone!==z||P.patternId(z)!==pid)return editReply('The project or pattern changed while I was checking it. Nothing changed; ask again.');
            if(p.adviceSnapshot){var now=undoSigNow(),s=p.adviceSnapshot;if(s.target!==z||!undoSameZones(s.signature,now)||!undoSameLayers(s.signature.layers,now.layers))return editReply('The paint changed while I was checking the pattern. Ask about its current settings again; nothing changed.');}
            var r=s5RunReply(text,null,P.frame(z,p));
            if(!r)return editReply('I could not prepare a scale adjustment for that existing pattern, or it is already at the limit. Nothing changed.');
            r.namedPattern={target:z,patternId:pid,beforeScale:Number(typeof z.pattern==='object'?z.pattern.scale:z.scale),selectors:P.selectors(z),documentStamp:stamp};
            r.editCtx={named_pattern:{zoneId:String(z.id),zoneName:z.name,patternId:pid,dir:p.dir,documentStamp:stamp}};
            return r;
        });
    }
'''
    hook = '''        var namedPattern = !window.SPB_CX3_OFF && window.SpbOfflineBuilder && SpbOfflineBuilder.offlineMode() && (window.SpbNamedPatternRefinement.parse(text) || patternAdviceRequest || namedPatternFollowup(text));
        if(namedPattern){
            try{captureOriginal();}catch(eNP){}
            if(SpbOfflineBuilder.showSteps)SpbOfflineBuilder.showSteps([],text);
            if(SpbOfflineBuilder.state)SpbOfflineBuilder.state()._handledPattern={text:text,stamp:window.SpbConversationScope&&SpbConversationScope.stamp()};
            if(window.SpbPbn&&SpbPbn.draw)SpbPbn.draw();
            _reqText=text;_specOnlyReq=false;_beforeImg=null;
            offlineNamedPatternAsk(text,namedPattern).then(function(r){return finish(r,text,'ask');}).then(function(){
                if(SpbOfflineBuilder.state)SpbOfflineBuilder.state()._handledPattern={text:text,stamp:window.SpbConversationScope&&SpbConversationScope.stamp()};
                if(window.SpbPbn&&SpbPbn.draw)SpbPbn.draw();
            });return;
        }
'''
    return [
        ('    function offlineNamedZoneMaterial(parsed) {',module+'\n'+handler+'    function offlineNamedZoneMaterial(parsed) {',1),
        ('        // Advice is handled before option-pick / complaint / edit parsers.', '''        var patternAdviceRequest = !window.SPB_CX3_OFF && window.SpbOfflineBuilder && SpbOfflineBuilder.offlineMode() && window.SpbEditorCapabilities ? namedPatternAdvice(text,SpbEditorCapabilities.previousFrom(SpbOfflineBuilder.state&&SpbOfflineBuilder.state(),_log)) : null;
        // Advice is handled before option-pick / complaint / edit parsers.''',1),
        ('            if (editorRead) editorRead.in_chat = true;', '            if (editorRead) {editorRead.in_chat = true;rememberPatternAdvice(editorRead);}',1),
        ('        _visHiddenOk = false; var replyCard',hook+'        _visHiddenOk = false; var replyCard',1),
    ]
