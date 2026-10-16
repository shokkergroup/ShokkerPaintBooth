"""Keep a completed MCP render from covering the customer's chat composer."""


def edits(relative):
    if relative != 'js/spb-pro-ai.js':
        return []
    return [
        ('        var t0 = Date.now(), said = [], st0 = window.showToast, started = false;', '''        var t0 = Date.now(), said = [], st0 = window.showToast, started = false;
        var resultPanelBefore=null,resultPanelWasOpen=false,renderDocumentStamp=null;''', 1),
        ("        function done(r) { if (typeof st0 === 'function') window.showToast = st0; return r; }", '''        function done(r) {
            if (typeof st0 === 'function') window.showToast = st0;
            // This MCP completion already returns its outcome to the chat.
            // Use the normal Close path only for a newly opened results modal
            // in this same paint; preserve an existing manual results view.
            if(!window.SPB_CX3_OFF&&r&&r.ok&&r.result&&r.result.rendered&&!resultPanelWasOpen&&resultPanelBefore&&window.SpbConversationScope&&SpbConversationScope.current(renderDocumentStamp)&&document.getElementById('renderResultsPanel')===resultPanelBefore&&typeof window.closeRenderResults==='function')window.closeRenderResults();
            return r;
        }''', 1),
        ('            try { window.safeDoRender(); } catch (e)', '''            resultPanelBefore=document.getElementById('renderResultsPanel');
            resultPanelWasOpen=!!(resultPanelBefore&&resultPanelBefore.getClientRects().length);
            renderDocumentStamp=window.SpbConversationScope?SpbConversationScope.stamp():null;
            try { window.safeDoRender(); } catch (e)''', 1),
    ]
