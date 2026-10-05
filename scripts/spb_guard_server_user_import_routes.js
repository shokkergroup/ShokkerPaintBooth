const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/user_import_routes.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  "@app.route('/api/user-imports'",
  'def api_user_imports_import(',
  'def api_user_imports_delete(',
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns ${needle}`);
});

[
  'from server_routes.user_import_routes import register_user_import_routes',
  'register_user_import_routes(',
  'SPB_USER_IMPORTS_DIR',
  'finish_catalog_cache_clear=_finish_catalog_cache',
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  'def register_user_import_routes(',
  "@app.route(\"/api/user-imports/import\", methods=[\"POST\"])",
  "@app.route(\"/api/user-imports/delete\", methods=[\"POST\"])",
  "@app.route(\"/api/user-imports/rebake-dna\", methods=[\"POST\"])",
  "@app.route(\"/api/user-imports/export-all\", methods=[\"GET\"])",
  "@app.route(\"/api/user-imports/preview-image/<finish_id>\", methods=[\"GET\"])",
  "@app.route(\"/api/user-imports/dna-styles\", methods=[\"GET\"])",
  "@app.route(\"/api/user-imports/engine-preview/<finish_id>\", methods=[\"GET\"])",
  'render_engine_uv_bytes',
  'DNA_STYLES',
  'export_all_packs',
  'resolve_preview_image',
  'rebake_dna_spec',
  'import_pattern_files',
  'import_spec_overlay_files',
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`user_import_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/user_import_routes.py"')) {
  failures.push('runtime manifest missing user_import_routes.py');
}
if (!manifest.includes('"engine/paint_v2/user_imports.py"')) {
  failures.push('runtime manifest missing user_imports.py');
}
if (!targets.includes('"server-user-import-routes"')) {
  failures.push('context target missing server-user-import-routes');
}

if (failures.length) {
  console.error('[spb_guard_server_user_import_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_user_import_routes] OK');
