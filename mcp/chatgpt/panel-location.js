/* Explain stored panel locations without guessing UVs or starting recognition. */
(function(W){
    'use strict';
    function requested(q) {
        if (/\b(?:kit|tool|button|menu|setting|control|layer)s?\b/i.test(q)) return null;
        if (!/^(?:where\s+(?:(?:exactly\s+)?(?:is|are)\b|exactly\b)|which\b.{0,35}\b(?:area|island|part|region)\b|(?:what|give me)\b.{0,30}\b(?:coordinates|bounds|bounding box)\b)/i.test(q)) return null;
        if (/(?:[.!?;]\s*|\b(?:and|then)\s+)(?:please\s+)?(?:make|set|apply|assign|change|remove|clear|turn|hide|show|paint|delete|undo|redo|run|scan|fix|enable|disable|render|export|place|add|move|resize)\b/i.test(q)) return null;
        var hits = q.toLowerCase().match(/\b(?:(?:left|right|front|rear)\s+)?(?:doors?|hood|bonnet|roof|trunk|deck|bed|tailgate|bumpers?|fenders?|quarter panels?|sides?|spoiler|wing)\b/g);
        if (!hits) return null;
        return Array.from(new Set(hits.map(function(hit){return hit.replace(/\bbonnet\b/,'hood').replace(/\b(door|bumper|fender|side)s\b/,'$1');})));
    }
    function read() {
        try { return W.SpbProCar && typeof W.SpbProCar.readCurrentGeometry === 'function' ? W.SpbProCar.readCurrentGeometry() : {status:'unavailable',parts:[],read_only:true}; }
        catch (_) { return {status:'unreadable',parts:[],read_only:true}; }
    }
    function explain(name,g) {
        var matches=(g.status==='current' && Array.isArray(g.parts) ? g.parts : []).filter(function(p){return p.name.toLowerCase()===name;});
        // Multiple pieces sharing a name cannot be collapsed into one paint box.
        var seen={}; matches=matches.filter(function(p){var k=JSON.stringify(p.bbox);if(seen[k])return false;seen[k]=true;return true;});
        var body;
        if (matches.length===1) {
            var p=matches[0],b=p.bbox;
            body='The current car map stores '+name+' at '+Math.round(b[0]*100)+'–'+Math.round(b[2]*100)+'% across and '+Math.round(b[1]*100)+'–'+Math.round(b[3]*100)+'% down the sheet, measured from its top-left corner ('+p.evidence+'). This is the stored rectangular extent, not the exact paintable outline or proof of orientation. Inspect the part overlay before painting.';
        } else {
            body=matches.length>1 ? 'The current map has several separate areas labelled '+name+'; a single box would be misleading.' : 'I cannot identify an exact '+name+' location from the current stored map.';
            if (g.status==='named-reference') body='The car named in your question is a reference; its name alone does not verify the loaded paint or its '+name+' location. Ask about the current sheet after confirming the correct file.';
            if (g.status==='stale' || g.status==='loading') body+=' The map is stale or this paint is still loading.';
            var options=(g.status==='current' ? g.parts : []).filter(function(p){return name==='door' ? /^(left|right) door$/i.test(p.name) : false;}).map(function(p){return p.name;});
            options=Array.from(new Set(options));
            if(options.length) body+=' The map names '+options.join(' and ')+'. Ask for one of those exact parts.';
            else body+=' Open the Car parts view in Chat and inspect the highlighted areas, or use the template guides to identify the part.'+( /\bdoor\b/.test(name) ? ' A whole side-panel box is not an exact door box.' : '');
            body+=' A typical stock-car layout or catalog match cannot establish where this panel is on your file.';
        }
        return body;
    }
    function answer(q) {
        if (W.SPB_CX3_OFF || W.SPB_CARKB_OFF) return null;
        var names=requested(String(q||'').trim()); if (!names) return null;
        var named=W.SpbCarReferenceAnswer && W.SpbCarReferenceAnswer.namesCar && W.SpbCarReferenceAnswer.namesCar(q);
        var g=named ? {status:'named-reference',parts:[]} : read();
        var body=names.length>4 ? 'Please ask for up to four named parts at a time so each location can be checked separately.' : names.map(function(name){return explain(name,g);}).join('\n\n');
        body+=' No map was built and no paint was changed.';
        return {cls:'ANSWER',hits:[],answer:{id:'assistant.live_editor_capabilities',live_context:true,editor_topic:null,title:'Locate panels on this template',text:body,summary:body,actions:[],how:[],related:[]}};
    }
    W.SpbPanelLocation={answer:answer,read:read,requested:requested};
})(window);
