const fs = require('fs');

function read(path) {
  return fs.readFileSync(path, 'utf8');
}

function assertIncludes(text, needle, label) {
  if (!text.includes(needle)) {
    throw new Error(`${label} missing: ${needle}`);
  }
}

function assertNotIncludes(text, needle, label) {
  if (text.includes(needle)) {
    throw new Error(`${label} should not include: ${needle}`);
  }
}

const server = read('server.py');
const modulePath = 'server_routes/finish_viewer_recent_routes.py';
const mod = read(modulePath);
const manifest = read('scripts/runtime-sync-manifest.json');
const contextTargets = read('scripts/spb_context_targets.json');

[
  "def api_finish_viewer_full_dna_export_start",
  'def api_finish_viewer_full_dna_export_status',
  'def _finish_viewer_latest_map_paths',
  'def api_finish_viewer_latest(',
  'def api_finish_viewer_latest_map',
].forEach((needle) => assertNotIncludes(server, needle, 'server.py'));

[
  'from server_routes.finish_viewer_recent_routes import register_finish_viewer_latest_routes',
  'register_finish_viewer_latest_routes(',
  'output_folder_getter=lambda: OUTPUT_FOLDER',
  'full_dna_job=_FULL_DNA_EXPORT_JOB',
  'full_dna_status_path_getter=_full_dna_status_path',
  'full_dna_status_reader=_read_full_dna_status',
  'safe_int=_safe_int',
  'server_dir=SERVER_DIR',
  'rate_limit=_rate_limit',
].forEach((needle) => assertIncludes(server, needle, 'server.py bridge'));

[
  "@app.route('/api/finish-viewer/full-dna-export', methods=['POST'])",
  "@app.route('/api/finish-viewer/full-dna-export/status', methods=['GET'])",
  "@app.route('/api/finish-viewer/latest', methods=['GET'])",
  "@app.route('/api/finish-viewer/latest-map/<kind>', methods=['GET'])",
  'def register_finish_viewer_latest_routes(',
  'subprocess.Popen(cmd, cwd=server_dir',
  'log_handle.close()',
  'full_catalog_dna_export_already_running',
].forEach((needle) => assertIncludes(mod, needle, modulePath));

assertIncludes(manifest, '"server_routes/finish_viewer_recent_routes.py"', 'runtime manifest');
assertIncludes(contextTargets, '"server-finish-viewer-recent-routes"', 'context target');

console.log('[guard] server finish-viewer latest routes extraction ok');
