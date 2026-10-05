const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/shokk_routes.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  'def api_shokk_library_path(',
  'def api_shokk_list(',
  'def api_shokk_save(',
  'def api_shokk_open(',
  'def api_shokk_extracted_file(',
  'def api_shokk_preview(',
  'def api_shokk_delete(',
  'def api_shokk_rename(',
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns ${needle}`);
});

[
  'from server_routes.shokk_routes import register_shokk_routes',
  'register_shokk_routes(',
  'manager_getter=_get_shokk_manager',
  'output_folder_getter=lambda: OUTPUT_FOLDER',
  "spb_version_getter=lambda: getattr(CFG, 'VERSION', '5.0.0')",
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  'def register_shokk_routes(',
  "@app.route('/api/shokk/library-path', methods=['GET'])",
  "@app.route('/api/shokk/list', methods=['GET'])",
  "@app.route('/api/shokk/save', methods=['POST'])",
  "@app.route('/api/shokk/open', methods=['POST'])",
  "@app.route('/api/shokk/extracted/<extract_basename>/<filename>', methods=['GET'])",
  "@app.route('/api/shokk/preview/<filename>', methods=['GET'])",
  "@app.route('/api/shokk/delete', methods=['POST'])",
  "@app.route('/api/shokk/rename', methods=['POST'])",
  'tempfile.mkdtemp(dir=output_folder, prefix="shokk_open_")',
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`shokk_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/shokk_routes.py"')) {
  failures.push('runtime manifest missing shokk_routes.py');
}
if (!targets.includes('"server-shokk-routes"')) {
  failures.push('context target missing server-shokk-routes');
}

if (failures.length) {
  console.error('[spb_guard_server_shokk_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_shokk_routes] OK');
