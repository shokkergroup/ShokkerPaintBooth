(function(W){
    'use strict';
    var proof=null, recoverySequence=0, recoveryState={state:"not-requested"};
    var HINT_KEY="spb_verified_original_source_hint_v1";
    function identity(){
        var T=W.SPBSourceLoadTransaction;
        try{return T?{path:String(T.getCommittedPath()||''),fingerprint:String(T.getCommittedFingerprint()||''),generation:T.getGeneration()}:null;}catch(e){return null;}
    }
    function pathKey(s){return String(s||'').replace(/\//g,'\\').toLowerCase();}
    function same(a,b){return !!a&&!!b&&pathKey(a.path)===pathKey(b.path)&&a.fingerprint===b.fingerprint;}
    function current(){var now=identity();if(proof&&(!same(proof.bound,now)||proof.bound.generation!==now.generation))proof=null;return now;}
    function sourceVerified(project,status,projectFile){
        recoverySequence++;
        var now=current(), source=String(project&&project.sourcePaintFile||''), expected=project&&project.sourceFingerprint, found=status&&status.current;
        if(!now||!now.path||!now.fingerprint||!source||!status||!status.exists||status.matchesSavedFingerprint!==true||status.legacyUnverified||pathKey(source)!==pathKey(status.requestedPath)||!expected||!found||expected.algorithm!=='sha256'||found.algorithm!=='sha256'||!/^[a-f0-9]{64}$/i.test(found.sha256||'')||expected.sha256!==found.sha256||expected.size!==found.size){proof=null;return false;}
        // The verified original source can differ from its generated flat preview path.
        var active='';try{active=W.getCurrentSourcePaintFile?W.getCurrentSourcePaintFile():'';}catch(e){}
        if(pathKey(active)!==pathKey(source)){proof=null;return false;}
        proof={bound:now,source:{schema:'spb-template-source/1',sha256:found.sha256.toLowerCase(),size:found.size,source_name:basename(source),basis:'Original source bytes verified during successful native project Open',verified_at:new Date().toISOString(),saved_artwork_may_differ:true,uv_geometry_verified:false}};
        if(validProjectFile(projectFile)) {
            var hint={schema:'spb-source-recovery-hint/1',project_file:projectFile,source_path:source,
                committed_path:now.path,sha256:found.sha256.toLowerCase(),size:found.size};
            try { if(W.localStorage) W.localStorage.setItem(HINT_KEY,JSON.stringify(hint)); } catch(e) {}
        }
        recoveryState={state:'verified',basis:proof.source.basis};
        return true;
    }
    function validProjectFile(value){return typeof value==='string'&&value.length>0&&value.length<=180&&/\.spbproj$/i.test(value)&&!/[\\/\u0000-\u001f]/.test(value)&&value.indexOf('..')<0;}
    function recoveryHint(){
        try {
            var h=W.localStorage&&JSON.parse(W.localStorage.getItem(HINT_KEY)||'null');
            return h&&h.schema==='spb-source-recovery-hint/1'&&validProjectFile(h.project_file)&&typeof h.source_path==='string'&&h.source_path.length<=4096&&typeof h.committed_path==='string'&&h.committed_path.length<=4096&&/^[a-f0-9]{64}$/.test(h.sha256||'')&&Number.isSafeInteger(h.size)&&h.size>0?h:null;
        }catch(e){return null;}
    }
    function sourceChanged(){proof=null;recoverySequence++;recoveryState={state:'document-changed'};}
    async function recoverSource(){
        var hint=recoveryHint(),bound=current(),token=++recoverySequence,active='';
        try{active=W.getCurrentSourcePaintFile?W.getCurrentSourcePaintFile():'';}catch(e){}
        if(!hint||!bound||!bound.path||!bound.fingerprint||pathKey(active)!==pathKey(hint.source_path)||pathKey(bound.path)!==pathKey(hint.committed_path)){
            recoveryState={state:'no-matching-hint'};return false;
        }
        recoveryState={state:'checking-original-source'};
        try {
            var verification=Promise.resolve(W.fetch('/api/projects/verify-source',{method:'POST',headers:{'Content-Type':'application/json','X-Shokker-Internal':'1'},body:JSON.stringify({file:hint.project_file})})).then(function(response){return response&&response.ok?response.json():null;});
            var deadline=null,result;
            try {
                result=await (W.setTimeout?Promise.race([verification,new Promise(function(resolve,reject){deadline=W.setTimeout(function(){reject(new Error('Source verification timed out'));},10000);})]):verification);
            } finally { if(deadline!==null&&W.clearTimeout)W.clearTimeout(deadline); }
            var now=identity();
            var sourceNow='';try{sourceNow=W.getCurrentSourcePaintFile?W.getCurrentSourcePaintFile():'';}catch(e){}
            if(token!==recoverySequence||!same(bound,now)||bound.generation!==now.generation||pathKey(sourceNow)!==pathKey(hint.source_path)){
                if(token===recoverySequence)recoveryState={state:'document-changed-during-check'};return false;
            }
            var s=result&&result.sourceStatus,e=s&&s.expected,c=s&&s.current;
            if(!result||result.ok!==true||result.file!==hint.project_file||!s||s.matchesSavedFingerprint!==true||s.legacyUnverified||!s.exists||pathKey(s.requestedPath)!==pathKey(hint.source_path)||!e||!c||e.algorithm!=='sha256'||c.algorithm!=='sha256'||e.sha256!==hint.sha256||c.sha256!==hint.sha256||e.size!==hint.size||c.size!==hint.size){
                proof=null;recoveryState={state:'source-not-verified'};return false;
            }
            if(!sourceVerified({sourcePaintFile:hint.source_path,sourceFingerprint:e},s))return false;
            proof.source.basis='Original source bytes reverified after a committed source reload';
            recoveryState={state:'verified',basis:proof.source.basis};
            try{if(W.spbProAI&&typeof W.spbProAI.refresh==='function')W.spbProAI.refresh();}catch(e){}
            return true;
        }catch(error){if(token===recoverySequence){proof=null;recoveryState={state:'verification-unavailable'};}return false;}
    }
    function captureSession(){current();return proof?JSON.parse(JSON.stringify(proof)):null;}
    function restoreSession(saved){
        proof=null;var now=identity();
        if(saved&&same(saved.bound,now)){proof=JSON.parse(JSON.stringify(saved));proof.bound=now;return true;}
        return false;
    }
    function basename(value){
        var text=String(value||'').trim().replace(/^['"]|['"]$/g,'').replace(/[\\/]+$/,'');
        return text.split(/[\\/]/).pop().replace(/[\u0000-\u001f]/g,'').slice(0,250);
    }
    function read(){
        current();
        function value(id){var el=W.document&&W.document.getElementById(id);return el&&el.value||'';}
        var recognized=null;try{var d=W.SpbProCar&&W.SpbProCar.describe();recognized=d&&d.car||null;}catch(e){}
        return {configured_paint_folder:basename(value('outputDir'))||null,
            source_paint_name:basename(value('paintFile'))||null,
            recognized_layout:recognized,
            identity_basis:proof?proof.source.basis+'; saved artwork and UV geometry may differ.':'Visible iRacing destination and source filename; not a verified template match.',
            current_file_verified:false,
            source_reference:proof?JSON.parse(JSON.stringify(proof.source)):null};
    }
    W.SpbTemplateIdentity={recoverSource:recoverSource,recoveryStatus:function(){return JSON.parse(JSON.stringify(recoveryState));},read:read,basename:basename,sourceVerified:sourceVerified,_sourceChanged:sourceChanged,captureSession:captureSession,restoreSession:restoreSession};
})(window);
