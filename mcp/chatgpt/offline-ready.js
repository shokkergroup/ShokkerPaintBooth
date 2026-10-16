(function(W){
    'use strict';
    // First-message readiness is separate from the editor's intent/action code.
    // Return a promise only while the local knowledge index is still loading.
    function wait(knowledge,timeoutMs,topicReady){
        if(!knowledge||!knowledge.load||!knowledge.ready)return null;
        function ready(){return knowledge.ready() && (!topicReady || !!topicReady());}
        if(ready())return null;
        var refresh = !!topicReady && knowledge.ready();
        return new Promise(function(resolve,reject){
            var done=false,timer=setTimeout(function(){if(!done){done=true;reject(new Error('The local help reference is still loading. Please send your question again.'));}},timeoutMs||10000);
            Promise.resolve().then(function(){return knowledge.load(undefined,{refresh:refresh});}).then(function(){
                if(done)return;done=true;clearTimeout(timer);
                if(ready())resolve();else reject(new Error('The local help reference could not load. Please send your question again.'));
            },function(){if(done)return;done=true;clearTimeout(timer);reject(new Error('The local help reference could not load. Please send your question again.'));});
        });
    }
    W.SpbOfflineReady={wait:wait};
})(window);
