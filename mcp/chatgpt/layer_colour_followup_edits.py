"""Keep completed native colour edits available to exact layer refinements."""
def edits(relative):
    if relative == 'js/spb-offline-builder.js':
        return [("['rel', 'soft', 'strong', 'shade', 'keep', 'pop', 'recipe', 'sub', 'exclude', 'scaleMul', 'shadeDir', 'strengthMul'].forEach",
                 "['_nativeColourRefinement', 'rel', 'soft', 'strong', 'shade', 'keep', 'pop', 'recipe', 'sub', 'exclude', 'scaleMul', 'shadeDir', 'strengthMul'].forEach",1)]
    if relative == 'js/spb-pro-edit.js':
        return [
            ('    function plan(text, env) {', '''    function plan(text, env) {
        if (!window.SPB_CX3_OFF && window.SpbLayerColourFollowup) {
            var nativeFollowup = window.SpbLayerColourFollowup.plan(text, env);
            if (nativeFollowup) return nativeFollowup;
        }''', 1),
            ('window.SpbProEdit = { lookSource:', 'window.SpbProEdit = { shadeColour: shadeHex, lookSource:', 1)]
    if relative == 'js/spb-pro-ai.js':
        return [(f"offline:true,text:{name}.text,queue:{name}.queue,usage:{{cost:0}}",
                 f"offline:true,text:{name}.text,queue:{name}.queue,editPlan:ed,editCtx:window.SpbLayerColourFollowup?SpbLayerColourFollowup.context(ed,{name}.queue):window.SpbProEdit.ctxOf(ed),usage:{{cost:0}}",1)
                for name in ('nativeColour', 'nativeBuilder', 'nativeFrame')]
    return []
