"""Qualify raw legacy read tools in the private/reviewable MCP index."""
def edits(relative):
    if relative != 'mcp/server/index.js':
        return []
    return [
        ("description: MK ? MK.desc(t.name, d0 || '') : d0",
         "description: require('../chatgpt/geometry-authority.cjs').toolDescription(t.name, MK ? MK.desc(t.name, d0 || '') : d0)", 1),
        ("const content = toContent({ result: r.json.result });",
         "// Geometry authority: legacy library coordinates carry no calibrated source receipt.\n  r.json.result = require('../chatgpt/geometry-authority.cjs').qualifyLegacyTool(name, r.json.result);\n  const content = toContent({ result: r.json.result });", 1),
    ]
