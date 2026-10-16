"""Exact common Offline/MCP entry points for non-mutating raw-layer inspection."""

ENV = "{layers:(typeof _psdLayers !== 'undefined' ? _psdLayers : []),busy:!!((typeof isDrawing !== 'undefined' && isDrawing)||(typeof _activeLayerCanvas !== 'undefined' && _activeLayerCanvas)||(typeof freeTransformState !== 'undefined' && freeTransformState && freeTransformState.active))}"


def edits(relative, original=''):
    if relative == 'mcp/server/index.js':
        adopted = 'let NATIVE_LAYER_COLOUR = null' in original
        before = 'return NATIVE_LAYER_COLOUR ? out.map(NATIVE_LAYER_COLOUR.tool).map(PRIVATE_LAYER_COLOUR.tool) : out;' if adopted else 'return out.map(NATIVE_LAYER_COLOUR.tool);'
        after = 'return NATIVE_LAYER_COLOUR ? out.concat([PRIVATE_LAYER_COLOUR.INSPECT_TOOL]).map(NATIVE_LAYER_COLOUR.tool).map(PRIVATE_LAYER_COLOUR.tool) : out;' if adopted else 'return out.concat([NATIVE_LAYER_COLOUR.INSPECT_TOOL]).map(NATIVE_LAYER_COLOUR.tool);'
        return [
            ("const READ_ONLY = new Set(['spb_car_knowledge'", "const READ_ONLY = new Set(['spb_inspect_layer', 'spb_car_knowledge'", 1),
            ("  spb_status: 'status',", "  spb_inspect_layer: 'inspect_layer', spb_status: 'status',", 1),
            (before, after, 1),
            ('Read colour_overlay in current STATE.', 'Read colour_overlay in current STATE. Before recolouring an unfamiliar layer, use spb_inspect_layer: empty pixels cannot produce a visible recolour, and a full opaque multi-colour layout needs region choices rather than a solid overlay if its design is to survive.', 1),
        ]
    if relative == 'js/spb-pro-ai.js':
        return [
            ('/^(?:status|get_state|zones|list_tools|', '/^(?:inspect_layer|status|get_state|zones|list_tools|', 1),
            ("        if (tool === 'status') return mcpStatus(mcpContext);", """        if (tool === 'inspect_layer') {
            var pixelRead = window.SpbNativeLayerColour ? SpbNativeLayerColour.inspect(args.layer, """ + ENV + """, args.image !== false) : {error:'Layer inspection is not ready.'};
            var pixelImages = pixelRead.images || []; delete pixelRead.images;
            return Promise.resolve({ok:!pixelRead.error,error:pixelRead.error,result:pixelRead,images:pixelImages});
        }
        if (tool === 'status') return mcpStatus(mcpContext);""", 1),
            ('        if (inventoryRead) designAdvice = inventoryRead;', """        var pixelRead = !_busy && !(window.SpbAiConnect && SpbAiConnect.relaying()) && adviceBuilder && adviceBuilder.offlineMode() && window.SpbNativeLayerColour && SpbNativeLayerColour.offlineInspection(text, """ + ENV + """);
        if (pixelRead) inventoryRead = pixelRead;
        if (inventoryRead) designAdvice = inventoryRead;""", 1),
            ("inventoryRead ? 'The Loaded layers card below lists the current groups and name examples. Nothing has been changed or queued.'", "inventoryRead ? (pixelRead ? 'The Layer pixels card below reports the current layer raster. Nothing has been changed or queued.' : 'The Loaded layers card below lists the current groups and name examples. Nothing has been changed or queued.')", 1),
        ]
    if relative in ('js/spb-offline-builder.js', 'js/spb-pbn.js', 'js/spb-offline-answer.js'):
        needle = "readAns3.id === 'assistant.template_layers'" if relative.endswith('spb-pbn.js') else "r.answer.id === 'assistant.template_layers'" if relative.endswith('spb-offline-builder.js') else "A.id === 'assistant.template_layers'"
        return [(needle, '(' + needle + ' || ' + needle.replace('assistant.template_layers', 'assistant.layer_pixels') + ')', 1)]
    return []
