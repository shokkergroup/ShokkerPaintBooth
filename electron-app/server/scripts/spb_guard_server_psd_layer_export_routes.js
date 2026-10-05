#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf8');

const server = read('server.py');
const route = read('server_routes/psd_layer_export_routes.py');
const manifest = JSON.parse(read('scripts/runtime-sync-manifest.json'));
const contextTargets = JSON.parse(read('scripts/spb_context_targets.json'));

const failures = [];
const assert = (condition, message) => {
  if (!condition) failures.push(message);
};

assert(!server.includes('def export_psd_layers('), 'server.py still owns export_psd_layers');
assert(
  server.includes('from server_routes.psd_layer_export_routes import register_psd_layer_export_routes'),
  'server.py missing PSD layer export import'
);
assert(
  server.includes('register_psd_layer_export_routes('),
  'server.py missing PSD layer export registration'
);
[
  'output_folder_getter=lambda: OUTPUT_FOLDER',
  'apply_paint_recolor=lambda',
  'decode_rle_mask_payload=lambda',
  'decode_source_layer_rgb_payload=lambda',
  "build_multi_zone=lambda *args, **kwargs: __import__('shokker_engine_v2').build_multi_zone",
].forEach((needle) => assert(server.includes(needle), `server bridge missing ${needle}`));

[
  'def register_psd_layer_export_routes(',
  "@app.route('/export-psd-layers', methods=['POST'])",
  'def export_psd_layers():',
  'decode_rle_mask_payload(',
  'decode_source_layer_rgb_payload(',
  'pattern_strength_map',
  '"base_scale"',
  '"base_offset_x"',
  '"base_offset_y"',
  '"base_rotation"',
  '"base_flip_h"',
  '"base_flip_v"',
  '"second_base"',
  'export_layers=True',
  'per_zone_{idx}_spec.png',
  'combined_paint.png',
  'layers.json',
].forEach((needle) => assert(route.includes(needle), `route module missing ${needle}`));

assert(
  manifest.files.includes('server_routes/psd_layer_export_routes.py'),
  'runtime manifest missing PSD layer export route module'
);
assert(
  contextTargets.targets['server-psd-layer-export-routes'],
  'context targets missing server-psd-layer-export-routes'
);

if (failures.length) {
  console.error('[spb_guard_server_psd_layer_export_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_psd_layer_export_routes] OK');
