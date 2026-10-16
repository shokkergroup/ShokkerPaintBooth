"""Pass an optional read-only buyer query to current page material evidence."""


def edits(source):
    if source != 'js/spb-pro-ai.js':
        return []
    return [
        ('    function state() {', '''    function state() {
        var editorQuery=typeof arguments[0]==='string'&&arguments[0].length<=1000?arguments[0]:'';''', 1),
        ('SpbEditorCapabilities.read() : undefined', 'SpbEditorCapabilities.read(editorQuery) : undefined', 1),
        ("parameters: { type: 'object', properties: {} }, handler: function () { var s = state();",
         "parameters: { type: 'object', properties: {editor_query:{type:'string',maxLength:1000,description:'Optional buyer question for focused current layer-material evidence; read-only.'}} }, handler: function (a) { var s = state(a && a.editor_query);", 1),
    ]
