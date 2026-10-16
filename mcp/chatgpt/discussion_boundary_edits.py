"""Rebase the MCP classifier from the same function used by local/context reads."""
from pathlib import Path

def classifier_edits(original):
    common = Path(__file__).with_name('design-intent.js').read_text(encoding='utf-8')
    start = original.index('    function classify(text) {')
    end = original.index('    function answer(', start)
    common_start = common.index('    function classify(text) {')
    common_end = common.index('    function discussion(', common_start)
    return [(original[start:end], common[common_start:common_end], 1)]

def index_edits(relative):
    if relative != 'mcp/server/index.js':
        return []
    return [("DESIGN_INTENT = require('./design-intent.cjs');", "DESIGN_INTENT = require('../chatgpt/candidates/design-intent.cjs');", 1)]
