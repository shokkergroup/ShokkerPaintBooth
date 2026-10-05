#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf8');

const server = read('server.py');
const route = read('server_routes/photoshop_export_routes.py');
const manifest = JSON.parse(read('scripts/runtime-sync-manifest.json'));
const contextTargets = JSON.parse(read('scripts/spb_context_targets.json'));

const failures = [];
const assert = (condition, message) => {
  if (!condition) failures.push(message);
};

assert(!server.includes('def export_to_photoshop('), 'server.py still owns export_to_photoshop');
assert(
  server.includes('from server_routes.photoshop_export_routes import register_photoshop_export_routes'),
  'server.py missing Photoshop export route import'
);
assert(
  server.includes('register_photoshop_export_routes('),
  'server.py missing Photoshop export route registration'
);
[
  'engine_getter=lambda: engine',
  'output_folder_getter=lambda: OUTPUT_FOLDER',
  'photoshop_exchange_root=_photoshop_exchange_root',
  'max_zones_per_request=MAX_ZONES_PER_REQUEST',
  'apply_paint_recolor=lambda',
  'decode_rle_mask_payload=lambda',
  'decode_source_layer_rgb_payload=lambda',
  'decode_spatial_mask_payload=lambda',
].forEach((needle) => assert(server.includes(needle), `server.py bridge missing ${needle}`));

[
  'def register_photoshop_export_routes(',
  "@app.route('/api/export-to-photoshop', methods=['POST'])",
  'def export_to_photoshop():',
  'engine.full_render_pipeline(',
  'stamp_image=stamp_image_path,',
  'stamp_spec_finish=stamp_spec_finish,',
  'decal_spec_finishes=decal_spec_finishes if decal_spec_finishes else None,',
  'decal_paint_path=decal_paint_path,',
  'decal_mask_base64=decal_mask_base64,',
  'decode_source_layer_rgb_payload(',
  'decode_spatial_mask_payload(',
  'max_zones_per_request',
  'manifest.json',
  'last_export.json',
].forEach((needle) => assert(route.includes(needle), `route module missing ${needle}`));

assert(
  manifest.files.includes('server_routes/photoshop_export_routes.py'),
  'runtime manifest missing Photoshop export route module'
);
assert(
  contextTargets.targets['server-photoshop-export-routes'],
  'context targets missing server-photoshop-export-routes'
);

if (failures.length) {
  console.error('[spb_guard_server_photoshop_export_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_photoshop_export_routes] OK');
