"""Private SPB-93 proposal: explicit live layer eyes override imported hiding.

Import records effective visibility on each leaf. Native group/solo/individual
controls and their Undo change those leaf flags. An immutable imported parent
must not permanently veto a formerly hidden leaf that the user has now shown.
"""


def candidate(source):
    marker = '    function composeLayerStack(ctx, layers, options) {'
    helper = '''    function hasShownImportedChild(node) {
        if (node.type === 'layer') {
            return node.layer.visible === true && node.layer.importVisible === false && !!node.layer.img;
        }
        return node.children.some(hasShownImportedChild);
    }

'''
    gate = '                if (group.visible === false || group.ownVisible === false) return;'
    fixed = '''                // SPB-93 private59910: native show/Undo owns live leaf visibility.
                // Preserve hidden siblings and group opacity/blend; never mutate import metadata.
                if ((group.visible === false || group.ownVisible === false) && !hasShownImportedChild(node)) return;'''
    if source.count(marker) != 1 or source.count(gate) != 1:
        raise ValueError('Group compositor changed; review before refreshing this candidate')
    return source.replace(marker, helper + marker, 1).replace(gate, fixed, 1)


if __name__ == '__main__':
    from pathlib import Path
    import hashlib
    import json
    root = Path(__file__).resolve().parents[2]
    original = root / 'js/canvas/layer/clipping-mask.js'
    result = candidate(original.read_text(encoding='utf-8'))
    output = Path(__file__).parent / 'candidates/clipping-mask.js'
    output.write_text(result, encoding='utf-8')
    manifest = {'source': str(original.relative_to(root)),
                'source_sha256': hashlib.sha256(original.read_bytes()).hexdigest(),
                'candidate_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))
