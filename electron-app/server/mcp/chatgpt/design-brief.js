(function(W){
    'use strict';
    // A saved discussion is reference evidence. It never restores executable targets,
    // pending approval, masks, queues, tool calls or session Undo identifiers.
    var SCHEMA='spb-design-brief/1', MAX_TURNS=60, MAX_CHARS=24000;
    var state={bound:null,offset:0,prior:null};
    function copy(v){return JSON.parse(JSON.stringify(v));}
    function enabled(){return !W.SPB_DESIGN_BRIEF_OFF;}
    function log(){try{return W.spbProAI&&W.spbProAI.log?W.spbProAI.log():[];}catch(e){return [];}}
    function identity(){
        var tx=W.SPBSourceLoadTransaction;
        try{return tx?{path:String(tx.getCommittedPath()||''),fingerprint:String(tx.getCommittedFingerprint()||''),generation:tx.getGeneration()}:null;}catch(e){return null;}
    }
    function sameFile(a,b){return !!a&&!!b&&a.path===b.path&&a.fingerprint===b.fingerprint;}
    function observe(){
        if(W.SpbConversationScope)W.SpbConversationScope.observe();
        if(!enabled())return;
        var now=identity();
        if(!sameFile(state.bound,now)){state={bound:now,offset:log().length,prior:null};}
    }
    function sourceCommitted(){
        // Track document changes even while disabled, so re-enabling cannot revive stale notes.
        var now=identity();
        if(!sameFile(state.bound,now)||!state.bound||state.bound.generation!==now.generation)state={bound:now,offset:log().length,prior:null};
    }
    function cleanTurn(row,fromLog){
        if(!row||!['user','ai','assistant'].includes(row.role))return null;
        var text=typeof row.text==='string'?row.text.trim():'';
        var options=fromLog===true&&Array.isArray(row.options)?row.options.slice(0,6).filter(Boolean).map(function(o,i){return 'Proposal '+(i+1)+': '+String(o.label||o.name||o.title||'').slice(0,200)+(o.description?' — '+String(o.description).slice(0,600):'');}).filter(function(s){return !/: $/.test(s);}):[];
        if(options.length)text+='\n'+options.join('\n');
        if(!text)return null;
        var cleaned={role:row.role==='user'?'user':'assistant',text:text.slice(0,4000),truncated:row.truncated===true||text.length>4000};
        // Proposal descriptions are historical evidence, never restored live picks.
        var proposal=W.SpbDesignIntent&&row.role!=='user'?W.SpbDesignIntent.discussion({answer:{design_proposals:row.design_proposals}}):null;
        if(proposal)cleaned.design_proposals=proposal;
        return cleaned;
    }
    function bounded(rows,budget){
        var valid=rows.map(cleanTurn).filter(Boolean),omitted=0;
        if(valid.length>MAX_TURNS){omitted=valid.length-MAX_TURNS;valid=valid.slice(0,10).concat(valid.slice(-(MAX_TURNS-10)));}
        var used=0,indices=[];
        function size(row){return row.text.length+(row.design_proposals?JSON.stringify(row.design_proposals).length:0);}
        valid.slice(0,2).forEach(function(row,i){if(used+size(row)<=budget/3){indices.push(i);used+=size(row);}});
        for(var i=valid.length-1;i>=0;i--){if(indices.includes(i))continue;if(used+size(valid[i])>budget)continue;indices.push(i);used+=size(valid[i]);}
        omitted+=valid.length-indices.length;
        var kept=indices.sort(function(a,b){return a-b;}).map(function(i){return valid[i];});
        return {turns:kept,omitted_turns:omitted,contains_truncated_turns:kept.some(function(r){return r.truncated;})};
    }
    function capture(projectId){
        if(!enabled())return null;
        observe();
        if(!state.bound||!state.bound.path||typeof projectId!=='string'||!projectId)return null;
        var fresh=log().slice(state.offset),firstUser=fresh.findIndex(function(r){return r&&r.role==='user';});
        // A delayed answer from the previous document cannot begin a new brief.
        fresh=firstUser<0?[]:fresh.slice(firstUser).map(function(row){return cleanTurn(row,true);}).filter(Boolean);
        var result=bounded((state.prior&&state.prior.turns||[]).concat(fresh),MAX_CHARS);
        if(!result.turns.length)return null;
        return {schema:SCHEMA,project_id:projectId,saved_at:new Date().toISOString(),turns:result.turns,
            omitted_turns:result.omitted_turns+(state.prior&&state.prior.omitted_turns||0),contains_truncated_turns:result.contains_truncated_turns,
            authority:'Historical discussion only. Customer quotes and assistant proposals are separate. Revalidate current scope and ask for any missing choice; this is not approval to execute.'};
    }
    function restore(brief,projectId,sourceVerified){
        // Called only after the existing project source/layer/config transaction commits.
        state={bound:identity(),offset:log().length,prior:null};
        if(!enabled()||!sourceVerified||!brief||brief.schema!==SCHEMA||brief.project_id!==projectId||!Array.isArray(brief.turns)||brief.turns.length>MAX_TURNS)return false;
        var clean=bounded(brief.turns,MAX_CHARS);
        if(!clean.turns.length)return false;
        state.prior={schema:SCHEMA,project_id:projectId,turns:clean.turns,
            omitted_turns:clean.omitted_turns+Math.max(0,Math.min(100000,Number(brief.omitted_turns)||0)),contains_truncated_turns:clean.contains_truncated_turns};
        return true;
    }
    function view(){
        if(!enabled())return {available:false,reason:'Saved discussion is disabled.'};
        observe();
        if(!state.prior)return {available:false,reason:'No saved design discussion is attached to this project.'};
        var small=bounded(state.prior.turns,8000);
        return {available:true,schema:SCHEMA,project_id:state.prior.project_id,historical:true,turns:small.turns,
            omitted_turns:small.omitted_turns+state.prior.omitted_turns,
            guidance:'Saved project discussion; not live SpbConvo targets, pending approval or Undo. Read exact buyer quotes and separate proposals. Recheck live paint and ask if a choice is missing.'};
    }
    function recall(text){
        if(!enabled()||!(/\b(?:what|remind|recap|summari[sz]e|remember|show)\b/i.test(text)&&/\b(?:brief|discussed|agree(?:d)?|decided|design discussion|design choices|saved discussion|previous design)\b/i.test(text)))return null;
        var saved=view();
        if(!saved.available)return {text:'There is no saved design discussion attached to this project yet. Save a project after discussing your design to keep those notes with it.'};
        var customer=saved.turns.filter(function(r){return r.role==='user';}),proposals=saved.turns.filter(function(r){return r.role==='assistant';});
        function quote(r,max){return r.text.length>max?r.text.slice(0,max)+' [excerpt]':r.text;}
        var chosen=Array.from(new Set(customer.slice(0,2).concat(customer.length>2?customer.slice(-2):[])));
        var pieces=chosen.map(function(r){return 'You said: '+quote(r,650);});
        if(proposals.length)pieces.push('Last saved assistant proposal (not approval): '+quote(proposals[proposals.length-1],1200));
        var design=proposals.slice().reverse().find(function(r){return r.design_proposals;});
        if(design){
            pieces.push('Saved design directions (not approval):\n'+design.design_proposals.items.map(function(item,i){return (i+1)+'. '+item.title+' — '+item.description;}).join('\n'));
            if(design.design_proposals.constraints.no_glitter)pieces.push('Saved constraint: no glitter.');
            if(design.design_proposals.constraints.protected_artwork.length)pieces.push('Keep unchanged: '+design.design_proposals.constraints.protected_artwork.join(', ')+'.');
        }
        return {text:pieces.join('\n\n')+(saved.omitted_turns?'\nSome older discussion is omitted.':'')+'\nThese are saved quotes. I have not changed the paint or assumed that a proposal was approved.'};
    }
    function captureSession(){observe();var saved=copy(state);saved.prior=capture(state.prior&&state.prior.project_id||'session-discussion');return saved;}
    function explain(text){
        if(!W.SpbDesignIntent||! /\b(first|second|third|last)\b/i.test(String(text||'')))return null;
        var saved=view();if(!saved.available)return null;
        var turn=saved.turns.slice().reverse().find(function(r){return r.role==='assistant'&&r.design_proposals;});
        if(!turn)return null;
        var answer=W.SpbDesignIntent.answer(text,{answer:{design_proposals:turn.design_proposals}});
        // Only a resolved explanation can use historical options. A new proposal
        // or any edit request must take its usual current-document route.
        if(!answer||!/^Option \d+ — /.test(answer.answer.text))return null;
        answer.answer.text='From your saved discussion (a proposal, not an approved edit):\n\n'+answer.answer.text;
        answer.answer.summary=answer.answer.text;
        delete answer.answer.design_proposals;
        return answer;
    }
    function restoreSession(saved){if(saved&&typeof saved.offset==='number'){state=copy(saved);state.bound=identity();state.offset=log().length;}}
    function forget(){state={bound:identity(),offset:log().length,prior:null};}
    W.SpbDesignBrief={observe:observe,sourceCommitted:sourceCommitted,capture:capture,restore:restore,view:view,recall:recall,explain:explain,captureSession:captureSession,restoreSession:restoreSession,forget:forget};
    observe();
})(window);
