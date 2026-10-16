"""Review-only OA2 proposal: route kit Undo through existing busy/lease guards.

Not part of the candidate build while Claude owns the active kit lane.
"""

def patch(source):
    changes = [
        ("        if (act === 'undo') return kitUndo();\n        if (!kind)",
         "        if (!kind && act !== 'undo')"),
        ("var read = (kind === 'spec' && (act === 'check' || act === 'propose' || act === 'list'));",
         "var read = (act !== 'undo' && kind === 'spec' && (act === 'check' || act === 'propose' || act === 'list'));"),
        ("        BUSY = true;\n        try {\n            if (kind === 'sponsor')",
         "        BUSY = true;\n        try {\n            // Undo is an edit: obey the same busy and ownership guards.\n            if (act === 'undo') return kitUndo();\n            if (kind === 'sponsor')"),
    ]
    for before, after in changes:
        if source.count(before) != 1:
            raise ValueError('Kit Undo source changed; review exact anchor: ' + before[:70])
        source = source.replace(before, after, 1)
    return source

if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.stdout.write(patch(Path(sys.argv[1]).read_text(encoding='utf-8')))
