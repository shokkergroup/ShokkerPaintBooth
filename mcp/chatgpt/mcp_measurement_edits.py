"""Keep the executed native colour scope when the customer rechecks a result."""
def edits():
    return [
        ('        var hc = host && host.ctx ? host.ctx(E) : {}, ctx0 =', '''        // Scope evidence only, not an executable/replay queue. Copy scalar fields.
        E._nativeColourMeasureQueue = flat && flat.length && flat.every(function (op) { return op.kind === 'layer' && op.colour != null; }) ? flat.map(function (op) { return {kind:'layer',layer:op.layer,colour:op.colour,sourceColour:op.sourceColour}; }) : null;
        E._nativeColourMeasureText = E._nativeColourMeasureQueue ? String(text || '') : '';
        var hc = host && host.ctx ? host.ctx(E) : {}, ctx0 =''', 1),
        ("text = s8.text || '', p = Promise.resolve(null)", "text = s8.text || E._nativeColourMeasureText || '', p = Promise.resolve(null)", 1),
        ("{ queue: [], offline: false }, ctx0)", "{ queue: E._nativeColourMeasureQueue || [], offline: false }, ctx0)", 1),
    ]
