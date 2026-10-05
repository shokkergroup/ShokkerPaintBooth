const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/psd_import_routes.py', 'utf8');
const tree = fs.readFileSync('server_routes/psd_import_tree.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  "def api_psd_import(",
  "def api_psd_rasterize_all(",
  "def api_psd_layer(",
  "@app.route('/api/psd-import'",
  "@app.route('/api/psd-rasterize-all'",
  "@app.route('/api/psd-layer'",
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns ${needle}`);
});

[
  "from server_routes.psd_import_routes import register_psd_import_routes",
  "register_psd_import_routes(",
  "require_internal_request=_require_spb_internal_request",
  "sanitize_path=_sanitize_path",
  "get_cached_psd=_get_cached_psd",
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  "def register_psd_import_routes(",
  "@app.route('/api/psd-import', methods=['POST'])",
  "@app.route('/api/psd-rasterize-all', methods=['POST'])",
  "@app.route('/api/psd-layer', methods=['POST'])",
  "require_internal_request()",
  "sanitize_path(psd_path)",
  "get_cached_psd(psd_path)",
  "from server_routes.psd_import_tree import build_layer_tree, iter_leaf_layers",
  "layers = build_layer_tree(psd, psd.width, psd.height)",
  "for metadata, child in iter_leaf_layers(psd):",
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`psd_import_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/psd_import_routes.py"')) {
  failures.push('runtime manifest missing psd_import_routes.py');
}
if (!manifest.includes('"server_routes/psd_import_tree.py"')) {
  failures.push('runtime manifest missing psd_import_tree.py');
}
[
  "def build_layer_tree(",
  "def iter_leaf_layers(",
  '"layer_key": _layer_key(index_path)',
  '"effective_visible": effective_visible',
].forEach((needle) => {
  if (!tree.includes(needle)) failures.push(`psd_import_tree.py missing ${needle}`);
});
if (!targets.includes('"server-psd-import-routes"')) {
  failures.push('context target missing server-psd-import-routes');
}

if (failures.length) {
  console.error('[spb_guard_server_psd_import_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_psd_import_routes] OK');
