const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/cache_admin_routes.py', 'utf8');
const manifest = fs.readFileSync('scripts/runtime-sync-manifest.json', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  "def api_clear_cache(",
  "def regen_thumbnail(",
  "def debug_rotation_log(",
  "def api_reload_engine(",
  "def api_clear_cache_named(",
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns ${needle}`);
});

[
  "from server_routes.cache_admin_routes import register_cache_admin_routes",
  "register_cache_admin_routes(",
  "finish_catalog_cache_clear=_finish_catalog_cache['clear']",
  "finish_meta_cache_clear=lambda: _finish_meta_cache_clear()",
  "psd_cache_getter=lambda: _psd_cache",
  "prev_spec_cache_getter=_get_prev_spec_cache",
  "prev_spec_cache_setter=_set_prev_spec_cache",
  "validate_thumbnail_regen_request=lambda finish_type, finish_id: _validate_thumbnail_regen_request(finish_type, finish_id)",
  "queue_thumbnail_regen=lambda finish_type, finish_id: _queue_thumbnail_regen(finish_type, finish_id)",
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing bridge: ${needle}`);
});

[
  "def register_cache_admin_routes(",
  "@app.route('/api/clear-cache', methods=['POST'])",
  "@app.route('/api/thumb-regen/<finish_type>/<finish_id>', methods=['POST'])",
  "@app.route('/debug-rotation-log', methods=['GET'])",
  "@app.route('/api/reload-engine', methods=['POST'])",
  "@app.route('/api/clear-cache/<cache_name>', methods=['POST'])",
  "finish_catalog_cache_clear()",
  "finish_meta_cache_clear()",
  "prev_spec_cache_setter(None)",
  "queue_thumbnail_regen(normalized_type, finish_id)",
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`cache_admin_routes.py missing ${needle}`);
});

if (!manifest.includes('"server_routes/cache_admin_routes.py"')) {
  failures.push('runtime manifest missing cache_admin_routes.py');
}
if (!targets.includes('"server-cache-admin"')) {
  failures.push('context target missing server-cache-admin');
}

const swatchCacheIndex = server.indexOf('_SWATCH_CACHE = {}');
const cacheRegisterIndex = server.indexOf('register_cache_admin_routes(');
if (swatchCacheIndex < 0) {
  failures.push('server.py missing _SWATCH_CACHE initialization');
} else if (cacheRegisterIndex < 0 || swatchCacheIndex > cacheRegisterIndex) {
  failures.push('_SWATCH_CACHE must initialize before cache-admin route registration');
}

if (failures.length) {
  console.error('[spb_guard_server_cache_admin_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_cache_admin_routes] OK');
