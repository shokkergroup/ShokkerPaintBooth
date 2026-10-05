#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf8');

const server = read('server.py');
const route = read('server_routes/spec_channel_export_routes.py');
const manifest = JSON.parse(read('scripts/runtime-sync-manifest.json'));
const contextTargets = JSON.parse(read('scripts/spb_context_targets.json'));

const failures = [];
const assert = (condition, message) => {
  if (!condition) failures.push(message);
};

assert(!server.includes('def api_export_spec_channels('), 'server.py still owns api_export_spec_channels');
assert(
  server.includes('from server_routes.spec_channel_export_routes import register_spec_channel_export_routes'),
  'server.py missing spec-channel export import'
);
assert(
  server.includes('register_spec_channel_export_routes('),
  'server.py missing spec-channel export registration'
);
[
  'output_folder_getter=lambda: OUTPUT_FOLDER',
  'shokk_manager_getter=_get_shokk_manager',
  'logger=logger',
].forEach((needle) => assert(server.includes(needle), `server bridge missing ${needle}`));

[
  'def register_spec_channel_export_routes(',
  "@app.route('/api/export-spec-channels', methods=['POST'])",
  'def api_export_spec_channels():',
  'shokk_manager_getter()',
  'tempfile.mkdtemp(dir=output_folder, prefix="shokk_export_")',
  '_latest_render_files(output_folder)',
  '_latest_job_files(output_folder)',
  'spec_full.png',
  'paint_base.png',
  'spec_metallic.png',
  'spec_roughness.png',
  'spec_clearcoat.png',
  'spec_mask.png',
].forEach((needle) => assert(route.includes(needle), `route module missing ${needle}`));

assert(
  manifest.files.includes('server_routes/spec_channel_export_routes.py'),
  'runtime manifest missing spec-channel export route module'
);
assert(
  contextTargets.targets['server-spec-channel-export-routes'],
  'context targets missing server-spec-channel-export-routes'
);

if (failures.length) {
  console.error('[spb_guard_server_spec_channel_export_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_spec_channel_export_routes] OK');
