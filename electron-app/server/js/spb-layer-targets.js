/* CX3 2026-10-09 (CODEX-INTEGRATE-2): production copy of mcp/chatgpt/layer-targets.js (sha256 c43af610e4043ca3, body unchanged).
   window.SpbLayerTargets resolves a layer reference to ONE exact layer (full 'Group / Layer' path or a unique current id); refuses to guess when names repeat.
   Action-free helper: it never paints by itself. Callers are guarded by window.SPB_CX3_OFF (kill switch).
   Origin: Codex request REQUESTS_FOR_CLAUDE.md 'Shared layer intelligence' / 'Shared native-colour and Undo delta'. */
(function(W){
    'use strict';
    function norm(s){return String(s==null?'':s).toLowerCase().replace(/[_-]+/g,' ').replace(/\s+/g,' ').trim();}
    function group(l){return String(l.groupName||l.group||'');}
    function label(l){return group(l)?group(l)+' / '+l.name:String(l.name);}
    function select(l,rows){
        if(!l)return {ok:false,reason:'Layer is missing.'};
        var same=rows.filter(function(x){return x&&norm(x.name)===norm(l.name);});
        if(same.length===1&&!rows.some(function(x){return x&&x!==l&&x.id===l.name;}))return {ok:true,selector:l.name,label:label(l),row:l};
        if(!(typeof l.id==='number'&&Number.isFinite(l.id)||typeof l.id==='string'&&l.id.length>0&&l.id.length<=180)||rows.filter(function(x){return x&&x.id===l.id;}).length!==1)return {ok:false,reason:'Repeated layer names need a current, unique layer ID.'};
        return {ok:true,selector:l.id,label:label(l),row:l};
    }
    function resolve(ref,rows){
        rows=(rows||[]).filter(function(l){return l&&l.name;});var n=norm(ref);
        var hits=rows.filter(function(l){return l.id===ref;});
        if(!hits.length)hits=rows.filter(function(l){return norm(label(l))===n;});
        if(!hits.length)hits=rows.filter(function(l){return norm(l.name)===n;});
        if(hits.length!==1)return {ok:false,reason:hits.length?'Several layers match; choose the full group and layer.':'No current layer matches.',choices:hits.slice(0,8).map(label)};
        return select(hits[0],rows);
    }
    function scope(text,rows){
        var raw=String(text||''),lm=/\blayer\b\s*[,:]?/i.exec(raw);if(!lm)return null;
        var pre=raw.slice(0,lm.index).trim(),tail=raw.slice(lm.index+lm[0].length),hit=[];
        function escaped(s){return String(s).replace(/[.*+?^${}()|[\]\\]/g,'\\$&').replace(/\s+/g,'\\s+').replace(/\\s\+\/\\s\+/g,'\\s*\\/\\s*');}
        (rows||[]).forEach(function(l){
            if(!l||!l.name||!group(l))return;
            var m=new RegExp('(?:^|\\s)('+escaped(label(l))+')$','i').exec(pre);
            if(m){hit.push({row:l,start:m.index+(m[0].length-m[1].length),tail:tail});return;}
            var named=new RegExp('(?:^|\\s)('+escaped(l.name)+')$','i').exec(pre);
            var grouped=new RegExp('^\\s*(?:in|from|under|within|inside)\\s+(?:the\\s+)?'+escaped(group(l))+'(?:\\s+group)?(?=\\s|[,;:]|$)\\s*[,;:]?\\s*','i').exec(tail);
            if(named&&grouped)hit.push({row:l,start:named.index+(named[0].length-named[1].length),tail:tail.slice(grouped[0].length)});
        });
        if(!hit.length){
            var namedHits=[];
            (rows||[]).forEach(function(l){
                if(!l||!l.name)return;
                var m=new RegExp('(?:^|\\s)('+escaped(l.name)+')$','i').exec(pre);
                if(m)namedHits.push({row:l,start:m.index+(m[0].length-m[1].length)});
            });
            if(namedHits.length>1){
                var width=Math.max.apply(null,namedHits.map(function(h){return pre.length-h.start;}));
                namedHits=namedHits.filter(function(h){return pre.length-h.start===width;});
                if(namedHits.length>1){
                    var chosen=namedHits.map(function(h){return select(h.row,rows||[]);});
                    var usable=chosen.every(function(c){return c.ok;});
                    return {ask:{kind:'ask',layer_target_question:true,
                        text:'This file has '+namedHits.length+' layers named '+namedHits[0].row.name+'. Choose the full group and layer. Nothing has changed.',
                        chips:usable?namedHits.slice(0,5).map(function(h){return (pre.slice(0,h.start)+label(h.row)+' layer '+tail.trim()).trim();}):[]}};
                }
            }
            return null;
        }
        var longest=Math.max.apply(null,hit.map(function(h){return pre.length-h.start;}));hit=hit.filter(function(h){return pre.length-h.start===longest;});
        if(hit.length!==1)return {ask:{kind:'ask',text:'That group contains repeated layer names. Choose one exact layer before editing.',chips:[]}};
        var chosen=select(hit[0].row,rows||[]);if(!chosen.ok)return {ask:{kind:'ask',text:chosen.reason,chips:[]}};
        var head=pre.slice(0,hit[0].start).trim().replace(/(?:^|\s+)(?:(?:in|on|of|inside|within|for)\s+)?(?:the|my|that)$/i,'').trim();
        return {layers:[chosen.selector],word:chosen.label,rest:(head+' '+hit[0].tail).trim()};
    }
    function choose(text,options,rows){
        var n=norm(text).replace(/^(?:i mean\s+|use\s+|choose\s+|pick\s+)?(?:the\s+)?/,'').replace(/\s+(?:one|please)$/,'');
        if(!n||!(options||[]).length)return null;
        var choices=(options||[]).map(function(prompt){
            var s=scope(prompt,rows);if(!s||!s.layers||s.layers.length!==1)return null;
            var r=resolve(s.layers[0],rows);return r.ok?{prompt:prompt,row:r.row}:null;
        });
        if(choices.some(function(c){return !c;}))return null;
        var hits=choices.filter(function(c){
            var l=c.row,role=norm(l.role||'');
            if(n===norm(label(l))||n===norm(group(l)))return true;
            if(/^(?:body|body paint)$/.test(n))return role==='body paint';
            if(/^(?:metallic|metal|red channel|red channel metallic)$/.test(n))return /metallic/.test(role)||/red channel metallic/.test(norm(group(l)));
            if(/^(?:roughness|green channel|green channel roughness)$/.test(n))return /roughness/.test(role)||/green channel roughness/.test(norm(group(l)));
            if(/^(?:clearcoat|clear coat|blue channel|blue channel clearcoat)$/.test(n))return /clearcoat/.test(role)||/blue channel clearcoat/.test(norm(group(l)));
            return false;
        });
        return hits.length===1?hits[0].prompt:null;
    }
    W.SpbLayerTargets={resolve:resolve,select:select,scope:scope,label:label,choose:choose};
})(window);
