"""Fresh confirmed-target preflight; shared sources remain read-only."""
def edits(relative, text):
    if relative != 'mcp/server/index.js':
        return []
    start=text.index('// unknown part: the buyer names a part this template has no map for')
    end=text.index('async function chatTool(',start)
    return [
        ("description: require('../chatgpt/geometry-authority.cjs').toolDescription(t.name, MK ? MK.desc(t.name, d0 || '') : d0)",
         "description: require('../chatgpt/named-part-guard.cjs').toolDescription(t.name, require('../chatgpt/geometry-authority.cjs').toolDescription(t.name, MK ? MK.desc(t.name, d0 || '') : d0))", 1),
        ("async function bridgeCall(app, args, secs) { return httpJson('POST', '/api/mcp/call', { tool: app, args: args || {}, timeout: secs || 60 }, ((secs || 60) + 15) * 1000); }",
         """async function bridgeCall(app, args, secs) {
  if (WRITE_APPS.indexOf(app) !== -1 || app === 'kit') {
    const blocked = await unknownPartRefusal(app, args || {});
    if (blocked) return { status: 200, json: { ok: true, result: blocked } };
  }
  return httpJson('POST', '/api/mcp/call', { tool: app, args: args || {}, timeout: secs || 60 }, ((secs || 60) + 15) * 1000);
}""", 1),
        (text[start:end], """// Named targets require fresh current-source confirmation. No cache or fail-open fallback.
async function unknownPartRefusal(app, args) {
  return require('../chatgpt/named-part-guard.cjs').refusal(app, args, () =>
    httpJson('POST', '/api/mcp/call', { tool: 'get_state', args: {}, timeout: 30 }, 45000));
}
""", 1),
        ("  if (WRITE_APPS.indexOf(app) !== -1) { const refusal = await unknownPartRefusal(app, args || {}); if (refusal) return { content: [{ type: 'text', text: JSON.stringify(refusal) }] }; }\n", '', 1),
        ('  let baseFirst = null;', "  if (WRITE_APPS.indexOf(app) !== -1) { const refusal = await unknownPartRefusal(app, args || {}); if (refusal) return { content: [{ type: 'text', text: JSON.stringify(refusal) }] }; }\n  let baseFirst = null;", 1),
        ("try { r = await httpJson('POST', '/api/mcp/call', { tool: app, args: args || {}, timeout: timeoutFor(app) }, (timeoutFor(app) + 15) * 1000); }",
         "try { r = await bridgeCall(app, args || {}, timeoutFor(app)); }", 1),
        ("await httpJson('POST', '/api/mcp/call', { tool: 'add_graphic', args: checkerSecond(args, chk2), timeout: timeoutFor('add_graphic') }, (timeoutFor('add_graphic') + 15) * 1000)",
         "await bridgeCall('add_graphic', checkerSecond(args, chk2), timeoutFor('add_graphic'))", 1),
        ("async function oaiUndo(args) {\n  DIRTY = true;\n  const steps = Math.max(1, Math.min(30, Math.round(Number(args && args.steps) || 1))); let pending = 0, k = steps, last = null; const notes = [];",
         """async function oaiUndo(args) {
  const steps = Math.max(1, Math.min(30, Math.round(Number(args && args.steps) || 1)));
  // Check every possible graphic restore BEFORE changing history or undoing pixels.
  for (const e of HIST.slice(-steps)) if (e && e.restore) {
    const blocked = await unknownPartRefusal('add_graphic', e.restore.args || {});
    if (blocked) return {content:[{type:'text',text:JSON.stringify(blocked)}]};
  }
  DIRTY = true;
  let pending = 0, k = steps, last = null; const notes = [];""", 1),
        ("  const stop = (rule) => ({ content: [{ type: 'text', text: JSON.stringify({ changed: false, tweaked_zone: z.name, rule }) }] });",
         """  const stop = (rule) => ({ content: [{ type: 'text', text: JSON.stringify({ changed: false, tweaked_zone: z.name, rule }) }] });
  // A refusal must precede the undo used to re-draw a graphic.
  const blocked = await unknownPartRefusal('add_graphic', gx.args || {});
  if (blocked) return {content:[{type:'text',text:JSON.stringify(blocked)}]};""", 1),
    ]
