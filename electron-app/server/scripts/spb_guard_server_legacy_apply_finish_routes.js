const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/legacy_apply_finish_routes.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  "def apply_finish_legacy(",
  "@app.route('/apply-finish'",
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns ${needle}`);
});

[
  "from server_routes.legacy_apply_finish_routes import register_legacy_apply_finish_routes",
  "register_legacy_apply_finish_routes(",
  "engine_getter=lambda: engine",
  "output_folder_getter=lambda: OUTPUT_FOLDER",
  "load_config=load_config",
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  "def register_legacy_apply_finish_routes(",
  "@app.route('/apply-finish', methods=['POST'])",
  "request.files['paint_file']",
  "engine_getter().build_multi_zone(",
  "load_config()",
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`legacy_apply_finish_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/legacy_apply_finish_routes.py"')) {
  failures.push('runtime manifest missing legacy_apply_finish_routes.py');
}
if (!targets.includes('"server-legacy-apply-finish-routes"')) {
  failures.push('context target missing server-legacy-apply-finish-routes');
}

if (failures.length) {
  console.error('[spb_guard_server_legacy_apply_finish_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_legacy_apply_finish_routes] OK');
