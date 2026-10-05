const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/custom_finish_routes.py', 'utf8');
const mixerRoute = fs.readFileSync('server_routes/custom_finish_mixer_routes.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  'def api_save_custom_finish(',
  'def api_custom_finishes(',
  'def api_delete_custom_finish(',
  'def api_mix_preview(',
  'def api_mix_paint_preview(',
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns ${needle}`);
});

[
  'from server_routes.custom_finish_routes import register_custom_finish_routes',
  'register_custom_finish_routes(',
  'load_custom_finishes=_load_custom_finishes',
  'save_custom_finishes=_save_custom_finishes',
  'from server_routes.custom_finish_mixer_routes import register_custom_finish_mixer_routes',
  'register_custom_finish_mixer_routes(',
].forEach((needle) => {
  // [2026-09-05 RETIRED LEDGER] Finish Mixer SCRAPPED by the owner: server.py must NOT call these
  // registrars any more (the modules stay on disk, inert). scripts/retired_catalog.json feature=finish_mixer.
  if (server.includes(needle)) failures.push(`server.py re-registers the scrapped Finish Mixer: ${needle}`);
});

[
  'def register_custom_finish_routes(',
  "@app.route('/api/save-custom-finish', methods=['POST'])",
  "@app.route('/api/custom-finishes', methods=['GET'])",
  "@app.route('/api/delete-custom-finish', methods=['POST'])",
  'def _next_custom_finish_id(',
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`custom_finish_routes.py missing ${needle}`);
});

[
  'def register_custom_finish_mixer_routes(',
  "@app.route('/api/mix-preview', methods=['POST'])",
  "@app.route('/api/mix-paint-preview', methods=['POST'])",
  'engine = engine_getter()',
  "render_swatch_bytes('base'",
  'mix_paint_preview_failed',
].forEach((needle) => {
  if (!mixerRoute.includes(needle)) failures.push(`custom_finish_mixer_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/custom_finish_routes.py"')) {
  failures.push('runtime manifest missing custom_finish_routes.py');
}
if (!manifest.includes('"server_routes/custom_finish_mixer_routes.py"')) {
  failures.push('runtime manifest missing custom_finish_mixer_routes.py');
}
if (!targets.includes('"server-custom-finish-routes"')) {
  failures.push('context target missing server-custom-finish-routes');
}
if (!targets.includes('"server-custom-finish-mixer-routes"')) {
  failures.push('context target missing server-custom-finish-mixer-routes');
}

if (failures.length) {
  console.error('[spb_guard_server_custom_finish_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_custom_finish_routes] OK');
