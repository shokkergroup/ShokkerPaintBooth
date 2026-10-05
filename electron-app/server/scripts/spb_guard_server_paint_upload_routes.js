const fs = require('fs');

const server = fs.readFileSync('server.py', 'utf8');
const route = fs.readFileSync('server_routes/paint_upload_routes.py', 'utf8');
const targets = fs.readFileSync('scripts/spb_context_targets.json', 'utf8');

const failures = [];

[
  "def upload_spec_map(",
  "@app.route('/upload-spec-map'",
  "Spec map imported:",
].forEach((needle) => {
  if (server.includes(needle)) failures.push(`server.py still owns upload-spec-map implementation: ${needle}`);
});

[
  "from server_routes.paint_upload_routes import register_paint_upload_routes",
  "register_paint_upload_routes(",
  "output_folder=OUTPUT_FOLDER",
  "temp_file_path=_spb_temp_file_path",
].forEach((needle) => {
  if (!server.includes(needle)) failures.push(`server.py missing paint upload bridge: ${needle}`);
});

[
  "def register_paint_upload_routes(",
  "@app.route('/upload-composited-paint', methods=['POST'])",
  "@app.route('/upload-spec-map', methods=['POST'])",
  "def upload_spec_map(",
  "Spec map path must be TGA/PNG/JPG",
  "temp_spec_imports",
  "@app.route('/api/upload-paint-file', methods=['POST'])",
].forEach((needle) => {
  if (!route.includes(needle)) failures.push(`paint_upload_routes.py missing ${needle}`);
});

if (!targets.includes('"server-paint-upload-routes"')) {
  failures.push('context target missing server-paint-upload-routes');
}

if (failures.length) {
  console.error('[spb_guard_server_paint_upload_routes] FAIL');
  failures.forEach((failure) => console.error(` - ${failure}`));
  process.exit(1);
}

console.log('[spb_guard_server_paint_upload_routes] OK');
