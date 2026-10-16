(function(W){
    'use strict';
    function context(plan,queue){
        var E=W.SpbProEdit,ctx=E&&E.ctxOf(plan),q=queue||[];
        if(!ctx||q.length!==1||q[0].kind!=='layer'||q[0].sourceColour||q[0].colourOpacity!==100)return ctx;
        ctx.native_layer_colour={id:q[0].layer,colour:q[0].colour,document_stamp:W.SpbConversationScope?W.SpbConversationScope.stamp():null};
        return ctx;
    }
    function ask(text){return {kind:'ask',text:text,chips:[],layer_target_question:true};}
    function validate(op,env){
        var ref=op&&op._nativeColourRefinement;if(!ref)return null;
        if(!W.SpbConversationScope||!W.SpbConversationScope.current(ref.document_stamp))return 'The paint changed after this refinement was planned. Ask for the adjustment again. Nothing changed.';
        var t=op.target,hit=W.SpbLayerTargets.resolve(ref.id,W._psdLayers||[]);
        if(!t||t.kind!=='layer'||(t.layers||[]).length!==1||t.layers[0]!==ref.id||!hit.ok||hit.row.id!==ref.id)return 'The refinement target changed. Ask for the adjustment again. Nothing changed.';
        var o=W.SpbNativeLayerColour.overlay(hit.row);
        if(hit.row.locked||hit.row.visible===false||!o||!o.enabled||o.opacity!==100||o.blend!=='source-over'||o.colour!==ref.colour)return 'The layer changed after this refinement was planned. Ask for the adjustment again. Nothing changed.';
        return null;
    }
    function plan(text,env){
        var s=String(text||'').trim().toLowerCase(),last=env&&env.last,n=last&&last.native_layer_colour;
        if(!n)return null;
        var m=/^(?:(?:make\s+(?:it|that|this)\s+)|(?:a\s+))?(?:(?:little|bit)\s+)?(darker|lighter|brighter|deeper|richer|paler)(?:\s+(red|blue|green|yellow|orange|purple|pink|brown|black|white|grey|gray))?(?:\s+again)?(?:,?\s+please)?[.!?]*$/.exec(s);
        if(!m)return null;
        var T=W.SpbLayerTargets,E=W.SpbProEdit,N=W.SpbNativeLayerColour;
        if(!W.SpbConversationScope||!W.SpbConversationScope.current(n.document_stamp))return ask('The paint changed since that colour edit. Choose the current layer before refining it. Nothing changed.');
        var r=T&&T.resolve(n.id,(env||{}).layers),live=T&&T.resolve(n.id,W._psdLayers||[]);
        if(!r||!r.ok||!live||!live.ok||r.row.id!==n.id||live.row.id!==n.id)return ask('That layer is no longer available. Choose the current layer before refining its colour. Nothing changed.');
        if(live.row.locked||live.row.visible===false)return ask('That layer is locked or hidden. Nothing changed.');
        var o=N&&N.overlay(live.row);
        if(!o||!o.enabled||o.opacity!==100||o.blend!=='source-over'||o.colour!==n.colour)return ask('That layer colour has changed since my last edit. Tell me which current colour to refine. Nothing changed.');
        if(m[2]&&(m[2]==='gray'?'grey':m[2])!==E.familyOf(o.colour))return ask('My last colour edit was on '+r.label+'. Which layer should get the '+m[2]+' adjustment? Nothing changed.');
        if(!E.shadeColour)return ask('Layer colour refinement is unavailable in this build. Nothing changed.');
        var colour=E.shadeColour(o.colour,m[1]);
        return {kind:'ops',ops:[{target:{kind:'layer',layers:[r.row.id],word:r.label},colour:{hex:colour,exact:true,name:m[1]+' '+(m[2]||'colour')},_nativeColourRefinement:{id:n.id,colour:n.colour,document_stamp:n.document_stamp}}],text:String(text),raw:String(text),unknown:[],alt:[],usedLast:true};
    }
    W.SpbLayerColourFollowup={context:context,plan:plan,validate:validate};
})(window);
