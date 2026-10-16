/* Exact identity guard around Claude's W20 per-piece resize; no raster kernel. */
(function(W){
    'use strict';
    function targetAPI(){if(!W.SpbLayerTargets)throw Error('Exact layer lookup is unavailable. Nothing was resized.');return W.SpbLayerTargets;}
    function roleLayer(role, layers){
        var T=targetAPI(),ref=role.id!=null?role.id:T.label(role),r=T.resolve(ref,layers);
        if(!r.ok)throw Error('The resize target '+T.label(role)+' is not unique in the current layers. Choose its full group and layer.');
        return r.row;
    }
    function editable(layers){
        layers.forEach(function(l){
            if(!l.img)throw Error('The source pixels for '+l.name+' are unavailable. Nothing was resized.');
            if(l.locked)throw Error(l.name+' is locked. Unlock that layer before resizing it. Nothing was resized.');
            if(l.visible===false)throw Error(l.name+' is hidden. Show that layer before resizing it. Nothing was resized.');
        });
        return layers;
    }
    function exactTargets(ids,layers,roles,element){
        if(!Array.isArray(ids)||!ids.length)throw Error('The exact resize target is missing. Nothing was resized.');
        var rx=element==='numbers'?/^numbers$/i:/logo|sponsor|decal/i,T=targetAPI();
        var result=ids.map(function(id){
            var hit=layers.filter(function(l){return l&&l.id===id;});
            if(hit.length!==1)throw Error('The resize layer changed or is missing. Choose its current full group and name.');
            var matched=roles.filter(function(r){try{return roleLayer(r,layers)===hit[0]&&rx.test(String(r.role||''));}catch(_){return false;}});
            if(matched.length!==1)throw Error(T.label(hit[0])+' is not a uniquely identified '+element+' layer. Nothing was resized.');
            return hit[0];
        });
        return editable(result);
    }
    function bind(text,steps,rows){
        var T=targetAPI(),scope=T.scope(text,rows||[]),explicit=/\blayers?\b/i.test(String(text||''));
        // The common scope reader leaves a unique bare name to colour parsing.
        // Resolve that exact suffix here without fuzzy matching or role widening.
        if(!scope&&explicit){
            var prefix=String(text||'').split(/\blayer\b/i)[0].trim().toLowerCase();
            var named=(rows||[]).filter(function(r){var n=String(r.name||'').toLowerCase();return n&&(prefix===n||prefix.endsWith(' '+n));});
            if(named.length){
                var longest=Math.max.apply(null,named.map(function(r){return r.name.length;}));
                named=named.filter(function(r){return r.name.length===longest;});
                var exact=T.resolve(named[0].name,rows||[]);
                scope=exact.ok?{layers:[exact.selector]}:{ask:{text:exact.reason}};
            }
        }
        if(scope&&scope.ask)return {ok:false,error:scope.ask.text};
        if(explicit&&(!scope||!scope.layers))return {ok:false,error:'Name one exact layer, including its group if needed, before resizing its artwork. Nothing was resized.'};
        if(!scope||!scope.layers)return {ok:true,steps:steps};
        if(steps.length!==1||scope.layers.length!==1)return {ok:false,error:'Resize one exact layer at a time so the other artwork stays in place.'};
        var found=T.resolve(scope.layers[0],rows||[]);
        if(!found.ok||found.row.id==null)return {ok:false,error:'The exact resize layer needs a current unique ID. Nothing was resized.'};
        var row=found.row,rx=steps[0].extra.w20x.element==='numbers'?/^numbers$/i:/logo|sponsor|decal/i;
        if(!rx.test(String(row.role||'')))return {ok:false,error:'That layer is not identified as the requested artwork. Select the separate numbers or sponsor layer; nothing was resized.'};
        if(row.locked||row.visible===false)return {ok:false,error:T.label(row)+(row.locked?' is locked. Unlock it':' is hidden. Show it')+' before resizing. Nothing was resized.'};
        var out=JSON.parse(JSON.stringify(steps)),x=out[0].extra.w20x;
        x.layer_ids=[row.id];x.layer_labels=[T.label(row)];
        x.document_stamp=W.SpbConversationScope&&W.SpbConversationScope.stamp?W.SpbConversationScope.stamp():null;
        out[0].extra.s5g=String(out[0].extra.s5g||'resize artwork').replace(/the sponsors and logos|the numbers/i,'the artwork on '+T.label(row)+' layer');
        return {ok:true,steps:out};
    }
    function validate(x,layers){
        if(x.document_stamp!=null&&(!W.SpbConversationScope||!W.SpbConversationScope.current(x.document_stamp)))throw Error('The paint changed after this resize was planned. Send the request again. Nothing was resized.');
        return editable(layers);
    }
    W.SpbElementResizeScope={bind:bind,roleLayer:roleLayer,exactTargets:exactTargets,validate:validate};
})(window);
