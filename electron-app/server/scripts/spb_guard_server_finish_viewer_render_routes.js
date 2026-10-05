const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/finish_viewer_render_routes.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  "@app.route('/api/finish-viewer/mono/<finish_id>'",
  "@app.route('/api/finish-viewer/render/<finish_type>/<finish_id>'",
  "def _finish_viewer_render_maps(",
  "def _finish_viewer_encode_maps(",
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns Finish Viewer render implementation: ${needle}`);
});

[
  'from server_routes.finish_viewer_render_routes import register_finish_viewer_render_routes',
  'register_finish_viewer_render_routes(',
  'engine_getter=lambda: engine',
  'normalize_spec_result_to_rgba=_normalize_spec_result_to_rgba',
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  'def register_finish_viewer_render_routes(',
  "@app.route('/api/finish-viewer/mono/<finish_id>', methods=['GET'])",
  "@app.route('/api/finish-viewer/render/<finish_type>/<finish_id>', methods=['GET'])",
  'def _finish_viewer_render_maps(',
  'enforce_iron_rules(spec_u8)',
  'engine_getter()',
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`finish_viewer_render_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/finish_viewer_render_routes.py"')) {
  failures.push('runtime manifest missing finish_viewer_render_routes.py');
}
if (!targets.includes('"server-finish-viewer-render-routes"')) {
  failures.push('context target missing server-finish-viewer-render-routes');
}

const normalizeIndex = server.indexOf('def _normalize_spec_result_to_rgba(');
const normalizeImportIndex = server.indexOf('from server_routes.spec_result_support import normalize_spec_result_to_rgba as _normalize_spec_result_to_rgba');
const renderRegisterIndex = server.indexOf('register_finish_viewer_render_routes(');
const normalizeAvailableIndex = normalizeImportIndex >= 0 ? normalizeImportIndex : normalizeIndex;
if (normalizeAvailableIndex < 0) {
  failures.push('server.py missing _normalize_spec_result_to_rgba helper/import');
} else if (renderRegisterIndex < 0 || normalizeAvailableIndex > renderRegisterIndex) {
  failures.push('_normalize_spec_result_to_rgba must be imported/defined before Finish Viewer render route registration');
}

if (failures.length) {
  console.error('[spb_guard_server_finish_viewer_render_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_finish_viewer_render_routes] OK');
