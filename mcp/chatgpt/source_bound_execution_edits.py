"""Carry read-time source identity into existing page executor guards."""
def edits(relative):
    if relative == 'js/spb-pro-ai.js':
        return [
            ('handler: function () { var s = state(); s.pending_changes = pendingText(queue); return s; }',
             """handler: function () { var s = state();
                s.execution_source = mcpCaptureContext(false);
                s.execution_source.documentScope = window.SpbAiConnect && window.SpbAiConnect.documentScope ? window.SpbAiConnect.documentScope() : '';
                s.pending_changes = pendingText(queue); return s; }""", 1),
            ('    function mcpCall(tool, args) {',
             """    function mcpCall(tool, args) {
        // Bind this edit to the source used by its broker preflight, before any lease/history mutation.
        if (args && Object.prototype.hasOwnProperty.call(args, '_spb_expected_source')) {
            var expected = args._spb_expected_source;
            var currentScope = window.SpbAiConnect && window.SpbAiConnect.documentScope ? window.SpbAiConnect.documentScope() : '';
            if (!expected || !expected.documentScope || expected.documentScope !== currentScope)
                return Promise.resolve({ok:false,error:'The open paint changed since this request was prepared; no changes were applied.'});
            var wrongSource = mcpStaleResult(expected, false);
            if (wrongSource) return Promise.resolve(wrongSource);
            args = Object.assign({}, args); delete args._spb_expected_source;
        }""", 1),
        ]
    if relative == 'mcp/server/index.js':
        return [
            ("const b = await httpJson('POST', '/api/mcp/call', { tool: 'do', args: { frame: { v: 1, act: 'change', ops: [{ verb: 'recolour', target: { kind: 'body' }, look: { colour: { hex: args.palette.base } } }], decals: 'protect' }, text: String(args.buyer_said), confirm: true }, timeout: timeoutFor('do') }, (timeoutFor('do') + 15) * 1000);",
             "const b = await bridgeCall('do', { frame: { v: 1, act: 'change', ops: [{ verb: 'recolour', target: { kind: 'body' }, look: { colour: { hex: args.palette.base } } }], decals: 'protect' }, text: String(args.buyer_said), confirm: true, _spb_expected_source: args._spb_expected_source }, timeoutFor('do'));", 1),
            ("  return require('../chatgpt/named-part-guard.cjs').refusal(app, args, () =>\n    httpJson('POST', '/api/mcp/call', { tool: 'get_state', args: {}, timeout: 30 }, 45000));",
             """  const prepared = await require('../chatgpt/source-bound-execution.cjs').prepare(app, args || {}, () =>
    httpJson('POST', '/api/mcp/call', { tool: 'get_state', args: {}, timeout: 30 }, 45000));
  if (prepared.blocked) return prepared.blocked;
  if (args) args._spb_expected_source = prepared.args._spb_expected_source;
  return null;""", 1),
            ("  if (WRITE_APPS.indexOf(app) !== -1 || app === 'kit') {\n    const blocked = await unknownPartRefusal(app, args || {});\n    if (blocked) return { status: 200, json: { ok: true, result: blocked } };\n  }",
             """  if (WRITE_APPS.indexOf(app) !== -1 || app === 'edit_layer' || app === 'undo' ||
      (app === 'kit' && !/^(?:check|propose)$/i.test(String((args || {}).action || 'place')))) {
    const prepared = await require('../chatgpt/source-bound-execution.cjs').prepare(app, args || {}, () =>
      httpJson('POST', '/api/mcp/call', { tool: 'get_state', args: {}, timeout: 30 }, 45000));
    if (prepared.blocked) return {status:200,json:{ok:true,result:prepared.blocked}};
    args = prepared.args;
  }""", 1),
            ("bridgeCall('undo', { steps: nW }, timeoutFor('undo'))",
             "bridgeCall('undo', { steps: nW, _spb_expected_source: gx.args._spb_expected_source }, timeoutFor('undo'))", 1),
            ("bridgeCall('undo', { steps: run.restore.nW }, timeoutFor('undo'))",
             "bridgeCall('undo', { steps: run.restore.nW, _spb_expected_source: run.restore.args._spb_expected_source }, timeoutFor('undo'))", 1),
        ]
    return []
