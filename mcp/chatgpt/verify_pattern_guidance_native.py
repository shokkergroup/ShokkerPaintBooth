"""Read-only comparison of the captured Offline pattern conversation."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[2]
evidence = root / '_codex_mcp_work/chatgpt-dev/59910'
before_file = 'offline-pattern-before-2026-10-10T18-10-00-244Z.json'
after_file = 'offline-pattern-final-after-2026-10-10T18-20-00-184Z.json'
before = json.loads((evidence / before_file).read_text(encoding='utf-8'))['state']
after = json.loads((evidence / after_file).read_text(encoding='utf-8'))['state']
chat = (evidence / 'offline-pattern-settings-chat.txt').read_text(encoding='utf-8')
a = np.asarray(Image.open(evidence / 'offline-pattern-before.png').convert('RGBA'))
b = np.asarray(Image.open(evidence / 'offline-pattern-final-preview.png').convert('RGBA'))
checks = {
    'layer_summaries_exact': before['layers'] == after['layers'],
    'zone_summaries_exact': before['zones'] == after['zones'],
    'exposed_primary_pattern_controls_exact': before['editor_capabilities']['pattern_controls'] == after['editor_capabilities']['pattern_controls'],
    'preview_every_rgba_channel_exact': a.shape == b.shape and bool(np.array_equal(a, b)),
    'friendly_pattern_name': 'Pattern: Diner Checkerboard.' in chat,
    'exact_scale': 'Pattern scale: 0.6.' in chat,
    'exact_settings': all(x in chat for x in ['Pattern rotation: 0 degrees.', 'Pattern opacity: 100%.', 'Pattern paint strength multiplier: 1.', 'Pattern spec amount: 0%.']),
    'body_restriction_reported': 'Stored layer restriction: Body.' in chat,
    'visual_assessment_limit': 'these settings alone are not a visual assessment' in chat,
    'coarser_tradeoff': 'Coarser makes the marks larger.' in chat and 'compete with the number' in chat,
    'selection_change_clarified': 'The selected zone changed since that answer.' in chat and 'Zone 1 which has no primary pattern.' in chat,
    'repeated_stale_followup_clarified': 'Choose a zone with the pattern you mean' in chat,
    'unrelated_racewear_absent': 'RaceWear' not in chat,
}
assert all(checks.values()), checks
receipt = {
    'pass': True, 'port': 59910, 'checks': checks,
    'before': before_file, 'after': after_file,
    'preview_size': [int(a.shape[1]), int(a.shape[0])],
    'layers': len(after['layers']), 'zones': len(after['zones']),
    'negative_baseline': 'offline-pattern-stale-selection-baseline.txt',
    'conversation': 'offline-pattern-settings-chat.txt',
    'screenshots': ['offline-pattern-clarification-chat.png', 'offline-pattern-settings-chat.png'],
    'limits': 'Native Offline guidance plus captured MCP state only. No model invocation, project save or intentional paint mutation. Summary records and exposed primary settings are not a full raster/project audit. Numeric scale is not calibrated physical geometry or universal pixel size. Advice-to-edit continuity, actual Claude parity and shared runtime adoption remain open.',
}
(evidence / 'offline-pattern-guidance-native-acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'pass': True, 'checks': len(checks), 'preview_size': receipt['preview_size'], 'layers': receipt['layers'], 'zones': receipt['zones']}))
