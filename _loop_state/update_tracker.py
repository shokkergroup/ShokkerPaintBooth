import json, datetime, os

TRACKER = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum\_loop_state\spec_pattern_rebuild_tracker.json"
BATCH = ['hand_polished','heat_discoloration','heat_distortion','holographic_flake','jeweling_circles','knurl_diamond','knurl_straight','lathe_concentric','lava_crack','magnetic_field','marble_vein','metallic_sand']

with open(TRACKER, 'r', encoding='utf-8') as f:
    t = json.load(f)

# Move from pending to rebuilt
moved = []
for n in BATCH:
    if n in t['pending']:
        t['pending'].remove(n)
        moved.append(n)
    if 'rebuilt' not in t:
        t['rebuilt'] = []
    if n not in t['rebuilt']:
        t['rebuilt'].append(n)

t['pending_count'] = len(t['pending'])
t['rebuilt_count'] = len(t['rebuilt'])

# Append tick log
if 'ticks' not in t:
    t['ticks'] = []
tick_entry = {
    'timestamp': datetime.datetime.now().isoformat(timespec='seconds'),
    'count': len(moved),
    'names': moved,
    'elapsed_ms_min': 4,
    'elapsed_ms_max': 32,
    'elapsed_ms_mean': 18,
    'fails': 0,
    'notes': 'All 12 passed verify (shape, range, time<400ms).',
}
t['ticks'].append(tick_entry)

with open(TRACKER, 'w', encoding='utf-8') as f:
    json.dump(t, f, indent=2)

print('TRACKER updated. pending=', t['pending_count'], 'rebuilt=', t['rebuilt_count'])
print('Moved:', moved)
